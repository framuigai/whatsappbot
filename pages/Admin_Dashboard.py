# pages/Admin_Dashboard.py
import streamlit as st
import os
import json
from dotenv import load_dotenv

# Note: We no longer import firebase_auth_component here directly.
# The login status is maintained via st.session_state.

# Placeholder for db_utils functions (remove if you have your actual db_utils.py)
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
            ("What are your hours?", "We are open Monday to Friday, 9 AM to 5 PM."),
            ("Thank you!", "You're welcome!")
        ]
    return []

def get_tenant_id_from_whatsapp_phone_number(whatsapp_phone_number_id):
    st.info(f"DB: Getting tenant ID for WhatsApp Phone ID: {whatsapp_phone_number_id}...")
    return "my_initial_client_id"


load_dotenv()

st.set_page_config(page_title="WhatsApp Bot Admin Dashboard", layout="wide")
st.title("WhatsApp Bot Admin Dashboard")

# --- Authentication Check and Redirection ---
# If not logged in, redirect to login page and stop execution of this page.
if 'logged_in_user_info' not in st.session_state or not st.session_state.logged_in_user_info:
    st.warning("You are not logged in. Redirecting to login page...")
    st.switch_page("Login") # Correct: "Login" (page name, not "pages/Login.py")
    st.stop() # Important: Stop further execution of this page

# --- Dashboard Content (Only if logged in) ---

# Display user info and logout button at the top of the sidebar
st.sidebar.title("Dashboard Menu")
st.sidebar.write(f"**Logged in as:** {st.session_state.logged_in_user_info.get('email')}")

# Static Sidebar Menu Items
st.sidebar.markdown("---")
# Corrected page_link paths:
st.sidebar.page_link("Home.py", label="Home") # Home.py is in the root, so direct path
st.sidebar.page_link("pages/Admin_Dashboard.py", label="Dashboard Overview", icon="📊")
st.sidebar.page_link("pages/Manage_Tenants.py", label="Manage Tenants", icon="👥") # Added pages/ prefix
st.sidebar.page_link("pages/View_Reports.py", label="View Reports", icon="📈") # Added pages/ prefix
st.sidebar.markdown("---")

# Logout Button
if st.sidebar.button("Logout", key="sidebar_logout_button"):
    # Clear session state and redirect to login
    st.session_state.logged_in_user_info = None
    st.switch_page("Login") # Correct: "Login" (page name)


# --- Main Dashboard Functionality ---
st.subheader("Conversations Overview")
st.write("This section allows you to view and manage WhatsApp conversations per tenant.")

# Tenant ID input in the main area
selected_tenant_id = st.text_input("Enter Tenant ID", value="", key="main_tenant_id_input")

if selected_tenant_id:
    st.subheader(f"Conversations for Tenant: `{selected_tenant_id}`")

    # Display clients in the sidebar for selection for this tenant
    # This part of the sidebar is dynamic based on tenant selection
    st.sidebar.subheader("Clients for Tenant")
    wa_ids = get_all_wa_ids(selected_tenant_id)

    if not wa_ids:
        st.info(f"No conversations found for tenant `{selected_tenant_id}` yet.")
        st.sidebar.info("No WhatsApp users found for this tenant.")
    else:
        # Provide a unique key for the selectbox
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
            st.info("Please select a WhatsApp user to view chat history.")
else:
    st.info("Please enter a Tenant ID above to view conversations and select clients.")