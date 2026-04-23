/**
 * app.js — Shelf Bookstore Global JavaScript
 * Shared across all 5 pages:
 *   index.html, book.html, auth.html, cart.html, admin.html
 *
 * Covers:
 *  - API client (apiFetch) with JWT injection
 *  - Auth helpers (token storage, user state)
 *  - Cart state management + badge updates
 *  - Search debounce utility
 *  - Toast notification
 *  - INR currency formatter
 *  - Star rating renderer
 *  - Skeleton loader helpers
 *  - DOM helpers
 *  - Page-level init (auto-detects current page)
 */

'use strict';

/* ═══════════════════════════════════════════════════════════
   CONSTANTS
═══════════════════════════════════════════════════════════ */
const SHELF = {
  API_BASE: '',          // same origin — Flask serves both
  TOKEN_KEY: 'shelf_token',
  USER_KEY:  'shelf_user',

  FALLBACK_COVERS: [
    'https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=300&q=80',
    'https://images.unsplash.com/photo-1512820790803-83ca734da794?w=300&q=80',
    'https://images.unsplash.com/photo-1495640388908-05fa85288e61?w=300&q=80',
    'https://images.unsplash.com/photo-1516979187457-637abb4f9353?w=300&q=80',
    'https://images.unsplash.com/photo-1519682337058-a94d519337bc?w=300&q=80',
    'https://images.unsplash.com/photo-1432821596592-e2c18b78144f?w=300&q=80',
  ],

  MOODS: [
    'Light & Funny', 'Dark & Thrilling', 'Thought-Provoking',
    'Romantic', 'Mind-Bending', 'Emotional', 'Melancholic', 'Inspirational'
  ],

  ORDER_STATUSES: ['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled'],

  LOW_STOCK_THRESHOLD: 10,
};

/* ═══════════════════════════════════════════════════════════
   TOKEN / AUTH STORAGE
═══════════════════════════════════════════════════════════ */
const Auth = {
  getToken()        { return localStorage.getItem(SHELF.TOKEN_KEY); },
  setToken(t)       { localStorage.setItem(SHELF.TOKEN_KEY, t); },
  removeToken()     { localStorage.removeItem(SHELF.TOKEN_KEY); },
  hasToken()        { return !!localStorage.getItem(SHELF.TOKEN_KEY); },

  getUser()         {
    try { return JSON.parse(localStorage.getItem(SHELF.USER_KEY)); }
    catch { return null; }
  },
  setUser(u)        { localStorage.setItem(SHELF.USER_KEY, JSON.stringify(u)); },
  removeUser()      { localStorage.removeItem(SHELF.USER_KEY); },

  logout() {
    this.removeToken();
    this.removeUser();
    window.location.href = '/auth';
  },

  redirectIfLoggedIn(redirectTo = '/') {
    if (this.hasToken()) window.location.href = redirectTo;
  },

  redirectIfNotLoggedIn(redirectTo = null) {
    if (!this.hasToken()) {
      const url = redirectTo || `/auth?redirect=${encodeURIComponent(window.location.pathname)}`;
      window.location.href = url;
    }
  },
};

