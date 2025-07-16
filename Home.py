import streamlit as st
from auth_utils import init_session_state, add_logout_button
import os

# ✅ Ensure Streamlit knows about static assets (like the JS library)
# Injects <base> tag so that iframe and scripts load properly
st.markdown("""
    <head>
        <base href="/" />
    </head>
""", unsafe_allow_html=True)

# ✅ Initialize session state for all pages
init_session_state()

# ✅ Page configuration
st.set_page_config(page_title="WhatsApp Bot App Home", layout="centered")

# ✅ Title and instructions
st.title("Welcome to the WhatsApp Bot Admin App!")
st.write("Please use the navigation in the sidebar to get started.")

# ✅ Show login status
if st.session_state.get("logged_in_user_info"):
    st.success(f"✅ Logged in as: {st.session_state.logged_in_user_info.get('email')}")
else:
    st.info("🔒 You are currently not logged in.")

# ✅ Sidebar navigation
st.sidebar.title("Navigation")
st.sidebar.page_link("pages/Login.py", label="Login", icon="🔐")
st.sidebar.page_link("pages/Admin_Dashboard.py", label="Admin Dashboard", icon="📊")
st.sidebar.page_link("pages/Manage_Tenants.py", label="Manage Tenants", icon="👥")
st.sidebar.page_link("pages/View_Reports.py", label="View Reports", icon="📈")
st.sidebar.markdown("---")

# ✅ Add logout button in sidebar
add_logout_button()

# ✅ Debug info (optional)
st.markdown(
    """
    <p style="font-size:12px; color:gray;">
        Static assets (JS/CSS) should load from <code>/static/</code>. 
        If you see any errors about <b>Streamlit not defined</b>, check the script path.
    </p>
    """, unsafe_allow_html=True
)
