const token = localStorage.getItem('jwt_token');

// --- Notification System ---
function showNotification(message, isError = false) {
    const notif = document.createElement('div');
    const color = isError ? '#ff0055' : '#00ffcc';
    
    notif.style.position = 'fixed';
    notif.style.top = '20px';
    notif.style.right = '20px';
    notif.style.zIndex = '9999';
    notif.style.backgroundColor = '#0a0a0a';
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
        setTimeout(() => notif.remove(), 400);
    }, 3500);
}

function parseActiveState(value) {
    if (typeof value === 'boolean') return value;
    if (typeof value === 'number') return value === 1;
    if (typeof value === 'string') {
        const normalized = value.trim().toLowerCase();
        return normalized === 'true' || normalized === '1';
    }
    return false;
}

async function loadRoster() {
    if (!token) {
        window.location.href = '/';
        return;
    }

    const response = await fetch(`/api/network/admin/users/?t=${Date.now()}`, {
        headers: {
            'Authorization': `Bearer ${token}`,
            'Cache-Control': 'no-cache'
        },
        cache: 'no-store'
    });
    
    if (response.status === 403) {
        showNotification("ACCESS DENIED: INSUFFICIENT PRIVILEGES.", true);
        setTimeout(() => window.location.href = '/feed/', 1500);
        return;
    }

    const users = await response.json();
    const tbody = document.getElementById('userTableBody');
    tbody.innerHTML = '';

    users.forEach(user => {
        const isActive = parseActiveState(user.is_active);
        const statusText = isActive ? 'ACTIVE' : 'INACTIVE';
        const btnClass = isActive ? 'btn-outline-danger' : 'btn-success';
        const btnLabel = isActive ? 'BAN' : 'UNBAN';
        const statusClass = isActive ? 'text-bg-success' : 'text-bg-danger';

        tbody.innerHTML += `
            <tr id="user-row-${user.id}">
                <td>${user.id}</td>
                <td>${user.username}</td>
                <td>${user.email || '-'}</td>
                <td>${user.role}</td>
                <td>
                    <span id="status-${user.id}" class="badge ${statusClass}">${statusText}</span>
                </td>
                <td>
                    <select onchange="updateRole(${user.id}, this.value)" class="bg-dark text-white border-secondary">
                        <option value="USER" ${user.role === 'USER' ? 'selected' : ''}>USER</option>
                        <option value="ADMIN" ${user.role === 'ADMIN' ? 'selected' : ''}>ADMIN</option>
                    </select>
                    <button id="ban-btn-${user.id}" class="btn ${btnClass} btn-sm ms-2" onclick="toggleBan(${user.id})">
                        ${btnLabel}
                    </button>
                </td>
            </tr>
        `;
    });
}

async function updateRole(userId, role) {
    const response = await fetch(`/api/network/admin/users/${userId}/promote/`, {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ role: role })
    });

    if (response.ok) {
        showNotification(`CLEARANCE LEVEL UPDATED TO: ${role}`);
        return;
    }

    const data = await response.json().catch(() => ({}));
    showNotification(data.error || 'Failed to update role.', true);
}

async function toggleBan(userId) {
    const statusBadge = document.getElementById(`status-${userId}`);
    const banButton = document.getElementById(`ban-btn-${userId}`);

    // Infer current state from UI so we can still toggle deterministically
    // even if the backend response body is empty/non-JSON.
    const uiShowsActive = statusBadge ? statusBadge.textContent.trim() === 'ACTIVE' : true;

    const response = await fetch(`/api/network/admin/users/${userId}/action/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ action: 'toggle_ban' })
    });

    if (response.ok) {
        const data = await response.json().catch(() => ({}));

        let isActive;
        if (Object.prototype.hasOwnProperty.call(data, 'is_active')) {
            isActive = parseActiveState(data.is_active);
        } else {
            // Fallback: if server did not return state, invert current UI state.
            isActive = !uiShowsActive;
        }

        if (statusBadge) {
            statusBadge.textContent = isActive ? 'ACTIVE' : 'INACTIVE';
            statusBadge.classList.remove('text-bg-success', 'text-bg-danger');
            statusBadge.classList.add(isActive ? 'text-bg-success' : 'text-bg-danger');
        }

        if (banButton) {
            banButton.textContent = isActive ? 'BAN' : 'UNBAN';
            banButton.classList.remove('btn-outline-danger', 'btn-success');
            banButton.classList.add(isActive ? 'btn-outline-danger' : 'btn-success');
        }

        if (data.message) {
            showNotification(data.message);
        } else {
            showNotification(isActive ? 'User UNBANNED.' : 'User BANNED.');
        }
        return;
    }

    const data = await response.json().catch(() => ({}));
    showNotification(data.error || 'Failed to update user status.', true);
}
