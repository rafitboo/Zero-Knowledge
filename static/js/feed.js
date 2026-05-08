// 1. Security Check & Setup
const token = localStorage.getItem('jwt_token');
if (!token) {
    window.location.href = '/'; 
}

// --- NEW: Custom Cyber Notification System ---
function showNotification(message, isError = false) {
    const notif = document.createElement('div');
    const color = isError ? '#ff0055' : '#00ffcc';
    
    // Style the notification to match your theme
    notif.style.position = 'fixed';
    notif.style.top = '20px';
    notif.style.right = '20px';
    notif.style.zIndex = '9999';
    notif.style.backgroundColor = '#121212';
    notif.style.border = `1px solid ${color}`;
    notif.style.borderLeft = `4px solid ${color}`;
    notif.style.color = color;
    notif.style.padding = '15px 20px';
    notif.style.fontFamily = 'monospace';
    notif.style.boxShadow = `0 0 10px ${color}40`;
    notif.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    notif.style.transform = 'translateX(50px)';
    notif.style.opacity = '0';
    
    notif.innerHTML = `> ${message}`;
    document.body.appendChild(notif);

    // Trigger animation in
    requestAnimationFrame(() => {
        notif.style.transform = 'translateX(0)';
        notif.style.opacity = '1';
    });

    // Auto-remove after 3.5 seconds
    setTimeout(() => {
        notif.style.opacity = '0';
        notif.style.transform = 'translateX(50px)';
        setTimeout(() => notif.remove(), 400); // Wait for fade out
    }, 3500);
}


// 2. Fetch and render the Double-Encrypted Feed
async function loadPosts() {
    const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    };

    const feedContainer = document.getElementById('feedContainer');
    
    try {
        const response = await fetch('/api/network/posts/', { headers });
        const posts = await response.json();
        
        feedContainer.innerHTML = ''; 
        
        if (!Array.isArray(posts)) {
            feedContainer.innerHTML = `<p class="text-danger">Failed to load ledger: ${posts.error || 'Unknown error'}</p>`;
            return;
        }

        if (posts.length === 0) {
            feedContainer.innerHTML = `
                <div class="post-card mb-3 bg-dark p-3" style="border-left: 3px solid #00d2ff;">
                    <div class="ciphertext-block text-info font-monospace">
                        No readable posts yet. You can decrypt posts created after your account was added to the key ring.
                    </div>
                </div>
            `;
            return;
        }

        posts.forEach(post => {
            const isLocked = post.content.includes('[ENCRYPTED_DATA_LOCKED]');
            const textColor = isLocked ? 'text-danger' : 'text-success';
            
            const postHTML = `
                <div class="post-card mb-3 bg-dark p-3" id="post-${post.id}" style="border-left: 3px solid ${isLocked ? '#ff0000' : '#00ffcc'};">
                    <div class="d-flex justify-content-between mb-2">
                        <span class="author-tag font-monospace text-info">@${post.author}</span>
                        <small class="text-muted">${new Date(post.created_at).toLocaleString()}</small>
                    </div>
                    
                    <div class="ciphertext-block ${textColor} font-monospace" id="content-${post.id}">
                        ${post.content}
                    </div>
                </div>
            `;
            feedContainer.innerHTML += postHTML;
        });
    } catch (err) {
        feedContainer.innerHTML = '<p class="text-danger">Failed to load secure feed.</p>';
    }
}

// 3. Handle New Post Creation
document.getElementById('createPostForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const content = document.getElementById('postContent').value;
    const submitBtn = e.target.querySelector('button[type="submit"]');
    
    // UI feedback while encrypting
    const originalBtnText = submitBtn.innerText;
    submitBtn.innerText = "Encrypting...";
    submitBtn.disabled = true;
    
    try {
        const response = await fetch('/api/network/posts/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ content: content })
        });
        const data = await response.json();
        
        if (response.ok) {
            // ---> THE FIX: Using the new slick notification! <---
            showNotification(data.message); 
            document.getElementById('postContent').value = ''; 
            
            const keyArea = document.getElementById('keyDisplayArea');
            if (keyArea) keyArea.classList.add('d-none');
            
            loadPosts(); 
        } else {
            // Using it for errors too!
            showNotification("Error: " + (data.error || "Broadcast failed."), true);
        }
    } catch (err) {
        showNotification("Network error. Could not reach server.", true);
    } finally {
        // Reset button
        submitBtn.innerText = originalBtnText;
        submitBtn.disabled = false;
    }
});

