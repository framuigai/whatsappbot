e # admin_dashboard.py
import streamlit as st
import os
from dotenv import load_dotenv # Assuming you might load secrets from .env locally
# ... your firebase_auth_component and firebase_admin_utils imports ...
from db_utils import get_all_wa_ids, get_message_history # Ensure these are updated

load_dotenv() # Load .env if you're keeping tenant IDs there for local dev

st.set_page_config(page_title="WhatsApp Bot Admin", layout="wide")
st.title("WhatsApp Bot Admin Dashboard")

# --- TENANT SELECTION IN DASHBOARD ---
# For testing, you can hardcode it or use a simple input.
# Later, this would be tied to the logged-in admin user's permissions.
# Example: if you only have one client initially, you can hardcode
# selected_tenant_id = os.getenv("DEFAULT_TENANT_ID", "default_client")

# For multiple tenants, you'd have a dropdown or input:
# Option 1: Manually enter tenant ID (good for initial testing)
selected_tenant_id = st.sidebar.text_input("Enter Tenant ID", value=os.getenv("DEFAULT_TENANT_ID", "default_client_id"))

# Option 2: Select from a predefined list (better as you add clients)
# tenant_options = ["client_a", "client_b", "client_c"] # Or fetch from a config/Firebase
# selected_tenant_id = st.sidebar.selectbox("Select Client/Tenant", tenant_options)
# ------------------------------------

# Assuming authentication is handled and user is logged in
# if st.session_state.logged_in: # Placeholder from Week 4 roadmap
if selected_tenant_id: # For now, just check if a tenant ID is provided
    st.subheader(f"Conversations for Tenant: `{selected_tenant_id}`")

    # Get and display client WA IDs for the selected tenant
    wa_ids = get_all_wa_ids(selected_tenant_id)
    if not wa_ids:
        st.info(f"No conversations found for tenant `{selected_tenant_id}` yet.")
    else:
        st.sidebar.subheader("Clients")
        selected_wa_id = st.sidebar.selectbox("Select a WhatsApp User:", wa_ids)

        if selected_wa_id:
            st.subheader(f"Chat History with {selected_wa_id}")
            # Get message history for the selected wa_id AND tenant_id
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
    st.warning("Please enter a Tenant ID to view conversations.")