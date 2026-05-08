const token = localStorage.getItem('jwt_token');
let currentTarget = null;
let activeUsername = null;
let isFetchingMessages = false;
let refreshTimer = null;
let latestMessageId = 0;
let targetUnlocked = false;

// Redirect if not authenticated
if (!token) {
    window.location.href = '/'; 
}

// Get current username for sender checks
async function loadMyProfile() {
    try {
        const res = await fetch(`/api/accounts/profile/?t=${Date.now()}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            const data = await res.json();
            activeUsername = data.username;
        }
    } catch (e) {
        console.error('Failed to load profile for DM page', e);
    }
}

async function loadUsers() {
    const res = await fetch('/api/network/operatives/', {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
        const users = await res.json();
        const list = document.getElementById('userList');
        list.innerHTML = '';
        if (users.length === 0) {
            list.innerHTML = '<div class="status-message">No operatives online</div>';
        } else {
            users.forEach(u => {
                const div = document.createElement('div');
                div.className = 'user-item';
                div.innerText = u.username.toUpperCase();
                div.onclick = () => openChat(u.username);
                list.appendChild(div);
            });
        }
    } else {
        const list = document.getElementById('userList');
        list.innerHTML = `<div class="status-message" style="color: #ff6b6b;">Error loading users</div>`;
        console.error('Failed to load operatives:', res.status);
    }
}

async function openChat(username) {
    currentTarget = username;
    latestMessageId = 0;
    document.getElementById('chatTitle').innerText = `◆ ENCRYPTED_LINK: ${username.toUpperCase()}`;
    document.getElementById('msgInput').disabled = false;
    document.getElementById('sendBtn').disabled = false;
    document.getElementById('chatHistory').innerHTML = '';
    
    // Clear any existing auto-refresh timer
    if (refreshTimer) clearTimeout(refreshTimer);
    
    // Conversations are auto-unlocked using server-stored shared secret when available
    targetUnlocked = true;
    // ensure we know who we are for sender checks
    if (!activeUsername) await loadMyProfile();

    // If a saved secret exists, auto-verify it (silent) and unlock if valid
    const saved = sessionStorage.getItem(`dm_shared_secret_${username}`) || '';
    if (saved) {
        const ok = await verifySecretForTarget(saved, username);
        if (ok) {
            targetUnlocked = true;
            latestMessageId = 0;
            await fetchMessages(true);
            scheduleRefresh();
        } else {
            targetUnlocked = false;
            const chatSecretError = document.getElementById('chatSecretError');
            if (chatSecretError) {
                chatSecretError.textContent = 'Saved key invalid. Press SET to re-verify.';
                chatSecretError.style.display = 'block';
            }
        }
    }
    
    // Auto-refresh silently without flooding the server
    scheduleRefresh();
}

// No modal: use inline SET button and `chatSecretError` for feedback.

// verification is handled server-side using stored conversation secret; no client-side verify

// show chat secret input and load/set per-target secret when opening
// Conversations are auto-verified server-side; no per-conversation input required in UI.

function scheduleRefresh() {
    if (refreshTimer) clearTimeout(refreshTimer);
    if (!currentTarget) return;

    refreshTimer = setTimeout(async () => {
        if (!document.hidden) {
            await fetchMessages(false);
        }
        scheduleRefresh();
    }, 4000);
}

async function fetchMessages(showLoading = false) {
    if (!currentTarget) return;
    if (isFetchingMessages) return;
    if (!targetUnlocked) return;
    
    const historyDiv = document.getElementById('chatHistory');

    // Only show loading on initial fetch
    if (showLoading && historyDiv.innerHTML === '') {
        historyDiv.innerHTML = `<div class="status-message">🔓 Decrypting packets...</div>`;
    }

    try {
        isFetchingMessages = true;
        const query = latestMessageId > 0 ? `?after_id=${latestMessageId}` : '';
        const res = await fetch(`/api/network/dm/${currentTarget}/${query}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (res.ok) {
            const messages = await res.json();
            // Note: we no longer auto-relock just because existing messages are compromised.
            // Users may agree to a new shared secret and want to stay unlocked for future messages.
            if (messages.length === 0) {
                if (historyDiv.children.length === 0) {
                    historyDiv.innerHTML = `<div class="status-message">No messages yet. Start a conversation!</div>`;
                }
                return;
            }

            if (historyDiv.innerHTML.includes('status-message')) {
                historyDiv.innerHTML = '';
            }

            messages.forEach((msg) => appendMessage(msg));
            historyDiv.scrollTop = historyDiv.scrollHeight;

            const newestMessage = messages[messages.length - 1];
            latestMessageId = Math.max(latestMessageId, newestMessage.id);
            if (historyDiv.children.length === 0) {
                historyDiv.innerHTML = `<div class="status-message">No messages yet. Start a conversation!</div>`;
            }
        } else {
            if (showLoading) {
                historyDiv.innerHTML = `<div class="status-message">❌ Failed to fetch messages. Check your shared secret.</div>`;
            }
        }
    } catch (error) {
        if (showLoading) {
            historyDiv.innerHTML = `<div class="status-message">❌ Connection error</div>`;
        }
    } finally {
        isFetchingMessages = false;
    }
}

function appendMessage(msg) {
    const historyDiv = document.getElementById('chatHistory');
    const isMe = msg.sender === activeUsername;
    const timestamp = msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : '';
    let warningHtml = '';
    if (msg.is_compromised) {
        warningHtml = `<div class="msg-warning">🚨 ALERT: Integrity check failed. Unable to verify or decrypt this message.</div>`;
    }

    const existing = historyDiv.querySelector(`[data-message-id="${msg.id}"]`);
    if (existing) return;

    const wrapper = document.createElement('div');
    wrapper.className = `msg-bubble ${isMe ? 'sent' : 'received'} ${msg.is_compromised ? 'compromised-msg' : ''}`;
    wrapper.dataset.messageId = msg.id;
    // If integrity failed, redact content to avoid leaking plaintext but allow reveal
    const contentHtml = msg.is_compromised ? '<em style="color:#ff6b6b;">🔒 Unable to decrypt message. Verify shared secret.</em>' : msg.content;
    wrapper.innerHTML = `
        <div class="msg-sender">${msg.sender}${isMe ? ' (you)' : ''}</div>
        <div class="msg-content" data-revealed="0">${contentHtml}</div>
        ${msg.is_compromised ? '<div style="margin-top:6px;"><button class="btn btn-sm btn-outline-light reveal-btn">REVEAL</button></div>' : ''}
        ${warningHtml}
        <div class="msg-timestamp">${timestamp}</div>
    `;
    // Attach reveal handler if compromised
    if (msg.is_compromised) {
        wrapper.dataset.rawContent = msg.content || '';
        const btn = wrapper.querySelector('.reveal-btn');
        const contentDiv = wrapper.querySelector('.msg-content');
        btn.addEventListener('click', (e) => {
            if (contentDiv.dataset.revealed === '1') {
                contentDiv.innerHTML = '<em style="color:#ff6b6b;">🔒 Unable to decrypt message. Verify shared secret.</em>';
                contentDiv.dataset.revealed = '0';
                btn.innerText = 'REVEAL';
            } else {
                // show raw content (text-only to avoid HTML injection)
                contentDiv.textContent = wrapper.dataset.rawContent;
                contentDiv.dataset.revealed = '1';
                btn.innerText = 'HIDE';
            }
        });
    }
    historyDiv.appendChild(wrapper);
}

function appendPendingMessage(content) {
    const historyDiv = document.getElementById('chatHistory');
    const wrapper = document.createElement('div');
    wrapper.className = 'msg-bubble sent';
    wrapper.dataset.pending = 'true';
    wrapper.innerHTML = `
        <div class="msg-sender">YOU</div>
        <div class="msg-content">${content}</div>
        <div class="msg-timestamp">sending...</div>
    `;
    historyDiv.appendChild(wrapper);
    historyDiv.scrollTop = historyDiv.scrollHeight;
    return wrapper;
}

function finalizePendingMessage(pendingNode, msg) {
    if (!pendingNode) return;
    pendingNode.dataset.pending = 'false';
    pendingNode.dataset.messageId = msg.id;
    pendingNode.className = `msg-bubble sent ${msg.is_compromised ? 'compromised-msg' : ''}`;
    pendingNode.innerHTML = `
        <div class="msg-sender">YOU</div>
        <div class="msg-content">${msg.content}</div>
        ${msg.is_compromised ? '<div class="msg-warning">🚨 ALERT: Integrity check failed. Either shared secret is incorrect or message was tampered with.</div>' : ''}
        <div class="msg-timestamp">${msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : ''}</div>
    `;
}

document.getElementById('sendBtn').onclick = async () => {
    const content = document.getElementById('msgInput').value;
    if (!content) {
        alert("Message required.");
        return;
    }

    const pendingBubble = appendPendingMessage(content);

    const res = await fetch('/api/network/dm/send/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            receiver: currentTarget,
            content: content
        })
    });

    if (res.ok) {
        const created = await res.json();
        document.getElementById('msgInput').value = '';
        if (created && created.id) {
            latestMessageId = Math.max(latestMessageId, created.id);
            finalizePendingMessage(pendingBubble, created);
        }
    } else {
        if (pendingBubble && pendingBubble.parentNode) {
            pendingBubble.parentNode.removeChild(pendingBubble);
        }
        alert('Failed to send message');
    }
};

// Load profile and users when page loads
loadMyProfile();
loadUsers();

window.addEventListener('beforeunload', () => {
    if (refreshTimer) clearTimeout(refreshTimer);
});