"""
app.py — Shelf Bookstore Flask Application
All REST API routes for frontend ↔ backend communication.
"""

import json
import logging
from datetime import timedelta
from functools import wraps

from flask import Flask, request, jsonify, render_template, g
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required,
    get_jwt_identity, verify_jwt_in_request
)
from flask_cors import CORS
import bcrypt

from config import Config
import models
import embeddings as emb

# ──────────────────────────────────────────────────────────────
#  App Setup
# ──────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY']            = Config.SECRET_KEY
app.config['JWT_SECRET_KEY']        = Config.JWT_SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(seconds=Config.JWT_ACCESS_TOKEN_EXPIRES)
app.config['JSON_SORT_KEYS']        = False

CORS(app, resources={r"/api/*": {"origins": Config.CORS_ORIGINS}})
jwt = JWTManager(app)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────

def ok(data=None, msg="success", code=200):
    return jsonify({"status": "ok", "message": msg, "data": data}), code

def err(msg="error", code=400):
    return jsonify({"status": "error", "message": msg}), code

def optional_jwt_identity():
    """Return user_id if a valid JWT is present, else None."""
    try:
        verify_jwt_in_request(optional=True)
        return get_jwt_identity()
    except Exception:
        return None

def admin_required(fn):
    """Decorator: JWT + is_admin check."""
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = models.get_user_by_id(user_id)
        if not user or not user.get('is_admin'):
            return err("Admin access required.", 403)
        return fn(*args, **kwargs)
    return wrapper

def serialize_dates(obj):
    """Make datetime objects JSON-serialisable."""
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serialisable")


# ──────────────────────────────────────────────────────────────
#  Startup
# ──────────────────────────────────────────────────────────────

@app.before_request
def _load_index_once():
    """Load the FAISS index into memory before the first real request."""
    if not hasattr(app, '_index_loaded'):
        try:
            emb.load_index()
        except Exception as e:
            logger.error(f"Could not load FAISS index: {e}")
        app._index_loaded = True


# ══════════════════════════════════════════════════════════════
#  PAGE ROUTES  (serve HTML templates)
# ══════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/book/<int:book_id>')
def book_page(book_id):
    return render_template('book.html', book_id=book_id)

@app.route('/auth')
def auth_page():
    return render_template('auth.html')

@app.route('/cart')
def cart_page():
    return render_template('cart.html')

@app.route('/admin')
def admin_page():
    return render_template('admin.html')


# ══════════════════════════════════════════════════════════════
#  AUTH  /api/auth/
# ══════════════════════════════════════════════════════════════

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json(force=True)
    name        = (data.get('name') or '').strip()
    email       = (data.get('email') or '').strip().lower()
    password    = data.get('password') or ''
    preferences = data.get('preferences', {})

    if not name or not email or not password:
        return err("Name, email and password are required.")
    if len(password) < 6:
        return err("Password must be at least 6 characters.")

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    pref_json = json.dumps(preferences)

    user_id = models.create_user(name, email, pw_hash, pref_json)
    if user_id is None:
        return err("Email already registered.", 409)

    token = create_access_token(identity=user_id)
    user  = models.get_user_by_id(user_id)
    return ok({"token": token, "user": user}, "Registered successfully.", 201)


@app.route('/api/auth/login', methods=['POST'])
def login():
    data     = request.get_json(force=True)
    email    = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return err("Email and password are required.")

    user = models.get_user_by_email(email)
    if not user:
        return err("Invalid credentials.", 401)

    if not bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
        return err("Invalid credentials.", 401)

    token = create_access_token(identity=user['user_id'])
    safe_user = {k: v for k, v in user.items() if k != 'password_hash'}
    return ok({"token": token, "user": safe_user})


@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user    = models.get_user_by_id(user_id)
    if not user:
        return err("User not found.", 404)
    return ok(user)


@app.route('/api/auth/preferences', methods=['PUT'])
@jwt_required()
def update_preferences():
    user_id = get_jwt_identity()
    data    = request.get_json(force=True)
    prefs   = data.get('preferences', {})
    models.update_user_preferences(user_id, json.dumps(prefs))
    return ok(msg="Preferences updated.")


# ══════════════════════════════════════════════════════════════
#  BOOKS  /api/books/
# ══════════════════════════════════════════════════════════════

