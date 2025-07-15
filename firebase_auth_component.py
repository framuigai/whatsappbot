# firebase_auth_component.py
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
        <script src="https://cdn.jsdelivr.net/npm/@streamlit/streamlit-component-lib@1.5.0/dist/streamlit-component-lib.js"></script>
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

            // Function to send authentication status to Streamlit
            function sendStatus(user) {{
                if (user) {{
                    user.getIdToken().then(token => {{
                        Streamlit.setComponentValue(JSON.stringify({{
                            loggedIn: true,
                            email: user.email,
                            uid: user.uid,
                            idToken: token
                        }}));
                    }});
                }} else {{
                    Streamlit.setComponentValue(JSON.stringify({{ loggedIn: false }}));
                }}
            }}

            // Function to update the UI based on authentication state
            function updateUI(user) {{
                if (user) {{
                    // If logged in, hide login UI, show logout UI
                    emailInput.style.display = 'none';
                    passwordInput.style.display = 'none';
                    loginBtn.style.display = 'none';
                    logoutBtn.style.display = 'inline-block';
                    status.textContent = `Logged in as ${{user.email}}`;
                }} else {{
                    // If logged out, show login UI, hide logout UI
                    emailInput.style.display = 'inline-block';
                    passwordInput.style.display = 'inline-block';
                    loginBtn.style.display = 'inline-block';
                    logoutBtn.style.display = 'none';
                    status.textContent = 'Please log in.';
                }}
            }}

            loginBtn.addEventListener("click", async () => {{
                try {{
                    const userCredential = await signInWithEmailAndPassword(auth, emailInput.value, passwordInput.value);
                    status.textContent = "Login successful!";
                    // The onAuthStateChanged listener will handle UI update and sending status
                }} catch (e) {{
                    status.textContent = "Login failed: " + e.message;
                    sendStatus(null); // Ensure Streamlit state is updated even on login failure
                    updateUI(null); // Explicitly update UI to logged out state
                }}
            }});

            logoutBtn.addEventListener("click", async () => {{
                try {{
                    await signOut(auth);
                    status.textContent = "Logged out.";
                    // The onAuthStateChanged listener will handle UI update and sending status
                }} catch (e) {{
                    status.textContent = "Error logging out: " + e.message;
                }}
            }});

            // IMPORTANT: This listener is the primary way to manage UI and Streamlit state
            // It runs whenever the authentication state changes (login, logout, page refresh)
            onAuthStateChanged(auth, (user) => {{
                sendStatus(user); // Always send the current status to Streamlit
                updateUI(user); // Always update UI based on current auth state
            }});

            Streamlit.setComponentReady();
            // The initial UI state will be handled by the onAuthStateChanged listener when the component loads.
        </script>
    </body>
    </html>
    """

    return components.html(component_html, height=450, scrolling=False)