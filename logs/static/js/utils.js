/* =====================================================================
 * utils.js — Shared utilities for the Grocery POS frontend.
 * Public API (unchanged contracts used by other pages):
 *   apiRequest(url, method?, body?, options?)
 *   showToast(message, type?)        // type: 'success'|'error'|'warning'|'info'
 *   showLoading(on)
 *   formatDateTime(value)
 *   formatDate(value)
 *   formatCurrency(value)
 *   escapeHtml(value)
 *   debounce(fn, ms)
 *   confirmDialog(message)           // returns Promise<boolean>
 *   logout()                         // clears auth and redirects to /login
 * ===================================================================== */

(function (global) {
  'use strict';

  // ---------- Auth helpers ----------
  function getToken() {
    try { return localStorage.getItem('access_token') || ''; } catch (e) { return ''; }
  }

  function clearAuth() {
    try {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
    } catch (e) {}
  }

  function logout() {
    clearAuth();
    window.location.href = '/login';
  }

  // ---------- API ----------
  async function apiRequest(url, method, body, options) {
    method = (method || 'GET').toUpperCase();
    options = options || {};

    const headers = Object.assign({}, options.headers || {});
    const token = getToken();
    if (token && !headers['Authorization']) headers['Authorization'] = 'Bearer ' + token;

    let payload = body;
    const isForm = body instanceof FormData || body instanceof URLSearchParams;
    if (body !== undefined && body !== null && !isForm && typeof body === 'object') {
      headers['Content-Type'] = headers['Content-Type'] || 'application/json';
      payload = JSON.stringify(body);
    }

    let response;
    try {
      response = await fetch(url, { method, headers, body: method === 'GET' ? undefined : payload });
    } catch (networkErr) {
      showToast('Network error. Please check your connection.', 'error');
      throw networkErr;
    }

    if (response.status === 401) {
      clearAuth();
      if (!/\/login$/.test(location.pathname)) {
        showToast('Session expired. Please sign in again.', 'warning');
        setTimeout(function () { window.location.href = '/login'; }, 600);
      }
      throw new Error('Unauthorized');
    }

    const contentType = response.headers.get('content-type') || '';
    const isJson = contentType.indexOf('application/json') !== -1;
    const data = isJson ? await response.json().catch(function () { return null; }) : await response.text();

    if (!response.ok) {
      const message = (data && (data.detail || data.message)) || ('Request failed (' + response.status + ')');
      const err = new Error(message);
      err.status = response.status; err.data = data;
      throw err;
    }
    return data;
  }

  // ---------- Toasts ----------
  function showToast(message, type) {
    type = type || 'info';
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = 'toast ' + type;
    toast.setAttribute('role', type === 'error' ? 'alert' : 'status');

    const icon = ({
      success: '✓', error: '✕', warning: '!', info: 'i'
    })[type] || 'i';

    toast.innerHTML =
      '<span aria-hidden="true" style="display:inline-grid;place-items:center;width:22px;height:22px;border-radius:999px;background:currentColor;color:#fff;font-weight:700;font-size:12px;flex-shrink:0">' + escapeHtml(icon) + '</span>' +
      '<div style="flex:1;color:var(--text-primary)">' + escapeHtml(String(message)) + '</div>';

    container.appendChild(toast);

    const remove = function () {
      toast.style.transition = 'opacity .2s, transform .2s';
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(20px)';
      setTimeout(function () { toast.remove(); }, 220);
    };
    toast.addEventListener('click', remove);
    setTimeout(remove, type === 'error' ? 6000 : 3500);
  }

  // ---------- Loading overlay ----------
  let loadingDepth = 0;
  function showLoading(on) {
    const overlay = document.getElementById('loading-overlay');
    if (!overlay) return;
    if (on) {
      loadingDepth++;
      overlay.style.display = 'grid';
      overlay.setAttribute('aria-hidden', 'false');
    } else {
      loadingDepth = Math.max(0, loadingDepth - 1);
      if (loadingDepth === 0) {
        overlay.style.display = 'none';
        overlay.setAttribute('aria-hidden', 'true');
      }
    }
  }

  // ---------- Formatters ----------
  function formatDateTime(value) {
    if (!value) return '';
    const d = new Date(value);
    if (isNaN(d.getTime())) return String(value);
    return d.toLocaleString();
  }
  function formatDate(value) {
    if (!value) return '';
    const d = new Date(value);
    if (isNaN(d.getTime())) return String(value);
    return d.toLocaleDateString();
  }
  function formatCurrency(value, currency) {
    const n = Number(value || 0);
    return (currency || 'PKR') + ' ' + n.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  }

  // ---------- HTML / DOM ----------
  function escapeHtml(value) {
    if (value === null || value === undefined) return '';
    return String(value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function debounce(fn, ms) {
    let t;
    return function () {
      const self = this, args = arguments;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(self, args); }, ms || 250);
    };
  }

  function confirmDialog(message) {
    // Lightweight wrapper for now; can be upgraded to a custom modal later.
    return Promise.resolve(window.confirm(message));
  }

  // ---------- Export ----------
  global.apiRequest    = apiRequest;
  global.showToast     = showToast;
  global.showLoading   = showLoading;
  global.formatDateTime= formatDateTime;
  global.formatDate    = formatDate;
  global.formatCurrency= formatCurrency;
  global.escapeHtml    = escapeHtml;
  global.debounce      = debounce;
  global.confirmDialog = confirmDialog;
  global.logout        = logout;
  global._getToken     = getToken;
})(window);
