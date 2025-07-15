# pages/Login.py
import streamlit as st
from firebase_auth_component import firebase_auth_component
from auth_utils import init_session_state
import json

# Initialize session state (important for consistent behavior across pages)
init_session_state()

st.set_page_config(page_title="Login", layout="centered")
st.title("Admin Login")

# Render the Firebase auth component
auth_delta_generator = firebase_auth_component(key="firebase_auth_widget")
raw_auth_value = auth_delta_generator.value

current_auth_status = {"loggedIn": False}
if raw_auth_value is not None:
    try:
        current_auth_status = json.loads(raw_auth_value)
    except (json.JSONDecodeError, TypeError):
        current_auth_status = {"loggedIn": False}


# Check if the login status has changed or if it's a new login
if current_auth_status.get("loggedIn") and (
    st.session_state.logged_in_user_info is None
    or st.session_state.logged_in_user_info.get("email") != current_auth_status.get("email")
):
    st.session_state.logged_in_user_info = current_auth_status
    st.session_state.should_redirect_after_login = True
    st.success(f"Logged in as: {current_auth_status.get('email')}. Redirecting to dashboard...")
    st.rerun() # Trigger a rerun to process the new session state and trigger the redirect below

# Handle redirection after a successful login and a rerun
if st.session_state.should_redirect_after_login and st.session_state.logged_in_user_info:
    st.session_state.should_redirect_after_login = False # Reset the flag immediately
    st.switch_page("pages/Admin_Dashboard.py") # IMPORTANT: Full path for redirect
    st.stop() # Stop script execution to prevent rendering login page content below

# If not logged in and no pending redirect, display login prompt
# This ensures the message only shows when truly not logged in and not in a redirect cycle
if not st.session_state.logged_in_user_info and not st.session_state.should_redirect_after_login:
    st.info("Please log in to access the admin dashboard.")