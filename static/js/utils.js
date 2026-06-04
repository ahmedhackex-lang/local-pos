/**
 * Utility functions for Grocery POS System
 * Shared across all pages
 */

// ===== FORMATTING FUNCTIONS =====

function formatCurrency(amount) {
    return `PKR ${parseFloat(amount).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`;
}

function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB'); // DD/MM/YYYY
}

function formatTime(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', { hour12: true });
}

function formatDateTime(dateString) {
    if (!dateString) return '-';
    return `${formatDate(dateString)} ${formatTime(dateString)}`;
}

// ===== API REQUEST WRAPPER =====

async function apiRequest(url, method = 'GET', data = null) {
    const token = localStorage.getItem('access_token');
    
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include' // Include cookies
    };
    
    if (token) {
        options.headers['Authorization'] = `Bearer ${token}`;
    }
    
    if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(url, options);
        
        if (response.status === 401) {
            // Unauthorized - redirect to login
            localStorage.removeItem('access_token');
            localStorage.removeItem('user');
            window.location.href = '/login';
            throw new Error('Session expired');
        }
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Request failed');
        }
        
        // Handle empty responses
        const text = await response.text();
        return text ? JSON.parse(text) : {};
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// ===== TOAST NOTIFICATIONS =====

function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);
    
    // Remove after duration
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ===== LOADING OVERLAY =====

function showLoading(show = true) {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = show ? 'flex' : 'none';
    }
}

// ===== HTML ESCAPING =====

function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// ===== LOCAL STORAGE HELPERS =====

function getCurrentUser() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
}

function hasRole(requiredRole) {
    const user = getCurrentUser();
    if (!user) return false;
    
    const roleHierarchy = {
        'developer': 4,
        'owner': 3,
        'admin': 2,
        'cashier': 1
    };
    
    return roleHierarchy[user.role] >= roleHierarchy[requiredRole];
}

// ===== AUDIO HELPERS =====

function playSound(soundId) {
    const audio = document.getElementById(soundId);
    if (audio) {
        audio.currentTime = 0;
        audio.play().catch(err => console.log('Audio play failed:', err));
    }
}

// ===== VALIDATION =====

function validateBarcode(barcode) {
    return barcode && barcode.length > 0;
}

function validatePrice(price) {
    return !isNaN(price) && parseFloat(price) > 0;
}

function validateQuantity(quantity) {
    return !isNaN(quantity) && parseFloat(quantity) > 0;
}