/* ═══════════════════════════════════════════════════════════
   API CLIENT
═══════════════════════════════════════════════════════════ */
const API = {
  async fetch(path, opts = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...(opts.headers || {}),
    };
    if (Auth.hasToken()) {
      headers['Authorization'] = `Bearer ${Auth.getToken()}`;
    }
    try {
      const res  = await fetch(SHELF.API_BASE + path, { ...opts, headers });
      const data = await res.json();
      return data;
    } catch (err) {
      console.error('API error:', path, err);
      return { status: 'error', message: 'Network error. Please try again.' };
    }
  },

  get(path)             { return this.fetch(path); },
  post(path, body)      { return this.fetch(path, { method: 'POST',   body: JSON.stringify(body) }); },
  put(path, body)       { return this.fetch(path, { method: 'PUT',    body: JSON.stringify(body) }); },
  delete(path)          { return this.fetch(path, { method: 'DELETE' }); },

  // ── Auth ──────────────────────────────────────────────
  login(email, password)           { return this.post('/api/auth/login', { email, password }); },
  register(name, email, password, preferences) {
    return this.post('/api/auth/register', { name, email, password, preferences });
  },
  getMe()                          { return this.get('/api/auth/me'); },
  updatePreferences(prefs)         { return this.put('/api/auth/preferences', { preferences: prefs }); },

  // ── Books ─────────────────────────────────────────────
  getBooks(limit = 50, offset = 0) { return this.get(`/api/books?limit=${limit}&offset=${offset}`); },
  getBook(id)                      { return this.get(`/api/books/${id}`); },
  getCategories()                  { return this.get('/api/books/categories'); },
  getAuthor(id)                    { return this.get(`/api/books/author/${id}`); },

  // ── Search ────────────────────────────────────────────
  search(query, mode = 'semantic', mood = '', limit = 20) {
    let url = `/api/search?limit=${limit}`;
    if (query) url += `&q=${encodeURIComponent(query)}&mode=${mode}`;
    if (mood)  url += `&mood=${encodeURIComponent(mood)}`;
    return this.get(url);
  },
  similar(bookId, limit = 8) { return this.get(`/api/search/similar/${bookId}?limit=${limit}`); },

  // ── Cart ──────────────────────────────────────────────
  getCart()                        { return this.get('/api/cart'); },
  addToCart(bookId, qty = 1)       { return this.post('/api/cart/add', { book_id: bookId, quantity: qty }); },
  updateCart(bookId, qty)          { return this.put('/api/cart/update', { book_id: bookId, quantity: qty }); },
  removeFromCart(bookId)           { return this.delete(`/api/cart/remove/${bookId}`); },

  // ── Coupons ───────────────────────────────────────────
  applyCoupon(code, cartTotal)     { return this.post('/api/coupons/apply', { code, cart_total: cartTotal }); },

  // ── Orders ────────────────────────────────────────────
  placeOrder(address, couponCode)  { return this.post('/api/orders/place', { address, coupon_code: couponCode }); },
  getOrderHistory()                { return this.get('/api/orders/history'); },

  // ── Reviews ───────────────────────────────────────────
  getReviews(bookId)               { return this.get(`/api/reviews/${bookId}`); },
  addReview(bookId, rating, text)  { return this.post('/api/reviews/add', { book_id: bookId, rating, review_text: text }); },

  // ── Wishlist ──────────────────────────────────────────
  getWishlist()                    { return this.get('/api/wishlist'); },
  addToWishlist(bookId)            { return this.post('/api/wishlist/add', { book_id: bookId }); },
  removeFromWishlist(bookId)       { return this.delete(`/api/wishlist/remove/${bookId}`); },

  // ── Admin ─────────────────────────────────────────────
  adminStats()                     { return this.get('/api/admin/stats'); },
  adminBooks()                     { return this.get('/api/admin/books'); },
  adminAddBook(payload)            { return this.post('/api/admin/books/add', payload); },
  adminEditBook(id, payload)       { return this.put(`/api/admin/books/edit/${id}`, payload); },
  adminDeleteBook(id)              { return this.delete(`/api/admin/books/delete/${id}`); },
  adminOrders()                    { return this.get('/api/admin/orders'); },
  adminUpdateOrder(id, status)     { return this.put(`/api/admin/orders/update/${id}`, { status }); },
  adminSearchLogs(limit = 100)     { return this.get(`/api/admin/search-logs?limit=${limit}`); },
  adminLowStock()                  { return this.get('/api/admin/low-stock'); },
  adminRebuildIndex()              { return this.post('/api/admin/rebuild-index', {}); },
  adminAuthors()                   { return this.get('/api/admin/authors'); },
};

