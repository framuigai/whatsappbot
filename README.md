# WhatsApp Gemini AI Chatbot MVP

A basic, yet robust, WhatsApp chatbot powered by Google's Gemini 1.5 Flash model, built with Flask and SQLite. It handles conversation context, manages token limits, and includes resilience features for common edge cases.

## Features

* **WhatsApp Integration:** Receives and sends messages via WhatsApp Cloud API.
* **Gemini AI Powered:** Uses Google's Gemini 1.5 Flash model for intelligent replies.
* **Conversation Context:** Stores and retrieves message history in a SQLite database to maintain multi-turn conversations.
* **Token Management:** Intelligently truncates conversation history to stay within Gemini's context window limits.
* **Resilience & Edge Case Handling:**
    * Graceful handling of empty or whitespace-only messages.
    * Basic rate-limiting to prevent spam from a single user.
    * Detects and provides fallback for Gemini AI safety policy violations.
    * Implements exponential backoff with retries for Gemini API quota limits (HTTP 429).
* **Clear Logging:** Detailed logging for all operations and error cases.

## Prerequisites

Before you begin, ensure you have the following installed:

* **Python 3.8+**
* **pip** (Python package installer)
* A **WhatsApp Business Account** with a configured phone number and API access.
* A **Google Cloud Project** with the Gemini API enabled and an API key generated.
* `ngrok` (or a similar tunneling service) to expose your local Flask server to the internet for WhatsApp webhooks.

## Setup Guide

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git)
    cd YOUR_REPO_NAME
    ```
    (Replace `YOUR_USERNAME` and `YOUR_REPO_NAME` with your actual GitHub details.)

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install Flask python-dotenv requests google-generativeai sqlite3
    ```

4.  **Environment Variables:**
    Create a `.env` file in the root of your project directory and add the following:
    ```dotenv
    VERIFY_TOKEN="YOUR_WHATSAPP_WEBHOOK_VERIFY_TOKEN"
    WHATSAPP_ACCESS_TOKEN="YOUR_WHATSAPP_CLOUD_API_ACCESS_TOKEN"
    WHATSAPP_PHONE_NUMBER_ID="YOUR_WHATSAPP_PHONE_NUMBER_ID"
    GEMINI_API_KEY="YOUR_GOOGLE_GEMINI_API_KEY"
    ```
    * Replace the placeholder values with your actual tokens and IDs from WhatsApp and Google Cloud.

## Running the Bot

1.  **Start the Flask Application:**
    ```bash
    # Ensure your virtual environment is activated
    python app.py
    ```
    Your Flask app will start on `http://127.0.0.1:5000`.

2.  **Expose Your Local Server with ngrok:**
    Open a new terminal window (keep the Flask server running in the first one) and run `ngrok`:
    ```bash
    ngrok http 5000
    ```
    `ngrok` will provide you with a public HTTPS URL (e.g., `https://abcdef12345.ngrok-free.app`). Copy this URL.

3.  **Configure WhatsApp Webhook:**
    * Go to your Facebook Developer App dashboard for your WhatsApp Business Account.
    * Navigate to "WhatsApp" -> "API Setup".
    * In the "Webhook" section, click "Configure Webhook".
    * **Webhook URL:** Paste the `ngrok` HTTPS URL you copied.
    * **Verify Token:** Enter the same `VERIFY_TOKEN` you set in your `.env` file.
    * Click "Verify and Save".
    * Under the Webhook configuration, click "Manage" next to the Webhook URL and **subscribe to the `messages` field**.

## Usage

Once the Flask server and ngrok are running, and your WhatsApp webhook is configured, simply send a message to your WhatsApp Business Account number! The bot will respond.

## Troubleshooting

* **"WEBHOOK_VERIFIED failed"**: Double-check your `VERIFY_TOKEN` in `.env` and in the WhatsApp webhook configuration.
* **No replies from bot**: Check your Flask console for any `ERROR` messages. Ensure `ngrok` is running and its URL is correct in the WhatsApp webhook. Check your WhatsApp Cloud API dashboard for any error messages related to outgoing messages.
* **Bot not remembering context**: Check your database (`conversations.db`) to ensure messages are being saved. Verify the `MAX_HISTORY_TOKENS` logic in `generate_ai_reply`.
* **"Sorry, I couldn't process your request right now."**: This is a general fallback. Check your Flask logs for more specific errors (e.g., Gemini API errors, token counting issues).

## Future Enhancements (Optional)

* **Persistent Rate Limiting:** Implement rate limiting that persists across server restarts (e.g., using Redis or SQLite for timestamp storage).
* **Advanced Error Reporting:** Integrate with an error tracking service (e.g., Sentry, Bugsnag).
* **Unit Tests:** Write automated tests for individual functions.
* **Deployment:** Deploy to a cloud platform like Heroku, Google Cloud Run, AWS Elastic Beanstalk, etc., for production use.
* **Rich Media Support:** Extend the bot to handle images, audio, or other media types from WhatsApp.
* **Command Handling:** Add specific commands (e.g., `/reset` to clear conversation history).