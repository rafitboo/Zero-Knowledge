const token = localStorage.getItem('jwt_token');
const targetUserId = document.body?.dataset?.userId;

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

    requestAnimationFrame(() => {
        notif.style.transform = 'translateX(0)';
        notif.style.opacity = '1';
    });

    setTimeout(() => {
        notif.style.opacity = '0';
        notif.style.transform = 'translateX(50px)';
        setTimeout(() => notif.remove(), 400);
    }, 3500);
}

function formatTimestamp(value) {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? '-' : date.toLocaleString();
}

function getSelectedPostIds() {
    return Array.from(document.querySelectorAll('.post-select:checked')).map((checkbox) => checkbox.value);
}

function syncControls() {
    const selectedCount = getSelectedPostIds().length;
    const deleteButton = document.getElementById('deleteSelectedBtn');
    const selectAll = document.getElementById('selectAllPosts');
    const checkboxes = Array.from(document.querySelectorAll('.post-select'));

    if (deleteButton) {
        deleteButton.disabled = selectedCount === 0;
        deleteButton.textContent = selectedCount === 0 ? 'DELETE_SELECTED' : `DELETE_SELECTED (${selectedCount})`;
    }

    if (selectAll && checkboxes.length) {
        selectAll.checked = selectedCount > 0 && selectedCount === checkboxes.length;
        selectAll.indeterminate = selectedCount > 0 && selectedCount < checkboxes.length;
    }
}

function renderPosts(posts) {
    const tbody = document.getElementById('postsTableBody');

    if (!tbody) {
        return;
    }

    if (!posts.length) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No posts found for this user.</td></tr>';
        syncControls();
        return;
    }

    tbody.innerHTML = posts.map((post, index) => `
        <tr>
            <td>${index + 1}</td>
            <td style="white-space: pre-wrap; word-break: break-word;">${post.content}</td>
            <td>${formatTimestamp(post.created_at)}</td>
            <td>
                <input class="form-check-input post-select" type="checkbox" value="${post.id}">
            </td>
        </tr>
    `).join('');

    document.querySelectorAll('.post-select').forEach((checkbox) => {
        checkbox.addEventListener('change', syncControls);
    });

    syncControls();
}

async function loadUserPosts() {
    if (!token) {
        window.location.href = '/';
        return;
    }

    const response = await fetch(`/api/network/admin/users/${targetUserId}/posts/?t=${Date.now()}`, {
        headers: {
            'Authorization': `Bearer ${token}`,
            'Cache-Control': 'no-cache'
        },
        cache: 'no-store'
    });

    if (response.status === 403) {
        showNotification('ACCESS DENIED: INSUFFICIENT PRIVILEGES.', true);
        setTimeout(() => window.location.href = '/feed/', 1500);
        return;
    }

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        showNotification(data.error || 'Failed to load user posts.', true);
        return;
    }

    const username = data.user?.username || document.body.dataset.username || 'UNKNOWN';
    const usernameHeader = document.getElementById('usernameHeader');
    const targetUsername = document.getElementById('targetUsername');

    if (usernameHeader) {
        usernameHeader.textContent = username;
    }

    if (targetUsername) {
        targetUsername.textContent = `@${username}`;
    }

    renderPosts(Array.isArray(data.posts) ? data.posts : []);
}

async function deleteSelectedPosts() {
    const postIds = getSelectedPostIds();

    if (!postIds.length) {
        showNotification('Select at least one post.', true);
        return;
    }

    const response = await fetch(`/api/network/admin/users/${targetUserId}/posts/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ post_ids: postIds })
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        showNotification(data.error || 'Failed to delete posts.', true);
        return;
    }

    showNotification(data.message || 'Posts deleted.');
    await loadUserPosts();
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('selectAllPosts')?.addEventListener('change', (event) => {
        const shouldCheck = event.target.checked;
        document.querySelectorAll('.post-select').forEach((checkbox) => {
            checkbox.checked = shouldCheck;
        });
        syncControls();
    });

    document.getElementById('deleteSelectedBtn')?.addEventListener('click', deleteSelectedPosts);
    loadUserPosts();
});