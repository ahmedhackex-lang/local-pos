/**
 * Main application logic
 * Authentication, navigation, global functions
 */

// ===== AUTHENTICATION =====

async function initializeApp() {
    // Check if user is logged in
    const token = localStorage.getItem('access_token');
    
    if (!token && !window.location.pathname.includes('/login')) {
        window.location.href = '/login';
        return;
    }
    
    if (token && window.location.pathname.includes('/login')) {
        // Already logged in, redirect
        const user = getCurrentUser();
        if (user.role === 'cashier') {
            window.location.href = '/cashier';
        } else {
            window.location.href = '/inventory';
        }
        return;
    }
    
    // Validate session
    if (token) {
        try {
            const response = await apiRequest('/api/auth/validate', 'POST');
            if (response.valid) {
                updateUserInfo();
                buildNavigation();
            }
        } catch (error) {
            console.error('Session validation failed:', error);
            logout();
        }
    }
}

function updateUserInfo() {
    const user = getCurrentUser();
    if (!user) return;
    
    const userNameEl = document.getElementById('user-name');
    const userRoleEl = document.getElementById('user-role');
    
    if (userNameEl) {
        userNameEl.textContent = user.full_name || user.username;
    }
    
    if (userRoleEl) {
        userRoleEl.textContent = user.role.toUpperCase();
        userRoleEl.className = `role-badge role-${user.role}`;
    }
}

function buildNavigation() {
    const user = getCurrentUser();
    if (!user) return;
    
    const nav = document.getElementById('app-nav');
    if (!nav) return;
    
    const navItems = [];
    
    // All roles can access their respective dashboards
    if (user.role === 'cashier') {
        navItems.push({ href: '/cashier', text: 'Cashier', icon: '🛒' });
    }
    
    if (hasRole('admin')) {
        navItems.push({ href: '/inventory', text: 'Inventory', icon: '📦' });
        navItems.push({ href: '/reports', text: 'Reports', icon: '📊' });
        navItems.push({ href: '/users', text: 'Users', icon: '👥' });
    }
    
    if (hasRole('developer')) {
        navItems.push({ href: '/settings', text: 'Settings', icon: '⚙️' });
    }
    
    nav.innerHTML = navItems.map(item => `
        <a href="${item.href}" class="nav-item ${window.location.pathname === item.href ? 'active' : ''}">
            <span class="nav-icon">${item.icon}</span>
            <span class="nav-text">${item.text}</span>
        </a>
    `).join('');
}

async function logout() {
    try {
        await apiRequest('/api/auth/logout', 'POST');
    } catch (error) {
        console.error('Logout error:', error);
    }
    
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    window.location.href = '/login';
}

// ===== KEYBOARD SHORTCUTS =====

document.addEventListener('keydown', (e) => {
    // F12 - Complete Sale (on cashier page)
    if (e.key === 'F12' && window.location.pathname === '/cashier') {
        e.preventDefault();
        if (typeof completeSale === 'function') {
            completeSale();
        }
    }
    
    // Ctrl+N - New Product (on inventory page)
    if (e.ctrlKey && e.key === 'n' && window.location.pathname === '/inventory') {
        e.preventDefault();
        if (typeof showAddProductModal === 'function') {
            showAddProductModal();
        }
    }
    
    // Esc - Close modals
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.style.display = 'none';
        });
    }
});