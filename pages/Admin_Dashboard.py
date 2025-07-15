# pages/Admin_Dashboard.py
import streamlit as st
import os
import json
from dotenv import load_dotenv
from auth_utils import auth_guard, add_logout_button, init_session_state

# IMPORTANT: Initialize session state and perform auth guard at the very top
init_session_state()
auth_guard() # This will redirect to "pages/Login.py" if not logged in and stops execution

st.set_page_config(page_title="Admin Dashboard", layout="wide")
st.title("Admin Dashboard")

# Consistent Sidebar Navigation
st.sidebar.title("Menu")
if st.session_state.logged_in_user_info:
    st.sidebar.write(f"**Logged in as:** {st.session_state.logged_in_user_info.get('email')}")
st.sidebar.markdown("---")
st.sidebar.page_link("Home.py", label="Home")
st.sidebar.page_link("pages/Admin_Dashboard.py", label="Dashboard", icon="📊")
st.sidebar.page_link("pages/Manage_Tenants.py", label="Manage Tenants", icon="👥")
st.sidebar.page_link("pages/View_Reports.py", label="View Reports", icon="📈")
st.sidebar.markdown("---")

# Add Consistent Logout Button
add_logout_button()

# Placeholder for db_utils functions (replace with actual imports from your db_utils.py)
def get_all_wa_ids(tenant_id):
    st.info(f"DB: Fetching WhatsApp IDs for tenant '{tenant_id}'...")
    if tenant_id == "my_initial_client_id":
        return ["whatsapp:+1234567890", "whatsapp:+1987654321"]
    return []

def get_message_history(wa_id, tenant_id, limit=50):
    st.info(f"DB: Fetching message history for {wa_id} under tenant '{tenant_id}' (limit {limit})...")
    if wa_id == "whatsapp:+1234567890":
        return [
            ("Hello bot!", "Hi there! How can I help you?"),
            ("What are your hours?","We are open Monday to Friday, 9 AM to 5 PM."),
            ("Thank you!", "You're welcome!")
        ]
    return []

def get_tenant_id_from_whatsapp_phone_number(whatsapp_phone_number_id):
    st.info(f"DB: Getting tenant ID for WhatsApp Phone ID: {whatsapp_phone_number_id}...")
    if whatsapp_phone_number_id == os.getenv("WHATSAPP_PHONE_NUMBER_ID"):
        return "my_initial_client_id"
    return None

load_dotenv() # Ensure .env variables are loaded for this page if needed

st.subheader("Welcome to the Admin Dashboard!")
st.write("This dashboard provides an overview of your WhatsApp bot's activity.")
st.write("Use the sidebar to navigate to other management sections.")

st.subheader("Conversations Overview")
selected_tenant_id = st.text_input("Enter Tenant ID", value="", key="main_tenant_id_input")

if selected_tenant_id:
    st.subheader(f"Conversations for Tenant: `{selected_tenant_id}`")

    st.sidebar.subheader("Clients for Tenant")
    wa_ids = get_all_wa_ids(selected_tenant_id)

    if not wa_ids:
        st.info(f"No conversations found for tenant `{selected_tenant_id}` yet.")
        st.sidebar.info("No WhatsApp users found for this tenant.")
    else:
        selected_wa_id = st.sidebar.selectbox("Select a WhatsApp User:", wa_ids, key="whatsapp_user_select")

        if selected_wa_id:
            st.subheader(f"Chat History with {selected_wa_id}")
            history = get_message_history(selected_wa_id, selected_tenant_id, limit=50)

            if history:
                for sender_msg, bot_msg in history:
                    if sender_msg:
                        st.chat_message("user").write(sender_msg)
                    if bot_msg:
                        st.chat_message("assistant").write(bot_msg)
            else:
                st.info("No chat history found for this user within this tenant.")
        else:
            st.info("Select a WhatsApp user from the sidebar to view chat history.")
else:
    st.info("Enter a Tenant ID to view conversations.")