# pages/Login.py
import streamlit as st
from firebase_auth_component import firebase_auth_component
# Assuming auth_utils exists and init_session_state is defined within it
from auth_utils import init_session_state
import json
import time

# Initialize session state
# Ensure that auth_utils.py is in your project and init_session_state() properly sets
# st.session_state.logged_in_user_info and st.session_state.should_redirect_after_login
init_session_state()

print(f"\n--- Login.py Script Start --- Time: {time.time()}")
print(f"Initial st.session_state.logged_in_user_info: {st.session_state.get('logged_in_user_info')}")
print(f"Initial st.session_state.should_redirect_after_login: {st.session_state.get('should_redirect_after_login')}")

st.set_page_config(page_title="Login", layout="centered")
st.title("Admin Login")

# Render the Firebase auth component
# Ensure the key is consistent to help Streamlit identify the component across reruns
auth_delta_generator = firebase_auth_component(key="firebase_auth_widget")
raw_auth_value = auth_delta_generator.value

current_auth_status = {"loggedIn": False}

# --- ADDED DIAGNOSTIC FOR raw_auth_value TYPE ---
print(f"Type of raw_auth_value: {type(raw_auth_value)}")
if callable(raw_auth_value):
    print(f"WARNING: raw_auth_value is a callable object (function or method), not the component's data.")
# --- END ADDED DIAGNOSTIC ---

if raw_auth_value is not None:
    try:
        # Attempt to load as JSON. This will fail if raw_auth_value is a function.
        current_auth_status = json.loads(raw_auth_value)
    except (json.JSONDecodeError, TypeError) as e:
        print(f"Error parsing raw_auth_value as JSON: {e}. raw_auth_value was: {raw_auth_value}")
        current_auth_status = {"loggedIn": False}
else: # raw_auth_value is None
    print(f"raw_auth_value is None. Component might not have sent a value yet.")

print(f"After component output. raw_auth_value: {raw_auth_value}")
print(f"Parsed current_auth_status: {current_auth_status}")
print(f"st.session_state.logged_in_user_info (before conditional update): {st.session_state.get('logged_in_user_info')}")

# Check if the login status has changed or if it's a new login
if current_auth_status.get("loggedIn") and (
    st.session_state.logged_in_user_info is None
    or st.session_state.logged_in_user_info.get("email") != current_auth_status.get("email")
):
    print(f"LOGIN SUCCESS DETECTED!")
    st.session_state.logged_in_user_info = current_auth_status
    st.session_state.should_redirect_after_login = True
    st.success(f"Logged in as: {current_auth_status.get('email')}. Redirecting to dashboard...")
    print(f"st.session_state.logged_in_user_info (before rerun): {st.session_state.logged_in_user_info}")
    print(f"st.session_state.should_redirect_after_login (before rerun): {st.session_state.should_redirect_after_login}")
    print(f"Calling st.rerun()...")
    st.rerun() # Trigger a rerun to process the new session state and trigger the redirect below

# Handle redirection after a successful login and a rerun
# This block executes on the rerun.
print(f"On Rerun for Redirect. st.session_state.should_redirect_after_login: {st.session_state.get('should_redirect_after_login')}")
print(f"On Rerun for Redirect. st.session_state.logged_in_user_info: {st.session_state.get('logged_in_user_info')}")

if st.session_state.should_redirect_after_login and st.session_state.logged_in_user_info:
    print(f"REDIRECT CONDITION MET! Switching to Admin_Dashboard page.")
    st.session_state.should_redirect_after_login = False # Reset the flag immediately
    # Use the page name without .py extension for cleaner internal navigation
    st.switch_page("Admin_Dashboard")
    st.stop() # Stop script execution to prevent rendering login page content below

# If not logged in and no pending redirect, display login prompt
if not st.session_state.logged_in_user_info and not st.session_state.should_redirect_after_login:
    print(f"Displaying 'Please log in' prompt.")
    st.info("Please log in to access the admin dashboard.")

print(f"--- Login.py Script End --- Time: {time.time()}")