/* ═══════════════════════════════════════════════════════════
   FORMATTING UTILITIES
═══════════════════════════════════════════════════════════ */
const Fmt = {
  /**
   * Format a number as Indian Rupees.
   * e.g. 1299  → "₹1,299"
   *      499.5 → "₹499.50"
   */
  inr(amount) {
    return '₹' + parseFloat(amount || 0).toLocaleString('en-IN', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    });
  },

  /** Escape HTML special chars to prevent XSS */
  esc(str) {
    return (str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  },

  /** Format ISO date to Indian locale */
  date(isoStr) {
    if (!isoStr) return '—';
    return new Date(isoStr).toLocaleDateString('en-IN', {
      day: 'numeric', month: 'short', year: 'numeric',
    });
  },

  /** Relative time e.g. "2 hours ago" */
  relativeTime(isoStr) {
    if (!isoStr) return '';
    const diff = (Date.now() - new Date(isoStr)) / 1000;
    if (diff < 60)   return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return Fmt.date(isoStr);
  },

  /** Avatar initials from name */
  initials(name) {
    return (name || 'U').split(' ').map(w => w[0] || '').join('').toUpperCase().slice(0, 2);
  },

  /** Star rating HTML (1–5, half-star support) */
  stars(rating, size = 'text-sm') {
    const r = parseFloat(rating) || 0;
    let html = '';
    for (let i = 1; i <= 5; i++) {
      if (r >= i)
        html += `<span class="material-symbols-outlined ${size}" style="font-variation-settings:'FILL' 1">star</span>`;
      else if (r >= i - 0.5)
        html += `<span class="material-symbols-outlined ${size}" style="font-variation-settings:'FILL' 1">star_half</span>`;
      else
        html += `<span class="material-symbols-outlined ${size}" style="color:rgba(117,119,127,0.25)">star</span>`;
    }
    return html;
  },

  /** Order status badge HTML */
  statusBadge(status) {
    const map = {
      Pending:    'status-pending',
      Processing: 'status-processing',
      Shipped:    'status-shipped',
      Delivered:  'status-delivered',
      Cancelled:  'status-cancelled',
    };
    const cls = map[status] || 'status-pending';
    return `<span class="status-pill ${cls}">${Fmt.esc(status)}</span>`;
  },

  /** Book cover src with fallback */
  cover(url, idx = 0) {
    if (url && url.startsWith('http')) return url;
    return SHELF.FALLBACK_COVERS[idx % SHELF.FALLBACK_COVERS.length];
  },
};

/* ═══════════════════════════════════════════════════════════
   TOAST
═══════════════════════════════════════════════════════════ */
const Toast = {
  _timer: null,
  show(msg, type = 'success') {
    let el = document.getElementById('toast');
    if (!el) {
      el = document.createElement('div');
      el.id = 'toast';
      el.className = 'toast';
      el.innerHTML = `<span id="toast-icon" class="material-symbols-outlined text-base"></span><span id="toast-msg"></span>`;
      document.body.appendChild(el);
    }
    document.getElementById('toast-icon').textContent = type === 'success' ? 'check_circle' : 'error';
    document.getElementById('toast-msg').textContent  = msg;
    el.classList.remove('error');
    if (type === 'error') el.classList.add('error');
    el.classList.add('show');
    clearTimeout(this._timer);
    this._timer = setTimeout(() => el.classList.remove('show'), 3200);
  },
  success(msg)  { this.show(msg, 'success'); },
  error(msg)    { this.show(msg, 'error'); },
};

/* ═══════════════════════════════════════════════════════════
   CART STATE
═══════════════════════════════════════════════════════════ */
const Cart = {
  _count: 0,

  getBadgeEl() { return document.getElementById('cart-badge'); },

  setCount(n) {
    this._count = n;
    const badge = this.getBadgeEl();
    if (!badge) return;
    badge.textContent = n > 9 ? '9+' : n;
    if (n > 0) {
      badge.classList.remove('hidden');
      badge.classList.add('badge-pop');
      setTimeout(() => badge.classList.remove('badge-pop'), 300);
    } else {
      badge.classList.add('hidden');
    }
  },

  increment() { this.setCount(this._count + 1); },

  async sync() {
    if (!Auth.hasToken()) return;
    const data = await API.getCart();
    if (data.status === 'ok') {
      this.setCount((data.data.items || []).reduce((s, i) => s + (i.quantity || 1), 0));
    }
  },

  async add(bookId, title) {
    if (!Auth.hasToken()) {
      Toast.error('Please login to add books to cart.');
      setTimeout(() => {
        window.location.href = `/auth?redirect=${encodeURIComponent(window.location.pathname)}`;
      }, 1200);
      return false;
    }
    const data = await API.addToCart(bookId, 1);
    if (data.status === 'ok') {
      Toast.success(`"${title}" added to cart!`);
      this.increment();
      return true;
    } else {
      Toast.error(data.message || 'Could not add to cart.');
      return false;
    }
  },
};

/* ═══════════════════════════════════════════════════════════
   DEBOUNCE UTILITY
═══════════════════════════════════════════════════════════ */
function debounce(fn, delay = 400) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}

