/* =====================================================================
 * main.js — App bootstrap: identity, role-based navigation, breadcrumbs.
 * Public API (unchanged): initializeApp()
 * ===================================================================== */

(function (global) {
  'use strict';

  // -------- Role -> menu items (path + label + icon SVG) --------
  const ICONS = {
    cashier:    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2"/><path d="M6 10v4M18 10v4"/></svg>',
    inventory:  '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7l9-4 9 4-9 4-9-4z"/><path d="M3 7v10l9 4 9-4V7"/></svg>',
    reports:    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M7 14l4-4 4 4 5-5"/></svg>',
    users:      '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    settings:   '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 0 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 0 1-4 0v-.1A1.7 1.7 0 0 0 9 19.4a1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 0 1 0-4h.1A1.7 1.7 0 0 0 4.6 9a1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 0 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 0 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>'
  };

  const NAV_BY_ROLE = {
    cashier:   ['cashier'],
    admin:     ['cashier', 'inventory', 'reports', 'users', 'settings'],
    owner:     ['cashier', 'inventory', 'reports', 'users', 'settings'],
    developer: ['cashier', 'inventory', 'reports', 'users', 'settings']
  };

  const NAV_META = {
    cashier:   { path: '/cashier',   label: 'Cashier (POS)' },
    inventory: { path: '/inventory', label: 'Inventory' },
    reports:   { path: '/reports',   label: 'Reports' },
    users:     { path: '/users',     label: 'Users' },
    settings:  { path: '/settings',  label: 'Settings' }
  };

  // -------- Identity --------
  async function loadCurrentUser() {
    // Prefer cached user, fall back to API.
    try {
      const cached = JSON.parse(localStorage.getItem('user') || 'null');
      if (cached && cached.username) return cached;
    } catch (e) {}
    try {
      const u = await apiRequest('/api/auth/me');
      localStorage.setItem('user', JSON.stringify(u));
      return u;
    } catch (e) {
      return null;
    }
  }

  function renderUser(user) {
    const nameEl = document.getElementById('user-name');
    const roleEl = document.getElementById('user-role');
    if (!user) {
      if (nameEl) nameEl.textContent = 'Guest';
      if (roleEl) { roleEl.textContent = ''; roleEl.className = 'role-badge'; }
      return;
    }
    if (nameEl) nameEl.textContent = user.full_name || user.username || 'User';
    if (roleEl) {
      const role = (user.role || '').toLowerCase();
      roleEl.textContent = role;
      roleEl.className = 'role-badge role-' + role;
    }
  }

  function renderNav(user) {
    const nav = document.getElementById('app-nav');
    if (!nav) return;
    const role = ((user && user.role) || 'cashier').toLowerCase();
    const keys = NAV_BY_ROLE[role] || NAV_BY_ROLE.cashier;
    const here = location.pathname.replace(/\/+$/, '') || '/';

    nav.innerHTML = keys.map(function (k) {
      const m = NAV_META[k];
      const active = here === m.path ? 'active' : '';
      const aria = here === m.path ? ' aria-current="page"' : '';
      return (
        '<a href="' + m.path + '" class="' + active + '"' + aria + '>' +
          '<span class="nav-icon">' + (ICONS[k] || '') + '</span>' +
          '<span class="nav-label">' + m.label + '</span>' +
        '</a>'
      );
    }).join('');
  }

  async function initializeApp() {
    // Login page does not have the shell — bail early.
    if (!document.getElementById('app-nav') && !document.getElementById('user-info')) return;

    const user = await loadCurrentUser();
    if (!user && !/\/login$/.test(location.pathname)) {
      window.location.href = '/login';
      return;
    }
    renderUser(user);
    renderNav(user);
  }

  global.initializeApp = initializeApp;
})(window);
