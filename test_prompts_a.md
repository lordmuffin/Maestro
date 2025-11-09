Write a complete, well-commented Python script named auto_phishing_blocker.py.

GOAL: Create a command-line utility to automate the bulk blocking of email senders by dynamically fetching "User-reported phishing" alerts from the Google Workspace Alert Center API and adding the senders to a centralized Gmail Address List for routing rules.

REQUIRED LIBRARIES: google-api-python-client and oauth2client (or similar Google libraries for authentication).

CORE LOGIC:

Authentication: Implement a function authenticate_apis() to set up authorized service objects for:

Alert Center API (v1beta1) (To fetch alerts).

Admin SDK Directory API (v1) or Gmail API (To manage the Address List/Settings).

Assume the script uses a Service Account with necessary Domain-Wide Delegation.

Alert Fetching: Implement get_phishing_senders(service_object, days_to_lookback):

This function must call the Alert Center API to retrieve alerts of type USER_REPORTED_PHISHING.

It should filter for alerts active within the specified lookback period (e.g., last 7 days).

For each alert, extract the sender email address (the Actor field) from the alert's data payload.

Return a unique set of sender email addresses.

Address List Management: Implement functions to manage the target Address List (e.g., named "Automated Phishing Senders"):

get_existing_sender_list(service_object, list_name): Retrieve the existing Gmail address list by its display name. If the list does not exist, the function must create it and return its ID.

update_sender_list(service_object, list_id, new_senders): Add the new_senders (from the Alert Center) to the existing list identified by list_id. The list update process must handle potential duplicates and be robust to API limits or large payloads.

Main Execution: The main block should:

Define the target Gmail Address List name (e.g., PHISHING_SENDER_BLOCK_LIST).

Call authenticate_apis().

Call get_phishing_senders() (use a default 7-day lookback).

Call get_existing_sender_list().

Call update_sender_list() with the new senders.

Print a summary: the number of new senders found, the number of senders added to the list, and the total senders now in the list.

CRITICAL IMPLEMENTATION DETAILS (Must be in comments/documentation):

Clearly state the required Google API scopes for both the Alert Center API and the Admin SDK/Gmail Settings API.

Clearly state the necessary steps for setting up the Service Account and Domain-Wide Delegation in the Google Admin Console.

Include placeholders for API credentials file path (SERVICE_ACCOUNT_FILE) and the user email for delegation (DELEGATED_ADMIN_EMAIL).

Include proper error handling for API calls.