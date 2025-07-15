# auth_utils.py
import streamlit as st
import json

def init_session_state():
    """
    Initializes necessary session state variables for authentication.
    Call this at the beginning of your main app file (e.g., Home.py)
    and at the very top of *every* page script.
    """
    if "logged_in_user_info" not in st.session_state:
        st.session_state.logged_in_user_info = None
    if "should_redirect_after_login" not in st.session_state:
        st.session_state.should_redirect_after_login = False
    # Add any other global session state variables here

def auth_guard(redirect_page="pages/Login.py"): # Consistent full path
    """
    Ensures user is authenticated. If not, redirects to login page.
    This should be called at the very top of restricted pages.
    """
    if 'logged_in_user_info' not in st.session_state or not st.session_state.logged_in_user_info:
        st.warning("You are not logged in. Redirecting to login page...")
        st.switch_page(redirect_page) # Uses the full path
        st.stop() # Stop further execution of the current page

def add_logout_button(redirect_page="pages/Login.py"): # Consistent full path
    """
    Adds a logout button to the sidebar for consistent logout across pages.
    """
    if st.sidebar.button("Logout", key="sidebar_logout_button"):
        st.session_state.logged_in_user_info = None
        st.session_state.should_redirect_after_login = False # Reset redirect flag
        st.success("Logged out successfully!")
        st.switch_page(redirect_page) # Uses the full path
        st.stop() # Stop execution after logout and redirect