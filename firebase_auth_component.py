import streamlit.components.v1 as components
import os
import json
from dotenv import load_dotenv

load_dotenv()

def firebase_auth_component(key=None):
    firebase_config = {
        "apiKey": os.getenv("FIREBASE_API_KEY"),
        "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
        "projectId": os.getenv("FIREBASE_PROJECT_ID"),
        "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
        "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
        "appId": os.getenv("FIREBASE_APP_ID")
    }
    firebase_config_json = json.dumps(firebase_config)

    component_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <script type="module" src="https://www.gstatic.com/firebasejs/9.22.0/firebase-app.js"></script>
        <script type="module" src="https://www.gstatic.com/firebasejs/9.22.0/firebase-auth.js"></script>
        <script src="/static/js/streamlit-component-lib.js"></script>
        <script>
            document.addEventListener("DOMContentLoaded", function() {{
                if (typeof Streamlit === 'undefined') {{
                    console.error("❌ Streamlit library not loaded!");
                }}
            }});
        </script>
    </head>
    <body>
        <div>
            <input type="email" id="email" placeholder="Email">
            <input type="password" id="password" placeholder="Password">
            <button id="loginBtn">Login</button>
            <p id="status"></p>
            <button id="logoutBtn" style="display:none;">Logout</button>
        </div>
        <script type="module">
            import {{ initializeApp }} from "https://www.gstatic.com/firebasejs/9.22.0/firebase-app.js";
            import {{ getAuth, signInWithEmailAndPassword, signOut, onAuthStateChanged }} from "https://www.gstatic.com/firebasejs/9.22.0/firebase-auth.js";

            const config = {firebase_config_json};
            const app = initializeApp(config);
            const auth = getAuth(app);

            const loginBtn = document.getElementById("loginBtn");
            const logoutBtn = document.getElementById("logoutBtn");
            const emailInput = document.getElementById("email");
            const passwordInput = document.getElementById("password");
            const status = document.getElementById("status");

            function sendStatus(user) {{
                if (typeof Streamlit === "undefined") {{
                    console.error("❌ Streamlit is not available.");
                    return;
                }}
                if (user) {{
                    user.getIdToken().then(token => {{
                        Streamlit.setComponentValue({{
                            loggedIn: true,
                            email: user.email,
                            uid: user.uid,
                            idToken: token
                        }});
                    }});
                }} else {{
                    Streamlit.setComponentValue({{ loggedIn: false }});
                }}
            }}

            function updateUI(user) {{
                if (user) {{
                    emailInput.style.display = 'none';
                    passwordInput.style.display = 'none';
                    loginBtn.style.display = 'none';
                    logoutBtn.style.display = 'inline-block';
                    status.textContent = `Logged in as ${{user.email}}`;
                }} else {{
                    emailInput.style.display = 'inline-block';
                    passwordInput.style.display = 'inline-block';
                    loginBtn.style.display = 'inline-block';
                    logoutBtn.style.display = 'none';
                    status.textContent = 'Please log in.';
                }}
            }}

            loginBtn.addEventListener("click", async () => {{
                try {{
                    await signInWithEmailAndPassword(auth, emailInput.value, passwordInput.value);
                    status.textContent = "Login successful!";
                }} catch (e) {{
                    status.textContent = "Login failed: " + e.message;
                    sendStatus(null);
                    updateUI(null);
                }}
            }});

            logoutBtn.addEventListener("click", async () => {{
                try {{
                    await signOut(auth);
                    status.textContent = "Logged out.";
                }} catch (e) {{
                    status.textContent = "Error logging out: " + e.message;
                }}
            }});

            onAuthStateChanged(auth, (user) => {{
                sendStatus(user);
                updateUI(user);
            }});

            if (typeof Streamlit !== "undefined") {{
                Streamlit.setComponentReady();
            }}
        </script>
    </body>
    </html>
    """
    return components.html(component_html, height=450, scrolling=False)
