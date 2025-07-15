# Home.py
import streamlit as st
from auth_utils import init_session_state, add_logout_button

# Initialize session state for all pages
init_session_state()

st.set_page_config(page_title="WhatsApp Bot App Home", layout="centered")

st.title("Welcome to the WhatsApp Bot Admin App!")
st.write("Please use the navigation in the sidebar to get started.")

# Show current login status in the main content area (optional)
if st.session_state.get("logged_in_user_info"):
    st.success(f"✅ Logged in as: {st.session_state.logged_in_user_info.get('email')}")
else:
    st.info("🔒 You are currently not logged in.")

st.sidebar.title("Navigation")
# Navigation links - using full paths for consistency with st.switch_page
st.sidebar.page_link("pages/Login.py", label="Login", icon="🔐")
st.sidebar.page_link("pages/Admin_Dashboard.py", label="Admin Dashboard", icon="📊")
st.sidebar.page_link("pages/Manage_Tenants.py", label="Manage Tenants", icon="👥")
st.sidebar.page_link("pages/View_Reports.py", label="View Reports", icon="📈")
st.sidebar.markdown("---")

# Add Logout button to the sidebar on the Home page too
add_logout_button()