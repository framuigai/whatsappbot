// static/js/firebase-init.js
// This script runs on the login.html page and potentially other pages like dashboard.html.

// Check if firebaseConfig is defined (it's injected by Flask in login.html and should be in dashboard.html now)
if (typeof firebaseConfig === 'undefined') {
    console.error("Firebase config not found! Make sure it's injected by Flask.");
} else {
    // Initialize Firebase
    const app = firebase.initializeApp(firebaseConfig);
    const auth = firebase.auth(); // Use firebase.auth() for compat version

    // Get elements for login functionality (these are from login.html)
    const loginBtn = document.getElementById("loginBtn");
    const emailInput = document.getElementById("email");
    const passwordInput = document.getElementById("password");
    const statusDiv = document.getElementById("status"); // This div only exists on login.html

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
                if (statusDiv) { // statusDiv only exists on login.html, so check if it exists before using
                    statusDiv.textContent = data.message;
                    statusDiv.style.color = 'green';
                }
                console.log("Flask login API success:", data);
                // Redirect to dashboard on successful login, if not already there
                if (window.location.pathname !== '/dashboard') {
                    window.location.href = '/dashboard'; // Redirect using standard browser navigation
                }
            } else {
                if (statusDiv) { // statusDiv only exists on login.html
                    statusDiv.textContent = `Login failed: ${data.message || 'Unknown error'}`;
                    statusDiv.style.color = 'red';
                }
                console.error("Flask login API error:", data);
            }
        } catch (error) {
            if (statusDiv) { // statusDiv only exists on login.html
                statusDiv.textContent = `Network error: ${error.message}`;
                statusDiv.style.color = 'red';
            }
            console.error("Error sending ID token to Flask:", error);
        }
    }

    // Handle login button click (from login.html)
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
                statusDiv.style.color = 'black'; // Reset color
            }

            try {
                const userCredential = await auth.signInWithEmailAndPassword(email, password);
                const user = userCredential.user;
                const idToken = await user.getIdToken();
                console.log("Firebase login successful, ID Token obtained.");
                await sendIdTokenToFlask(idToken); // Send token to Flask backend
            } catch (error) {
                if (statusDiv) {
                    statusDiv.textContent = `Login failed: ${error.message}`;
                    statusDiv.style.color = 'red';
                }
                console.error("Firebase login error:", error);
            }
        });
    } else {
        console.warn("Login button not found (this is expected if script is on non-login page).");
    }

    // Handle logout button click (from dashboard.html)
    const logoutButton = document.getElementById('logout-button');

    if (logoutButton) {
        logoutButton.addEventListener('click', function(event) {
            event.preventDefault(); // IMPORTANT: Prevent default link navigation

            // 1. Sign out from Firebase on the client-side first
            firebase.auth().signOut().then(function() {
                // Firebase client-side sign-out successful
                console.log("Firebase client-side sign-out successful.");
                // 2. Now, redirect to Flask's logout route to clear server-side session
                window.location.href = '/logout';
            }).catch(function(error) {
                // An error occurred during Firebase client-side sign-out
                console.error("Firebase client-side sign-out failed:", error);
                alert('Error logging out from Firebase. Please try again.');
                // Even if client-side signOut fails, still attempt server-side logout
                window.location.href = '/logout';
            });
        });
    } else {
        console.warn("Logout button not found (this is expected if script is on non-dashboard page or button ID is different).");
    }

    // Handle initial auth state (e.g., if user is already logged in from a previous session)
    // This will run on page load for all pages that include this script.
    auth.onAuthStateChanged(async (user) => {
        if (user) {
            console.log("Firebase onAuthStateChanged: User is logged in.", user.email);
            // If user is logged in via Firebase:
            // - If on the login page, redirect to dashboard.
            // - If on any other page (like dashboard), re-establish Flask session if needed.
            if (window.location.pathname === '/login') {
                console.log("Firebase user detected on login page, redirecting to dashboard.");
                // We don't need to call sendIdTokenToFlask here directly,
                // as /dashboard will handle Flask-Login's @login_required,
                // and if the Flask session is truly gone, it will prompt /api/login there.
                // The main goal here is to get them OFF the login page.
                window.location.href = '/dashboard';
            } else {
                // User is on a protected page (e.g., dashboard) and Flask session might be gone.
                // Send token to Flask to ensure Flask session is re-established.
                // This will also redirect to /dashboard if the call is successful.
                const idToken = await user.getIdToken();
                await sendIdTokenToFlask(idToken);
            }
        } else {
            // No user is signed in with Firebase.
            console.log("Firebase onAuthStateChanged: User is logged out.");
            // Ensure status is clear on login page if no user
            if (statusDiv && window.location.pathname === '/login') {
                statusDiv.textContent = 'Please log in.';
                statusDiv.style.color = 'black';
            }
        }
    });
}