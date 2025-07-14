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
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Firebase Auth</title>
        <script type="module" src="https://www.gstatic.com/firebasejs/9.22.0/firebase-app.js"></script>
        <script type="module" src="https://www.gstatic.com/firebasejs/9.22.0/firebase-auth.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/@streamlit/streamlit-component-lib@1.5.0/dist/streamlit-component-lib.js"></script>
        <style>
            body {{ font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; background-color: #f0f2f6; color: #333; }}
            .container {{ background-color: #ffffff; padding: 25px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); width: 100%; max-width: 380px; text-align: center; }}
            h2 {{ color: #4CAF50; margin-bottom: 20px; }}
            input[type="email"], input[type="password"] {{ width: calc(100% - 20px); padding: 10px; margin-bottom: 15px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }}
            button {{ background-color: #4CAF50; color: white; padding: 12px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; width: 100%; transition: background-color 0.3s ease; }}
            button:hover {{ background-color: #45a049; }}
            .error {{ color: red; margin-top: 10px; font-size: 0.9em; }}
            .status {{ color: #007bff; margin-top: 10px; font-size: 0.9em; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2 id="auth-title">Admin Login</h2>
            <div id="auth-form">
                <input type="email" id="email" placeholder="Email" required>
                <input type="password" id="password" placeholder="Password" required>
                <button id="loginButton">Login</button>
                <div id="auth-error" class="error"></div>
                <div id="auth-status" class="status"></div>
            </div>
            <div id="logged-in-info" style="display: none;">
                <p>Logged in as: <strong id="user-email"></strong></p>
                <button id="logoutButton">Logout</button>
            </div>
        </div>

        <script type="module">
            import {{ initializeApp }} from "https://www.gstatic.com/firebasejs/9.22.0/firebase-app.js";
            import {{ getAuth, signInWithEmailAndPassword, signOut, onAuthStateChanged }} from "https://www.gstatic.com/firebasejs/9.22.0/firebase-auth.js";

            const firebaseConfig = {firebase_config_json}; // This one remains single braces!
            const app = initializeApp(firebaseConfig);
            const auth = getAuth(app);

            const emailInput = document.getElementById('email');
            const passwordInput = document.getElementById('password');
            const loginButton = document.getElementById('loginButton');
            const logoutButton = document.getElementById('logoutButton');
            const authErrorDiv = document.getElementById('auth-error');
            const authStatusDiv = document.getElementById('auth-status');
            const authForm = document.getElementById('auth-form');
            const loggedInInfo = document.getElementById('logged-in-info');
            const userEmailSpan = document.getElementById('user-email');

            function sendAuthStatusToStreamlit(user) {{ // Doubled for function body
                if (user) {{ // Doubled for if condition body
                    user.getIdToken().then(idToken => {{ // Doubled for .then callback body
                        Streamlit.setComponentValue({{ // Doubled for JS object literal
                            uid: user.uid,
                            email: user.email,
                            idToken: idToken,
                            loggedIn: true
                        }});
                    }}).catch(error => {{ // Doubled for .catch callback body
                        console.error("Error getting ID token:", error);
                        authErrorDiv.textContent = "Failed to get user token.";
                        Streamlit.setComponentValue({{ loggedIn: false }}); // Doubled for JS object literal
                    }});
                }} else {{ // Doubled for else condition body
                    Streamlit.setComponentValue({{ loggedIn: false }}); // Doubled for JS object literal
                }}
            }}

            loginButton.addEventListener('click', async () => {{ // Doubled for arrow function body
                const email = emailInput.value;
                const password = passwordInput.value;
                authErrorDiv.textContent = '';
                authStatusDiv.textContent = 'Logging in...';

                try {{ // Doubled for try block
                    const userCredential = await signInWithEmailAndPassword(auth, email, password);
                    authStatusDiv.textContent = 'Login successful!';
                }} catch (error) {{ // Doubled for catch block
                    console.error("Login Error:", error);
                    let errorMessage = "Login failed. Please check your credentials.";
                    if (error.code === 'auth/user-not-found' || error.code === 'auth/wrong-password') {{ // Doubled for if block
                        errorMessage = "Invalid email or password.";
                    }} else if (error.code === 'auth/too-many-requests') {{ // Doubled for else if block
                        errorMessage = "Too many login attempts. Try again later.";
                    }}
                    authErrorDiv.textContent = errorMessage;
                    authStatusDiv.textContent = '';
                    sendAuthStatusToStreamlit(null);
                }}
            }});

            logoutButton.addEventListener('click', async () => {{ // Doubled for arrow function body
                try {{ // Doubled for try block
                    await signOut(auth);
                    authStatusDiv.textContent = 'Logged out successfully.';
                    authErrorDiv.textContent = '';
                }} catch (error) {{ // Doubled for catch block
                    console.error("Logout Error:", error);
                    authErrorDiv.textContent = "Error logging out.";
                }}
            }});

            onAuthStateChanged(auth, (user) => {{ // Doubled for callback body
                if (user) {{ // Doubled for if block
                    userEmailSpan.textContent = user.email;
                    authForm.style.display = 'none';
                    loggedInInfo.style.display = 'block';
                    authErrorDiv.textContent = '';
                    authStatusDiv.textContent = '';
                    sendAuthStatusToStreamlit(user);
                }} else {{ // Doubled for else block
                    authForm.style.display = 'block';
                    loggedInInfo.style.display = 'none';
                    sendAuthStatusToStreamlit(null);
                }}
            }});

            // Send an initial 'logged out' status immediately when component is ready.
            // This ensures Streamlit always receives a dictionary value, avoiding initial None/ambiguous states.
            Streamlit.setComponentReady();
            auth.onAuthStateChanged(user => {{ // Doubled for arrow function body
                if (!user) {{ // Doubled for if block
                    Streamlit.setComponentValue({{ loggedIn: false }}); // Doubled for JS object literal
                }}
            }});
        </script>
    </body>
    </html>
    """
    component_value = components.html(component_html, height=450, scrolling=False)
    return component_value