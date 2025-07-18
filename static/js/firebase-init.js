// static/js/firebase-init.js
// This script runs on the login.html page.

// Check if firebaseConfig is defined (it's injected by Flask in login.html)
if (typeof firebaseConfig === 'undefined') {
    console.error("Firebase config not found! Make sure it's injected by Flask.");
} else {
    // Initialize Firebase
    const app = firebase.initializeApp(firebaseConfig);
    const auth = firebase.auth(); // Use firebase.auth() for compat version

    const loginBtn = document.getElementById("loginBtn");
    const emailInput = document.getElementById("email");
    const passwordInput = document.getElementById("password");
    const statusDiv = document.getElementById("status");

    // Function to send Firebase ID Token to Flask backend
    async function sendIdTokenToFlask(idToken) {
        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${idToken}` // Send token in Authorization header
                },
                body: JSON.stringify({ idToken: idToken }) // Also send in body for Flask's request.json.get
            });

            const data = await response.json();

            if (response.ok) {
                statusDiv.textContent = data.message;
                statusDiv.style.color = 'green';
                console.log("Flask login API success:", data);
                // Redirect to dashboard on successful login
                window.location.href = '/dashboard'; // Redirect using standard browser navigation
            } else {
                statusDiv.textContent = `Login failed: ${data.message || 'Unknown error'}`;
                statusDiv.style.color = 'red';
                console.error("Flask login API error:", data);
            }
        } catch (error) {
            statusDiv.textContent = `Network error: ${error.message}`;
            statusDiv.style.color = 'red';
            console.error("Error sending ID token to Flask:", error);
        }
    }

    // Handle login button click
    if (loginBtn) {
        loginBtn.addEventListener("click", async () => {
            const email = emailInput.value;
            const password = passwordInput.value;

            if (!email || !password) {
                statusDiv.textContent = "Please enter both email and password.";
                statusDiv.style.color = 'red';
                return;
            }

            statusDiv.textContent = "Logging in...";
            statusDiv.style.color = 'black'; // Reset color

            try {
                const userCredential = await auth.signInWithEmailAndPassword(email, password);
                const user = userCredential.user;
                const idToken = await user.getIdToken();
                console.log("Firebase login successful, ID Token obtained.");
                await sendIdTokenToFlask(idToken); // Send token to Flask backend
            } catch (error) {
                statusDiv.textContent = `Login failed: ${error.message}`;
                statusDiv.style.color = 'red';
                console.error("Firebase login error:", error);
            }
        });
    } else {
        console.error("Login button not found!");
    }

    // Handle initial auth state (e.g., if user is already logged in from a previous session)
    // This will also run on page load.
    auth.onAuthStateChanged(async (user) => {
        if (user) {
            console.log("Firebase onAuthStateChanged: User is logged in.", user.email);
            // If user is logged in via Firebase, ensure Flask also has a session
            // This is important for page reloads or direct navigation to protected pages
            const idToken = await user.getIdToken();
            // Only send token to Flask if we are on the login page,
            // or if we need to re-establish Flask session
            if (window.location.pathname === '/login') {
                await sendIdTokenToFlask(idToken);
            }
        } else {
            console.log("Firebase onAuthStateChanged: User is logged out.");
            // Ensure status is clear if no user
            if (statusDiv) {
                statusDiv.textContent = 'Please log in.';
                statusDiv.style.color = 'black';
            }
        }
    });
}