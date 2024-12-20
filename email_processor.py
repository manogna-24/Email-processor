import logging
import imaplib
import email
import time
from email.header import decode_header
from email.utils import parseaddr, parsedate_tz, mktime_tz
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError
import configparser

# Configure logging with proper encoding
def setup_logging():
    """Set up logging with proper Unicode handling."""
    handlers = []
    file_handler = logging.FileHandler('email_processor.log', encoding='utf-8')
    stream_handler = logging.StreamHandler()
    handlers.append(file_handler)
    handlers.append(stream_handler)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

setup_logging()

class EmailProcessor:
    def __init__(self, config_file: str):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        self.db_client = None
        self.db = None

    def _setup_database(self) -> None:
        """Initialize MongoDB connection with error handling."""
        try:
            self.db_client = MongoClient(
                self.config['Database']['mongodb_uri'], serverSelectionTimeoutMS=5000
            )
            self.db = self.db_client[self.config['Database']['database']]
            self.db[self.config['Database']['collection']].create_index('message_id', unique=True)
            self.db_client.admin.command('ping')
            logging.info("Successfully connected to MongoDB")
        except ServerSelectionTimeoutError as e:
            logging.error(f"MongoDB server not reachable: {str(e)}")
            raise
        except PyMongoError as e:
            logging.error(f"MongoDB error: {str(e)}")
            raise

    def connect_to_email_server(self) -> imaplib.IMAP4_SSL:
        """Establish connection to the email server with retries."""
        max_retries = 3
        retry_delay = 5  # seconds
        for attempt in range(max_retries):
            try:
                mail = imaplib.IMAP4_SSL(self.config['Email']['imap_server'])
                mail.login(self.config['Email']['email'], self.config['Email']['password'])
                logging.info("Successfully connected to email server")
                return mail
            except imaplib.IMAP4.error as e:
                logging.error(f"IMAP error: {str(e)}")
            except Exception as e:
                logging.error(f"Unexpected error: {str(e)}")
            if attempt < max_retries - 1:
                logging.info(f"Retrying connection... (Attempt {attempt + 2}/{max_retries})")
                time.sleep(retry_delay)
            else:
                raise ConnectionError("Failed to connect to email server after max retries")

    def process_email(self, email_message) -> dict:
        """Extract email data with error handling and proper Unicode handling."""
        try:
            subject = email_message.get("subject", "[No subject]")
            if subject:
                decoded_list = decode_header(subject)
                subject = "".join(
                    str(t[0], t[1] or 'utf-8') if isinstance(t[0], bytes)
                    else str(t[0])
                    for t in decoded_list
                ).encode('utf-8').decode('utf-8', errors='replace')
            
            sender = parseaddr(email_message.get("from", ""))[1]
            sender = sender.encode('utf-8').decode('utf-8', errors='replace')

            date_tuple = parsedate_tz(email_message.get("date"))
            timestamp = datetime.fromtimestamp(
                mktime_tz(date_tuple) if date_tuple else time.time()
            )

            return {
                'message_id': email_message.get("message-id", f"NO_ID_{timestamp.timestamp()}"),
                'sender': sender,
                'subject': subject,
                'timestamp': timestamp
            }
        except KeyError as e:
            logging.warning(f"Malformed email missing key {str(e)}: Skipping this email")
            return None
        except Exception as e:
            logging.error(f"Error processing email message: {str(e)}")
            return None

    def save_to_database(self, email_data: dict) -> None:
        """Save email data to MongoDB with error handling."""
        try:
            collection = self.db[self.config['Database']['collection']]
            email_dict = {
                'message_id': email_data['message_id'],
                'sender': email_data['sender'],
                'subject': email_data['subject'],
                'timestamp': email_data['timestamp'],
                'processed_at': datetime.now()
            }
            collection.update_one(
                {'message_id': email_data['message_id']},
                {'$set': email_dict},
                upsert=True
            )
            logging.info(f"Saved email from {email_data['sender']} to MongoDB")
        except PyMongoError as e:
            logging.error(f"Error saving email to database: {str(e)}")
            raise

    def process_unread_emails(self):
        """Fetch and process unread emails."""
        try:
            mail = self.connect_to_email_server()
            mail.select("inbox")
            status, messages = mail.search(None, 'UNSEEN')
            if status != "OK":
                logging.warning("Failed to search for unread emails.")
                return

            email_ids = messages[0].split()
            if not email_ids:
                logging.info("No unread emails in the inbox.")
                return

            for email_id in email_ids:
                res, msg = mail.fetch(email_id, '(RFC822)')
                if res != "OK":
                    logging.warning(f"Failed to fetch email with ID {email_id}")
                    continue

                email_message = email.message_from_bytes(msg[0][1])
                email_data = self.process_email(email_message)
                if email_data:
                    self.save_to_database(email_data)
                    logging.info(f"Processed email: {email_data['subject']}")
        except ConnectionError as e:
            logging.error(f"Connectivity issue: {str(e)}")
        except Exception as e:
            logging.error(f"Error processing emails: {str(e)}")
        finally:
            if 'mail' in locals():
                mail.logout()

def main():
    try:
        processor = EmailProcessor('config.ini')
        processor._setup_database()
        processor.process_unread_emails()
    except Exception as e:
        logging.critical(f"Critical error in main execution: {str(e)}")

if __name__ == "__main__":
    main()
