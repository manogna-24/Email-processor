# Email-processor

## Overview
The Email Processor is a Python-based application that retrieves unread emails from an email account using IMAP, processes their content, and stores relevant information into a MongoDB database. This tool is ideal for automating the extraction and storage of email data for further analysis or record-keeping.



## Installation
### Prerequisites
- Python 3.7+
- MongoDB server (local or cloud-based)

### Dependencies
Install the required Python packages:
```bash
pip install pymongo
```

---

## Setup
### Configuration File
Create a `config.ini` file in the root directory of the project with the following structure:

```ini
[Database]
mongodb_uri = mongodb://localhost:27017
database = email_processor_db
collection = emails

[Email]
imap_server = imap.gmail.com
email = your_email@gmail.com
password = your_password
```

Replace the placeholders with your MongoDB URI, database, collection name, and email credentials.

---



### Process Workflow
1. Connects to the MongoDB server and verifies the connection.
2. Connects to the email server using the IMAP protocol.
3. Searches for unread emails in the inbox.
4. Processes each email to extract relevant data.
5. Saves the data into MongoDB.

---

## Logging
Logs are stored in `email_processor.log` and displayed in the console for real-time updates. Logs include:
- Connection status for email and database servers.
- Processing status for each email.
- Errors encountered during execution.


## File Structure
```
├── email_processor.py        # Main script for email processing
├── config.ini                # Configuration file
├── email_processor.log       # Log file for tracking execution
└── README.md                 # Project documentation (this file)
```
