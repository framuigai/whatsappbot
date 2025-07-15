# pages/Manage_Tenants.py
import streamlit as st
from auth_utils import auth_guard, add_logout_button, init_session_state

# IMPORTANT: Initialize session state and perform auth guard at the very top
init_session_state()

st.set_page_config(page_title="Manage Tenants", layout="wide")

# Authentication Check - MUST be at the very top of restricted pages
auth_guard() # This will redirect to "pages/Login.py" if not authenticated and stops execution

st.title("Manage Tenants")

# Consistent Sidebar Navigation
st.sidebar.title("Menu")
if st.session_state.logged_in_user_info:
    st.sidebar.write(f"**Logged in as:** {st.session_state.logged_in_user_info.get('email')}")
st.sidebar.markdown("---")
st.sidebar.page_link("Home.py", label="Home")
st.sidebar.page_link("pages/Admin_Dashboard.py", label="Dashboard", icon="📊")
st.sidebar.page_link("pages/Manage_Tenants.py", label="Manage Tenants", icon="👥") # Self-link
st.sidebar.page_link("pages/View_Reports.py", label="View Reports", icon="📈")
st.sidebar.markdown("---")

# Add Consistent Logout Button
add_logout_button()

# Main Content for Manage Tenants
st.info(f"Logged in as: {st.session_state.logged_in_user_info.get('email')}")

st.subheader("Add New Tenant")
tenant_name = st.text_input("Tenant Name", key="new_tenant_name")
tenant_id = st.text_input("Tenant ID", key="new_tenant_id")
whatsapp_id = st.text_input("WhatsApp Phone ID", key="new_whatsapp_id")

if st.button("Add Tenant"):
    if tenant_name and tenant_id and whatsapp_id:
        st.success(f"Tenant '{tenant_name}' added successfully!")
        st.session_state.new_tenant_name = ""
        st.session_state.new_tenant_id = ""
        st.session_state.new_whatsapp_id = ""
        st.experimental_rerun()
    else:
        st.error("Please fill all fields.")

st.subheader("Existing Tenants")
st.info("No tenants found yet. Add some above!")