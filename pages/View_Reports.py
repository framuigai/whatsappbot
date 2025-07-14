# pages/View_Reports.py
import streamlit as st

st.set_page_config(page_title="View Reports", layout="wide")

# Authentication check for this page
if 'logged_in_user_info' not in st.session_state or not st.session_state.logged_in_user_info:
    st.warning("You are not logged in. Redirecting to login page...")
    st.switch_page("Login") # Corrected: Just the page name, assuming Login.py is in pages/
    st.stop() # Stop further execution

st.title("View Reports")
st.write("This section will display various reports on bot activity, usage, etc.")
st.info(f"Logged in as: {st.session_state.logged_in_user_info.get('email')}")

# Add your reporting UI here (e.g., charts, tables of metrics)
st.write("---")
st.subheader("Conversation Volume Report")
st.line_chart({"Day 1": 10, "Day 2": 15, "Day 3": 8, "Day 4": 20}) # Example chart

st.subheader("FAQ Usage Breakdown")
st.bar_chart({"FAQ 1": 50, "FAQ 2": 30, "FAQ 3": 20}) # Example bar chart