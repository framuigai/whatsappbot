# app.py

from flask import Flask

# Initialize the Flask application
app = Flask(__name__)

# Define a simple route for the root URL
@app.route('/')
def hello_world():
    """
    This function handles requests to the root URL ("/").
    It simply returns a "Hello, World!" message.
    This helps verify that the Flask application is running correctly.
    """
    return 'Hello, World! This is your WhatsApp Bot MVP.'

# This block ensures the Flask app runs only when the script is executed directly
if __name__ == '__main__':
    # Run the Flask application
    # debug=True enables debug mode, which provides a debugger and reloads
    # the server automatically on code changes. Useful for development.
    # port=5000 is the default port for Flask.
    app.run(debug=True, port=5000)