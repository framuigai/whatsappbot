# pages/View_Reports.py
import streamlit as st
from auth_utils import auth_guard, add_logout_button, init_session_state

# IMPORTANT: Initialize session state and perform auth guard at the very top
init_session_state()

st.set_page_config(page_title="View Reports", layout="wide")

# Authentication Check - MUST be at the very top of restricted pages
auth_guard() # This will redirect to "pages/Login.py" if not authenticated and stops execution

st.title("View Reports")

# Consistent Sidebar Navigation
st.sidebar.title("Menu")
if st.session_state.logged_in_user_info:
    st.sidebar.write(f"**Logged in as:** {st.session_state.logged_in_user_info.get('email')}")
st.sidebar.markdown("---")
st.sidebar.page_link("Home.py", label="Home")
st.sidebar.page_link("pages/Admin_Dashboard.py", label="Dashboard", icon="📊")
st.sidebar.page_link("pages/Manage_Tenants.py", label="Manage Tenants", icon="👥")
st.sidebar.page_link("pages/View_Reports.py", label="View Reports", icon="📈") # Self-link
st.sidebar.markdown("---")

# Add Consistent Logout Button
add_logout_button()

# Main Content for View Reports
st.info(f"Logged in as: {st.session_state.logged_in_user_info.get('email')}")

st.subheader("Overall Bot Metrics")
st.write("Metrics and analytics will be displayed here.")

st.subheader("Conversation Volume Report")
st.line_chart({"Day 1": 10, "Day 2": 15, "Day 3": 8, "Day 4": 20})

st.subheader("FAQ Usage Breakdown")
st.bar_chart({"FAQ 1": 50, "FAQ 2": 30, "FAQ 3": 20})

st.subheader("User Engagement")
st.metric(label="Total Active Users", value="150")
st.metric(label="Average Messages / User", value="7.2")