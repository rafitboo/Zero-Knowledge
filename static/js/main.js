const statusBox = document.getElementById('statusBox');
const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

// Initialize the Bootstrap Modal
const otpModalElement = document.getElementById('otpModal');
const otpModal = new bootstrap.Modal(otpModalElement);


let currentAuthUser = "";
let otpActionContext = ""; 

function showMessage(msg, isError = false) {
    statusBox.classList.remove('d-none');
    statusBox.style.borderLeftColor = isError ? '#ff0055' : '#00ffcc';
    statusBox.style.color = isError ? '#ff0055' : '#00ffcc';
    statusBox.innerText = `> ${msg}`;
}

// --- 1. REGISTRATION LOGIC ---
document.getElementById('registerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    showMessage("Registering and wrapping credentials...");
    
    const payload = {
        username: document.getElementById('regUser').value,
        email: document.getElementById('regEmail').value,
        password: document.getElementById('regPass').value,
        contact_info: document.getElementById('regContact').value
    };

    try {
        const response = await fetch('/api/accounts/register/', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(payload)
        });
        const data = await response.json();

        if (response.ok) {
            showMessage("REGISTRATION SUCCESS. Awaiting email verification...");
            // Trigger the 2FA Popup
            currentAuthUser = payload.username;
            otpActionContext = 'register';
            document.getElementById('modalOtpCode').value = '';
            otpModal.show();
        } else {
            const errorMsg = data.error || JSON.stringify(data);
            showMessage(errorMsg, true);
        }
    } catch (err) {
        showMessage("Connection to authentication server failed.", true);
    }
});

// --- 2. LOGIN LOGIC (Step 1: Credentials) ---
document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    showMessage("Authenticating credentials...");
    
    const payload = {
        username: document.getElementById('loginUser').value,
        password: document.getElementById('loginPass').value
    };

    try {
        const response = await fetch('/api/accounts/login/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await response.json();

        if (response.ok) {
            showMessage("CREDENTIALS ACCEPTED. Enforcing 2FA protocol...");
            // Trigger the 2FA Popup
            currentAuthUser = payload.username;
            otpActionContext = 'login';
            document.getElementById('modalOtpCode').value = '';
            otpModal.show();
        } else {
            showMessage(data.error || "ACCESS DENIED.", true);
        }
    } catch (err) {
        showMessage("Connection to authentication server failed.", true);
    }
});

// --- 3. THE 2FA POPUP SUBMIT LOGIC (Step 2: Verification) ---
document.getElementById('modalOtpForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const otpCode = document.getElementById('modalOtpCode').value.trim();
    
    // Determine the correct backend endpoint and payload based on context
    const endpoint = otpActionContext === 'login' ? '/api/accounts/login/verify/' : '/api/accounts/verify-otp/';
    const payload = { username: currentAuthUser };
    
    // The backend uses different variable names for the two endpoints
    if (otpActionContext === 'login') {
        payload.otp = otpCode;
    } else {
        payload.otp_code = otpCode;
    }

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(payload)
        });
        const data = await response.json();

        if (response.ok) {
            otpModal.hide(); // Close the popup
            
            if (otpActionContext === 'login') {
                // Login complete - Save token and enter system
                localStorage.setItem('jwt_token', data.token);
                showMessage("AUTHORIZATION GRANTED. Keys managed by server. Initializing feed...");
                setTimeout(() => {
                    window.location.href = '/feed/';
                }, 1000);
            } else {
                // Registration verified
                showMessage("EMAIL VERIFIED. Your account is active. Proceed to authenticate session.");
            }
        } else {
            showMessage(data.error || "Verification failed. Invalid or expired OTP.", true);
        }
    } catch (err) {
        showMessage("Connection to verification server failed.", true);
    }
});