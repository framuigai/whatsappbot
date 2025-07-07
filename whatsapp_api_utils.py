import requests
import os
import logging
from dotenv import load_dotenv # Ensure .env is loaded if this module is ever run standalone or tested

# Configure logging for this module
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables (important if this script might be run independently for testing)
load_dotenv()

WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

def send_whatsapp_message(to_number, message_body):
    """
    Sends a WhatsApp message using the WhatsApp Cloud API.
    """
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logging.error("WhatsApp API access token or phone number ID not set in environment variables.")
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
        logging.info(f"Message sent to {to_number}: {message_body[:50]}...")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending WhatsApp message to {to_number}: {e}")
        if response is not None:
            logging.error(f"WhatsApp API response: {response.status_code} - {response.text}")
        return False