/* ═══════════════════════════════════════════════════════════
   DOM HELPERS
═══════════════════════════════════════════════════════════ */
const DOM = {
  $: (sel, ctx = document) => ctx.querySelector(sel),
  $$: (sel, ctx = document) => [...ctx.querySelectorAll(sel)],

  show(el)  { if (el) el.classList.remove('hidden'); },
  hide(el)  { if (el) el.classList.add('hidden'); },
  toggle(el, force) { if (el) el.classList.toggle('hidden', force === undefined ? undefined : !force); },

  setText(sel, text) {
    const el = typeof sel === 'string' ? document.getElementById(sel) : sel;
    if (el) el.textContent = text;
  },

  setHtml(sel, html) {
    const el = typeof sel === 'string' ? document.getElementById(sel) : sel;
    if (el) el.innerHTML = html;
  },

  /** Show a loading spinner inside a button */
  btnLoading(btn, loading, originalText = '') {
    if (!btn) return;
    btn.disabled = loading;
    if (loading) {
      btn._origText = btn.textContent;
      btn.innerHTML = `<span class="material-symbols-outlined text-sm spin">progress_activity</span>&nbsp;Please wait…`;
    } else {
      btn.innerHTML = originalText || btn._origText || 'Submit';
    }
  },

  /** Smoothly scroll to element */
  scrollTo(el, offset = 100) {
    if (!el) return;
    const y = el.getBoundingClientRect().top + window.scrollY - offset;
    window.scrollTo({ top: y, behavior: 'smooth' });
  },
};

/* ═══════════════════════════════════════════════════════════
   NAV — shared auth area renderer
═══════════════════════════════════════════════════════════ */
const Nav = {
  async init() {
    await Cart.sync();
    const area = document.getElementById('auth-area');
    if (!area) return;

    if (!Auth.hasToken()) {
      area.innerHTML = `
        <a href="/auth"
           class="bg-primary text-on-primary px-6 py-2 rounded-md font-label text-sm font-bold hover:bg-primary-container transition-colors">
          Login
        </a>`;
      return;
    }

    const data = await API.getMe();
    if (data.status !== 'ok') { Auth.removeToken(); return; }

    const user = data.data;
    Auth.setUser(user);

    area.innerHTML = `
      <div class="flex items-center gap-3">
        <span class="text-sm font-label font-bold text-primary hidden md:block">
          Hi, ${Fmt.esc(user.name.split(' ')[0])}
        </span>
        ${user.is_admin
          ? `<a href="/admin" class="text-xs font-label font-bold text-secondary hover:underline">Admin ↗</a>`
          : ''}
        <button onclick="Auth.logout()"
          class="border border-primary/20 text-primary px-4 py-2 rounded-md font-label text-xs font-bold hover:bg-primary hover:text-on-primary transition-colors">
          Logout
        </button>
      </div>`;
  },
};

/* ═══════════════════════════════════════════════════════════
   BOOK CARD FACTORY
   Creates a book card element for the catalog grid
═══════════════════════════════════════════════════════════ */
function createBookCard(book, index = 0) {
  const card = document.createElement('div');
  card.className = 'book-card flex flex-col group cursor-pointer';

  const score = book.similarity_score
    ? `<div class="score-badge">${Math.round(book.similarity_score * 100)}% match</div>`
    : '';

  const stockLabel = book.stock === 0
    ? `<span class="stock-out text-[10px]">Out of Stock</span>`
    : book.stock <= SHELF.LOW_STOCK_THRESHOLD
    ? `<span class="stock-low text-[10px]">Only ${book.stock} left</span>`
    : '';

  const moodTag = book.mood_tags
    ? `<span class="text-[10px] font-label uppercase tracking-widest text-secondary/60">${Fmt.esc(book.mood_tags.split(',')[0].trim())}</span>`
    : '';

  card.innerHTML = `
    <a href="/book/${book.book_id}" class="block">
      <div class="book-card-cover mb-6 relative">
        <img src="${Fmt.cover(book.cover_url, index)}"
             alt="${Fmt.esc(book.title)}"
             class="w-full h-full object-cover"
             loading="lazy"
             onerror="this.style.display='none'"/>
        ${score}
      </div>
    </a>

    <div class="flex justify-between items-start mb-1">
      <a href="/book/${book.book_id}" class="flex-1 pr-2">
        <h4 class="book-card-title">${Fmt.esc(book.title)}</h4>
      </a>
      <div class="flex items-center text-secondary shrink-0 gap-0.5">
        <span class="material-symbols-outlined text-xs" style="font-variation-settings:'FILL' 1">star</span>
        <span class="text-xs font-label font-bold">${parseFloat(book.avg_rating || 0).toFixed(1)}</span>
      </div>
    </div>

    <p class="book-card-author">${Fmt.esc(book.author || '')}</p>

    <div class="flex items-center gap-2 mb-4">
      ${moodTag}
      ${stockLabel}
    </div>

    <div class="mt-auto flex items-center justify-between">
      <span class="book-card-price">${Fmt.inr(book.price)}</span>
      <button class="add-to-cart-btn"
              data-book-id="${book.book_id}"
              data-title="${Fmt.esc(book.title)}"
              ${book.stock === 0 ? 'disabled' : ''}>
        ADD TO CART
      </button>
    </div>
  `;

  card.querySelector('.add-to-cart-btn')?.addEventListener('click', (e) => {
    e.preventDefault();
    Cart.add(book.book_id, book.title);
  });

  return card;
}