// 4. RBAC Verification Logic
function verifyClearance() {
    if (!token) return;

    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const adminBtn = document.getElementById('adminCommandCenter');
        
        if (payload.role === 'ADMIN' && adminBtn) {
            adminBtn.style.display = 'inline-block';
            console.log(">>> ADMIN_CLEARANCE_VERIFIED: COMMAND_CENTER_ENABLED");
        }
    } catch (e) {
        console.error(">>> ERROR: FAILED_TO_DECODE_AUTH_TOKEN");
    }
}

// Initialize page
document.addEventListener('DOMContentLoaded', () => {
    verifyClearance();
    loadPosts();
});

// --- PROFILE MANAGEMENT LOGIC ---
let profileModalInstance = null;

async function openProfileModal() {
    if (!profileModalInstance) {
        profileModalInstance = new bootstrap.Modal(document.getElementById('profileModal'));
    }
    
    try {
        const response = await fetch(`/api/accounts/profile/?t=${Date.now()}`, {
            headers: { 
                'Authorization': `Bearer ${token}`
            }
        });
        const data = await response.json();
        
        if (response.ok) {
            document.getElementById('profUsername').value = data.username;
            document.getElementById('profEmail').value = data.email;
            document.getElementById('profContact').value = data.contact_info; // This will now be decrypted!
            profileModalInstance.show();
        }
    } catch (err) {
        showNotification("Failed to load profile.", true);
    }
}

document.getElementById('profileForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerText;
    
    submitBtn.innerText = "UPDATING...";
    submitBtn.disabled = true;

    // Gather updated payload
    const email = document.getElementById('profEmail').value;
    const contact_info = document.getElementById('profContact').value;
    const pwd = document.getElementById('profPassword').value;
    
    const payload = {
        email: email,
        contact_info: contact_info,
    };
    
    // Only send password if they actually typed a new one
    if (pwd) payload.password = pwd;
    
    console.log('Profile Update Payload:', payload);
    console.log('Token:', token);

    try {
        const response = await fetch('/api/accounts/profile/', {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });
        
        console.log('Response status:', response.status);
        console.log('Response ok:', response.ok);
        
        const data = await response.json();
        console.log('Response data:', data);

        if (response.ok) {
            // Check if email verification is pending
            if (data.updated_fields && data.updated_fields.includes('email_verification_pending')) {
                showNotification(data.message);
                // Show OTP verification form
                document.getElementById('profileForm').style.display = 'none';
                document.getElementById('emailOTPForm').style.display = 'block';
                // Store pending email for reference
                window.pendingEmail = data.pending_email;
            } else {
                showNotification(data.message);
                // Reload profile to show updated data
                profileModalInstance.hide();
                setTimeout(() => openProfileModal(), 500);
            }
        } else {
            showNotification(data.error || "Error updating profile.", true);
        }
    } catch (err) {
        console.error('Fetch error:', err);
        showNotification("Network error while updating profile.", true);
    } finally {
        submitBtn.innerText = originalText;
        submitBtn.disabled = false;
    }
});

// Handle Email OTP Verification
document.getElementById('emailOTPForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerText;
    
    const otp = document.getElementById('emailOTP').value;
    
    if (!otp || otp.length !== 6) {
        showNotification("Please enter a valid 6-digit OTP.", true);
        return;
    }
    
    submitBtn.innerText = "VERIFYING...";
    submitBtn.disabled = true;
    
    try {
        const response = await fetch('/api/accounts/verify-email-change/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ otp: otp })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification(data.message);
            // Reset form
            document.getElementById('profileForm').style.display = 'block';
            document.getElementById('emailOTPForm').style.display = 'none';
            document.getElementById('emailOTP').value = '';
            profileModalInstance.hide();
            setTimeout(() => openProfileModal(), 500);
        } else {
            showNotification(data.error || "OTP verification failed.", true);
        }
    } catch (err) {
        console.error('OTP verification error:', err);
        showNotification("Network error during OTP verification.", true);
    } finally {
        submitBtn.innerText = originalText;
        submitBtn.disabled = false;
    }
});

// Cancel email change
function cancelEmailChange() {
    document.getElementById('profileForm').style.display = 'block';
    document.getElementById('emailOTPForm').style.display = 'none';
    document.getElementById('emailOTP').value = '';
}