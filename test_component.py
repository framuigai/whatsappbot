import streamlit.components.v1 as components

def test_component_html(key=None):
    return_value = "Hello from Component!"
    component_html = f"""
    <!DOCTYPE html>
    <html>
    <body>
        <p>This is a test component.</p>
        <script>
            // Send an initial value to Streamlit
            Streamlit.setComponentValue('{return_value}');
            Streamlit.setComponentReady();
        </script>
    </body>
    </html>
    """
    # components.html returns a DeltaGenerator object
    return components.html(component_html, height=100)