@app.route('/api/books', methods=['GET'])
def list_books():
    limit  = min(int(request.args.get('limit',  50)), 100)
    offset = int(request.args.get('offset', 0))
    books  = models.get_all_books(limit, offset)
    # convert datetime → string
    for b in books:
        for k, v in b.items():
            if hasattr(v, 'isoformat'):
                b[k] = v.isoformat()
    return ok(books)


@app.route('/api/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    book = models.get_book_by_id(book_id)
    if not book:
        return err("Book not found.", 404)
    for k, v in book.items():
        if hasattr(v, 'isoformat'):
            book[k] = v.isoformat()
    return ok(book)


@app.route('/api/books/author/<int:author_id>', methods=['GET'])
def get_author(author_id):
    author = models.get_author_by_id(author_id)
    if not author:
        return err("Author not found.", 404)
    return ok(author)


@app.route('/api/books/categories', methods=['GET'])
def get_categories():
    return ok(models.get_all_categories())


# ══════════════════════════════════════════════════════════════
#  SEARCH  /api/search/
# ══════════════════════════════════════════════════════════════

@app.route('/api/search', methods=['GET'])
def search():
    query = (request.args.get('q') or '').strip()
    mode  = request.args.get('mode', 'semantic')   # 'semantic' | 'keyword'
    mood  = (request.args.get('mood') or '').strip()
    limit = min(int(request.args.get('limit', 20)), Config.MAX_SEARCH_RESULTS)

    user_id = optional_jwt_identity()

    if mood and not query:
        # mood-only filter
        books = models.get_books_by_mood(mood, limit)
        _clean_dates(books)
        models.log_search(user_id, f'[mood] {mood}', 'keyword', len(books))
        return ok({'books': books, 'mode': 'mood', 'query': mood, 'total': len(books)})

    if not query:
        return err("Search query is required.")

    if mode == 'keyword':
        books = models.search_books_keyword(query, limit)
        _clean_dates(books)
        models.log_search(user_id, query, 'keyword', len(books))
        return ok({'books': books, 'mode': 'keyword', 'query': query, 'total': len(books)})

    # ── Semantic search ──
    try:
        results = emb.semantic_search(query, top_k=limit)
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        # graceful fallback to keyword
        books = models.search_books_keyword(query, limit)
        _clean_dates(books)
        models.log_search(user_id, query, 'keyword', len(books))
        return ok({'books': books, 'mode': 'keyword_fallback', 'query': query, 'total': len(books)})

    if not results:
        models.log_search(user_id, query, 'semantic', 0)
        return ok({'books': [], 'mode': 'semantic', 'query': query, 'total': 0})

    book_ids = [r['book_id'] for r in results]
    score_map = {r['book_id']: r['score'] for r in results}

    books = models.get_books_by_ids(book_ids)
    _clean_dates(books)
    for b in books:
        b['similarity_score'] = score_map.get(b['book_id'], 0)

    models.log_search(user_id, query, 'semantic', len(books))
    return ok({'books': books, 'mode': 'semantic', 'query': query, 'total': len(books)})


@app.route('/api/search/similar/<int:book_id>', methods=['GET'])
def similar_books(book_id):
    top_k   = min(int(request.args.get('limit', 8)), 12)
    results = emb.more_like_this(book_id, top_k=top_k)

    if not results:
        return ok({'books': [], 'book_id': book_id})

    book_ids  = [r['book_id'] for r in results]
    score_map = {r['book_id']: r['score'] for r in results}
    books = models.get_books_by_ids(book_ids)
    _clean_dates(books)
    for b in books:
        b['similarity_score'] = score_map.get(b['book_id'], 0)

    return ok({'books': books, 'book_id': book_id})


# ══════════════════════════════════════════════════════════════
#  CART  /api/cart/
# ══════════════════════════════════════════════════════════════

@app.route('/api/cart', methods=['GET'])
@jwt_required()
def get_cart():
    user_id = get_jwt_identity()
    cart    = models.get_cart(user_id)
    _clean_dates(cart)
    total   = sum(item['price'] * item['quantity'] for item in cart)
    return ok({'items': cart, 'subtotal': round(total, 2)})


@app.route('/api/cart/add', methods=['POST'])
@jwt_required()
def add_to_cart():
    user_id  = get_jwt_identity()
    data     = request.get_json(force=True)
    book_id  = data.get('book_id')
    quantity = int(data.get('quantity', 1))

    if not book_id:
        return err("book_id is required.")
    if quantity < 1:
        return err("Quantity must be at least 1.")

    book = models.get_book_by_id(book_id)
    if not book:
        return err("Book not found.", 404)
    if book['stock'] < quantity:
        return err(f"Only {book['stock']} copies in stock.")

    models.add_to_cart(user_id, book_id, quantity)
    return ok(msg="Added to cart.")


@app.route('/api/cart/update', methods=['PUT'])
@jwt_required()
def update_cart():
    user_id  = get_jwt_identity()
    data     = request.get_json(force=True)
    book_id  = data.get('book_id')
    quantity = int(data.get('quantity', 1))

    if not book_id:
        return err("book_id is required.")

    models.update_cart_quantity(user_id, book_id, quantity)
    return ok(msg="Cart updated.")


@app.route('/api/cart/remove/<int:book_id>', methods=['DELETE'])
@jwt_required()
def remove_from_cart(book_id):
    user_id = get_jwt_identity()
    removed = models.remove_from_cart(user_id, book_id)
    if not removed:
        return err("Item not in cart.", 404)
    return ok(msg="Removed from cart.")


# ══════════════════════════════════════════════════════════════
#  COUPONS  /api/coupons/
# ══════════════════════════════════════════════════════════════

@app.route('/api/coupons/apply', methods=['POST'])
@jwt_required()
def apply_coupon():
    data          = request.get_json(force=True)
    code          = (data.get('code') or '').strip().upper()
    cart_total    = float(data.get('cart_total', 0))

    if not code:
        return err("Coupon code is required.")

    coupon = models.validate_coupon(code)
    if not coupon:
        return err("Invalid or expired coupon code.", 404)

    if cart_total < float(coupon['min_order_amt']):
        return err(f"Minimum order ₹{coupon['min_order_amt']} required for this coupon.")

    discount_pct = coupon['discount_pct']
    discount_amt = round(cart_total * discount_pct / 100, 2)
    final_total  = round(cart_total - discount_amt, 2)

    return ok({
        'code':         code,
        'discount_pct': discount_pct,
        'discount_amt': discount_amt,
        'final_total':  final_total
    })


# ══════════════════════════════════════════════════════════════
#  ORDERS  /api/orders/
# ══════════════════════════════════════════════════════════════

@app.route('/api/orders/place', methods=['POST'])
@jwt_required()
def place_order():
    user_id = get_jwt_identity()
    data    = request.get_json(force=True)
    address = (data.get('address') or '').strip()
    coupon_code = (data.get('coupon_code') or '').strip().upper() or None

    if not address:
        return err("Delivery address is required.")

    cart = models.get_cart(user_id)
    if not cart:
        return err("Your cart is empty.")

    # Stock check
    for item in cart:
        if item['stock'] < item['quantity']:
            return err(f"'{item['title']}' has only {item['stock']} copies in stock.")

    subtotal = sum(i['price'] * i['quantity'] for i in cart)
    discount_amt = 0.0

    if coupon_code:
        coupon = models.validate_coupon(coupon_code)
        if coupon and subtotal >= float(coupon['min_order_amt']):
            discount_amt = round(subtotal * coupon['discount_pct'] / 100, 2)
            models.increment_coupon_usage(coupon_code)
        else:
            coupon_code = None   # invalid coupon → ignore silently

    total_amount = round(subtotal - discount_amt, 2)

    order_id = models.create_order(
        user_id, total_amount, discount_amt, coupon_code, address
    )

    order_items = [
        {
            'book_id':           item['book_id'],
            'quantity':          item['quantity'],
            'price_at_purchase': item['price']
        }
        for item in cart
    ]
    models.add_order_items(order_id, order_items)
    models.clear_cart(user_id)

    return ok({
        'order_id':     order_id,
        'total_amount': total_amount,
        'discount_amt': discount_amt,
        'coupon_used':  coupon_code
    }, "Order placed successfully!", 201)


@app.route('/api/orders/history', methods=['GET'])
@jwt_required()
def order_history():
    user_id = get_jwt_identity()
    orders  = models.get_order_history(user_id)
    _clean_dates(orders)
    for order in orders:
        _clean_dates(order.get('items', []))
    return ok(orders)


# ══════════════════════════════════════════════════════════════
#  REVIEWS  /api/reviews/
# ══════════════════════════════════════════════════════════════

@app.route('/api/reviews/<int:book_id>', methods=['GET'])
def get_reviews(book_id):
    reviews = models.get_reviews_for_book(book_id)
    _clean_dates(reviews)
    return ok(reviews)


@app.route('/api/reviews/add', methods=['POST'])
@jwt_required()
def add_review():
    user_id     = get_jwt_identity()
    data        = request.get_json(force=True)
    book_id     = data.get('book_id')
    rating      = int(data.get('rating', 0))
    review_text = (data.get('review_text') or '').strip()

    if not book_id:
        return err("book_id is required.")
    if rating < 1 or rating > 5:
        return err("Rating must be between 1 and 5.")

    models.add_review(user_id, book_id, rating, review_text)
    return ok(msg="Review submitted.")


# ══════════════════════════════════════════════════════════════
#  WISHLIST  /api/wishlist/
# ══════════════════════════════════════════════════════════════

@app.route('/api/wishlist', methods=['GET'])
@jwt_required()
def get_wishlist():
    user_id = get_jwt_identity()
    items   = models.get_wishlist(user_id)
    _clean_dates(items)
    return ok(items)


@app.route('/api/wishlist/add', methods=['POST'])
@jwt_required()
def add_to_wishlist():
    user_id = get_jwt_identity()
    data    = request.get_json(force=True)
    book_id = data.get('book_id')
    if not book_id:
        return err("book_id is required.")
    models.add_to_wishlist(user_id, book_id)
    return ok(msg="Added to wishlist.")


@app.route('/api/wishlist/remove/<int:book_id>', methods=['DELETE'])
@jwt_required()
def remove_from_wishlist(book_id):
    user_id = get_jwt_identity()
    models.remove_from_wishlist(user_id, book_id)
    return ok(msg="Removed from wishlist.")


# ══════════════════════════════════════════════════════════════
#  ADMIN  /api/admin/
# ══════════════════════════════════════════════════════════════

@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def admin_stats():
    stats = models.get_admin_stats()
    # convert any date keys
    for item in stats.get('weekly_chart', []):
        _clean_obj(item)
    return ok(stats)


@app.route('/api/admin/books', methods=['GET'])
@admin_required
def admin_books():
    books = models.get_all_books_admin()
    _clean_dates(books)
    return ok(books)


@app.route('/api/admin/books/add', methods=['POST'])
@admin_required
def admin_add_book():
    data = request.get_json(force=True)
    required = ['title', 'synopsis', 'price', 'stock']
    for f in required:
        if not data.get(f):
            return err(f"'{f}' is required.")

    # Resolve author
    author_name = (data.get('author_name') or '').strip()
    author_id   = data.get('author_id')
    if not author_id and not author_name:
        return err("author_id or author_name is required.")
    if author_name and not author_id:
        author_id = models.get_or_create_author(
            author_name,
            data.get('author_nationality', ''),
            data.get('author_bio', '')
        )

    book_id = models.add_book(
        title          = data['title'].strip(),
        author_id      = int(author_id),
        synopsis       = data['synopsis'].strip(),
        price          = float(data['price']),
        stock          = int(data['stock']),
        cover_url      = data.get('cover_url', ''),
        language       = data.get('language', 'English'),
        isbn           = data.get('isbn', ''),
        published_year = data.get('published_year'),
        pages          = data.get('pages'),
        mood_tags      = data.get('mood_tags', '')
    )

    # Set categories
    cat_ids = data.get('category_ids', [])
    if cat_ids:
        models.set_book_categories(book_id, cat_ids)

    # Generate and store embedding
    try:
        emb.add_book_to_index(book_id, data['synopsis'])
    except Exception as e:
        logger.error(f"Embedding failed for new book {book_id}: {e}")

    return ok({'book_id': book_id}, "Book added successfully.", 201)


@app.route('/api/admin/books/edit/<int:book_id>', methods=['PUT'])
@admin_required
def admin_edit_book(book_id):
    data   = request.get_json(force=True)
    fields = {}
    allowed = ['title', 'synopsis', 'price', 'stock', 'cover_url',
               'language', 'isbn', 'published_year', 'pages', 'mood_tags', 'is_active']
    for f in allowed:
        if f in data:
            fields[f] = data[f]

    if not fields:
        return err("No updatable fields provided.")

    updated = models.update_book(book_id, fields)
    if not updated:
        return err("Book not found.", 404)

    # Re-embed if synopsis changed
    if 'synopsis' in fields:
        try:
            emb.add_book_to_index(book_id, fields['synopsis'])
        except Exception as e:
            logger.error(f"Re-embedding failed for book {book_id}: {e}")

    # Update categories
    cat_ids = data.get('category_ids')
    if cat_ids is not None:
        models.set_book_categories(book_id, cat_ids)

    return ok(msg="Book updated successfully.")


@app.route('/api/admin/books/delete/<int:book_id>', methods=['DELETE'])
@admin_required
def admin_delete_book(book_id):
    deleted = models.soft_delete_book(book_id)
    if not deleted:
        return err("Book not found.", 404)
    return ok(msg="Book deleted.")


@app.route('/api/admin/orders', methods=['GET'])
@admin_required
def admin_orders():
    orders = models.get_all_orders_admin()
    _clean_dates(orders)
    for order in orders:
        _clean_dates(order.get('items', []))
    return ok(orders)


@app.route('/api/admin/orders/update/<int:order_id>', methods=['PUT'])
@admin_required
def admin_update_order(order_id):
    data   = request.get_json(force=True)
    status = data.get('status')
    valid  = ('Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled')
    if status not in valid:
        return err(f"Status must be one of: {', '.join(valid)}")
    updated = models.update_order_status(order_id, status)
    if not updated:
        return err("Order not found.", 404)
    return ok(msg="Order status updated.")


@app.route('/api/admin/search-logs', methods=['GET'])
@admin_required
def admin_search_logs():
    limit = min(int(request.args.get('limit', 100)), 500)
    logs  = models.get_search_logs(limit)
    _clean_dates(logs)
    return ok(logs)


@app.route('/api/admin/low-stock', methods=['GET'])
@admin_required
def admin_low_stock():
    books = models.get_low_stock_books()
    return ok(books)


@app.route('/api/admin/rebuild-index', methods=['POST'])
@admin_required
def admin_rebuild_index():
    try:
        emb.rebuild_index()
        return ok(msg="FAISS index rebuilt successfully.")
    except Exception as e:
        logger.error(f"Index rebuild failed: {e}")
        return err(f"Index rebuild failed: {e}", 500)


@app.route('/api/admin/authors', methods=['GET'])
@admin_required
def admin_authors():
    authors = models.get_all_authors()
    return ok(authors)


# ══════════════════════════════════════════════════════════════
#  Error Handlers
# ══════════════════════════════════════════════════════════════

@app.errorhandler(404)
def not_found(e):
    return err("Resource not found.", 404)

@app.errorhandler(405)
def method_not_allowed(e):
    return err("Method not allowed.", 405)

@app.errorhandler(500)
def server_error(e):
    logger.exception("Internal server error")
    return err("Internal server error.", 500)

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_data):
    return err("Token has expired. Please log in again.", 401)

@jwt.invalid_token_loader
def invalid_token_callback(reason):
    return err(f"Invalid token: {reason}", 401)

@jwt.unauthorized_loader
def missing_token_callback(reason):
    return err("Authentication required.", 401)


# ──────────────────────────────────────────────────────────────
#  Utility
# ──────────────────────────────────────────────────────────────

def _clean_obj(obj: dict):
    """Convert datetime values in a single dict to ISO strings."""
    for k, v in obj.items():
        if hasattr(v, 'isoformat'):
            obj[k] = v.isoformat()

def _clean_dates(lst: list):
    """Convert datetime values in a list of dicts to ISO strings."""
    for obj in lst:
        if isinstance(obj, dict):
            _clean_obj(obj)


# ──────────────────────────────────────────────────────────────
#  Run
# ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=Config.DEBUG,
        use_reloader=False   # prevent double model load in debug mode
    )
