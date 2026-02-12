/**
 * Safebox Gallery - API Client Utilities
 * Uses HTTP-only cookie authentication
 */

const API_BASE = '/api';

const Auth = {
    isLoggedIn: async () => {
        try {
            const response = await fetch(`${API_BASE}/auth/check`, { credentials: 'include' });
            const data = await response.json();
            return data.authenticated;
        } catch (e) {
            return false;
        }
    },
    logout: async () => {
        await fetch(`${API_BASE}/auth/logout`, { method: 'POST', credentials: 'include' });
        window.location.href = '/admin/login';
    }
};

async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;

    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    const response = await fetch(url, {
        ...options,
        headers,
        credentials: 'include'
    });

    if (response.status === 401) {
        if (window.location.pathname.includes('/admin/') && !window.location.pathname.includes('login')) {
            window.location.href = '/admin/login';
        }
        throw new Error('Unauthorized');
    }

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'An error occurred' }));
        throw new Error(error.detail || 'Request failed');
    }

    if (response.status === 204) {
        return null;
    }

    return response.json();
}

const AuthAPI = {
    login: (email, password) => apiRequest('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
    }),
    logout: Auth.logout,
    getMe: () => apiRequest('/auth/me')
};



const UploadAPI = {
    upload: async (file) => {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_BASE}/admin/upload`, {
            method: 'POST',
            credentials: 'include',  // Use cookies
            body: formData
        });

        if (!response.ok) {
            throw new Error('Upload failed');
        }

        return response.json();
    }
};








window.Auth = Auth;
window.TokenManager = { isLoggedIn: Auth.isLoggedIn };  // Backward compatibility
window.AuthAPI = AuthAPI;
window.UploadAPI = UploadAPI;
