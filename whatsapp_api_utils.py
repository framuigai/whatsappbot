import requests
import os
import logging
# from dotenv import load_dotenv # REMOVED: Loaded globally in config.py

# Configure logging for this module
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s') # REMOVED: Configured globally in app.py
logger = logging.getLogger(__name__) # Use specific logger for this module

# Load environment variables (important if this script might be run independently for testing)
# load_dotenv() # REMOVED: Loaded globally in config.py

WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

def send_whatsapp_message(to_number, message_body):
    """
    Sends a WhatsApp message using the WhatsApp Cloud API.
    """
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.error("WhatsApp API access token or phone number ID not set in environment variables.") # Changed to logger.error
        return False

    url = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": message_body}
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        logger.info(f"Message sent to {to_number}: {message_body[:50]}...") # Changed to logger.info
        return True
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error sending message to {to_number}: {http_err} - {response.text}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Other error sending message to {to_number}: {e}", exc_info=True)
        return False