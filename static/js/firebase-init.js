// static/js/firebase-init.js

if (typeof firebaseConfig === 'undefined' || firebaseConfig.disabled === true || window.FIREBASE_ENABLED === false) {
    console.warn("🔧 Firebase is disabled or config missing. Skipping Firebase initialization.");
} else {
    // Initialize Firebase
    if (!firebase.apps.length) {
        firebase.initializeApp(firebaseConfig);
    }
    const auth = firebase.auth();

    const loginBtn = document.getElementById("loginBtn");
    const emailInput = document.getElementById("email");
    const passwordInput = document.getElementById("password");
    const statusDiv = document.getElementById("status");
    const logoutButton = document.getElementById("logout-button");

    async function sendIdTokenToFlask(idToken) {
        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${idToken}` },
                body: JSON.stringify({ idToken: idToken })
            });

            const data = await response.json();

            if (response.ok) {
                console.log("✅ Flask session established via Firebase:", data);
                if (statusDiv) {
                    statusDiv.textContent = data.message;
                    statusDiv.style.color = 'green';
                }
                if (window.location.pathname === '/login' || window.location.pathname === '/login/') {
                    window.location.href = '/';
                }
            } else {
                console.error("❌ Flask login API error:", data);
                if (statusDiv) {
                    statusDiv.textContent = `Login failed: ${data.message || 'Unknown error'}`;
                    statusDiv.style.color = 'red';
                }
            }
        } catch (error) {
            console.error("❌ Error sending ID token to Flask:", error);
            if (statusDiv) {
                statusDiv.textContent = `Network error: ${error.message}`;
                statusDiv.style.color = 'red';
            }
        }
    }

    if (loginBtn) {
        loginBtn.addEventListener("click", async () => {
            const email = emailInput.value;
            const password = passwordInput.value;

            if (!email || !password) {
                if (statusDiv) {
                    statusDiv.textContent = "Please enter both email and password.";
                    statusDiv.style.color = 'red';
                }
                return;
            }

            if (statusDiv) {
                statusDiv.textContent = "Logging in...";
                statusDiv.style.color = 'black';
            }

            try {
                const userCredential = await auth.signInWithEmailAndPassword(email, password);
                const user = userCredential.user;
                const idToken = await user.getIdToken();
                console.log("✅ Firebase login successful. Sending ID token to Flask.");
                await sendIdTokenToFlask(idToken);
            } catch (error) {
                console.error("❌ Firebase login error:", error);
                if (statusDiv) {
                    statusDiv.textContent = `Login failed: ${error.message}`;
                    statusDiv.style.color = 'red';
                }
            }
        });
    }

    if (logoutButton) {
        logoutButton.addEventListener('click', function(event) {
            event.preventDefault();
            auth.signOut().then(() => {
                console.log("✅ Firebase sign-out successful.");
                window.location.href = '/logout';
            }).catch(error => {
                console.error("❌ Firebase sign-out failed:", error);
                window.location.href = '/logout';
            });
        });
    }

    auth.onAuthStateChanged(async (user) => {
        if (user) {
            console.log("ℹ️ Firebase onAuthStateChanged: User is logged in:", user.email);
            if (window.location.pathname === '/login' || window.location.pathname === '/login/') {
                const idToken = await user.getIdToken();
                await sendIdTokenToFlask(idToken);
            }
        } else {
            console.log("ℹ️ Firebase onAuthStateChanged: User is logged out.");
            if (statusDiv && (window.location.pathname === '/login' || window.location.pathname === '/login/')) {
                statusDiv.textContent = 'Please log in.';
                statusDiv.style.color = 'black';
            }
        }
    });
}
