# pages/Login.py
import streamlit as st
from firebase_auth_component import firebase_auth_component

st.set_page_config(page_title="Login", layout="centered")

st.title("Admin Login")

# Render the Firebase auth component
auth_delta_generator = firebase_auth_component()
raw_auth_value = auth_delta_generator.value

# Initialize session state for login info if not already set
if 'logged_in_user_info' not in st.session_state:
    st.session_state.logged_in_user_info = None

current_auth_status = {"loggedIn": False}
if raw_auth_value is not None and isinstance(raw_auth_value, dict):
    current_auth_status = raw_auth_value

# Update session state
st.session_state.logged_in_user_info = current_auth_status if current_auth_status.get('loggedIn') else None

if st.session_state.logged_in_user_info:
    st.success(f"Logged in as: {st.session_state.logged_in_user_info.get('email')}. Redirecting to dashboard...")
    # Use st.switch_page for immediate, native Streamlit page transition
    st.switch_page("Admin_Dashboard") # Use the name of the file in pages/ without .py extension
    st.stop() # Stop further execution of this script immediately
else:
    st.info("Please log in to access the admin dashboard.")