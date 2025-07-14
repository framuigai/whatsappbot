# Home.py
import streamlit as st

st.set_page_config(page_title="WhatsApp Bot App Home", layout="centered")

st.title("Welcome to the WhatsApp Bot Admin App!")
st.write("Please use the navigation in the sidebar to get started.")

# These st.page_link calls generate links in the sidebar,
# they do NOT cause automatic page switches.
# Ensure correct casing for page names (e.g., "Login", "Admin_Dashboard")
st.page_link("pages/Login.py", label="Go to Login Page", icon="🔐")
st.page_link("pages/Admin_Dashboard.py", label="Go to Admin Dashboard", icon="📊")
st.page_link("pages/Manage_Tenants.py", label="Manage Tenants", icon="👥") # Added for completeness
st.page_link("pages/View_Reports.py", label="View Reports", icon="📈") # Added for completeness

st.info("Navigate to the 'Login' page to access the admin dashboard.")