/* ═══════════════════════════════════════════════════════════
   SEARCH STATE (used by index.html)
═══════════════════════════════════════════════════════════ */
const Search = {
  mode: 'semantic',
  query: '',
  activeMood: null,
  offset: 0,
  limit: 12,

  toggleMode() {
    this.mode = this.mode === 'semantic' ? 'keyword' : 'semantic';
  },

  setMood(mood) {
    this.activeMood = this.activeMood === mood ? null : mood;
  },

  clearMoods() {
    this.activeMood = null;
    document.querySelectorAll('.mood-pill').forEach(p => p.classList.remove('active'));
  },

  reset() {
    this.query = '';
    this.offset = 0;
    this.clearMoods();
  },
};

/* ═══════════════════════════════════════════════════════════
   PASSWORD STRENGTH METER
═══════════════════════════════════════════════════════════ */
function calcPasswordStrength(pw) {
  if (!pw) return { score: 0, label: '', color: 'transparent', pct: '0%' };
  let score = 0;
  if (pw.length >= 6)             score++;
  if (pw.length >= 10)            score++;
  if (/[A-Z]/.test(pw))          score++;
  if (/[0-9]/.test(pw))          score++;
  if (/[^A-Za-z0-9]/.test(pw))   score++;

  const levels = [
    { pct: '0%',   color: 'transparent', label: '' },
    { pct: '20%',  color: '#ba1a1a',     label: 'Very weak' },
    { pct: '40%',  color: '#e65c00',     label: 'Weak' },
    { pct: '65%',  color: '#e6c364',     label: 'Fair' },
    { pct: '85%',  color: '#4caf50',     label: 'Strong' },
    { pct: '100%', color: '#388e3c',     label: 'Very strong' },
  ];
  return levels[Math.min(score, 5)];
}

/* ═══════════════════════════════════════════════════════════
   PAGE DETECTION & AUTO-INIT
═══════════════════════════════════════════════════════════ */
function currentPage() {
  const path = window.location.pathname;
  if (path === '/' || path === '/index' || path.endsWith('index.html')) return 'index';
  if (path.startsWith('/book/'))                                         return 'book';
  if (path === '/auth' || path.endsWith('auth.html'))                    return 'auth';
  if (path === '/cart' || path.endsWith('cart.html'))                    return 'cart';
  if (path === '/admin' || path.endsWith('admin.html'))                  return 'admin';
  return 'unknown';
}

document.addEventListener('DOMContentLoaded', () => {
  const page = currentPage();

  // Always init nav (cart badge + auth area) except on auth/admin pages
  if (page !== 'auth' && page !== 'admin') {
    Nav.init();
  }

  // Page-specific inits (heavy logic lives in each template's <script>)
  // This file only wires global utilities.
  // The inline scripts in each template call API.*, Cart.*, Auth.*, etc.

  // Wire nav search bar (book detail page)
  const navSearch = document.getElementById('nav-search');
  if (navSearch) {
    navSearch.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const q = e.target.value.trim();
        if (q) window.location.href = `/?q=${encodeURIComponent(q)}`;
      }
    });
  }

  // Global: pressing Escape closes any open modal
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-overlay.open, #book-modal.open, #confirm-modal.open, #order-modal').forEach(m => {
        m.classList.remove('open');
        if (m.id === 'order-modal') m.classList.add('hidden');
      });
    }
  });
});

/* ═══════════════════════════════════════════════════════════
   EXPOSE GLOBALS
   Templates reference Auth, API, Cart, Toast, Fmt, DOM, etc.
═══════════════════════════════════════════════════════════ */
window.SHELF    = SHELF;
window.Auth     = Auth;
window.API      = API;
window.Cart     = Cart;
window.Toast    = Toast;
window.Fmt      = Fmt;
window.DOM      = DOM;
window.Search   = Search;
window.debounce = debounce;
window.createBookCard         = createBookCard;
window.calcPasswordStrength   = calcPasswordStrength;
