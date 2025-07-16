import streamlit as st
from test_component import test_component_html
import json # Just in case it's stringified

st.title("Component Value Test")

# Render the test component
component_output_delta = test_component_html(key="my_test_component")

# Access its value
raw_value = component_output_delta.value

st.write(f"Raw value from component.value: {raw_value}")
st.write(f"Type of raw_value: {type(raw_value)}")

if raw_value is not None and isinstance(raw_value, str):
    try:
        parsed_value = json.loads(raw_value)
        st.write(f"Parsed JSON value: {parsed_value}")
    except json.JSONDecodeError:
        st.write("Value is a string, but not valid JSON.")
elif raw_value is not None:
    st.write("Value is not a string, or None.")