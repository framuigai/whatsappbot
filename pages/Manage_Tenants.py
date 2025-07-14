# pages/Manage_Tenants.py
import streamlit as st

st.set_page_config(page_title="Manage Tenants", layout="wide")

# Authentication check for this page
if 'logged_in_user_info' not in st.session_state or not st.session_state.logged_in_user_info:
    st.warning("You are not logged in. Redirecting to login page...")
    st.switch_page("Login") # Corrected: Just the page name, assuming Login.py is in pages/
    st.stop() # Stop further execution

st.title("Manage Tenants")
st.write("This is where you would manage your tenant configurations.")
st.info(f"Logged in as: {st.session_state.logged_in_user_info.get('email')}")

# Add your tenant management UI here (e.g., forms, tables for tenant data)
st.write("---")
st.subheader("Add New Tenant")
tenant_name = st.text_input("Tenant Name")
tenant_id = st.text_input("Tenant ID (e.g., unique identifier)")
whatsapp_phone_id = st.text_input("WhatsApp Phone Number ID (from Meta/WhatsApp Business Account)")

if st.button("Add Tenant"):
    if tenant_name and tenant_id and whatsapp_phone_id:
        # You'd call your db_utils.add_tenant_config here
        # db_utils.add_tenant_config(whatsapp_phone_id, tenant_id, tenant_name)
        st.success(f"Tenant '{tenant_name}' (ID: {tenant_id}) added successfully! (Placeholder)")
    else:
        st.error("Please fill in all tenant details.")

st.subheader("Existing Tenants")
st.write("List and edit existing tenants here.")
# Example: Use db_utils.get_all_tenants() and display in a table