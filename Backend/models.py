"""
models.py — All raw MySQL query functions for Shelf Bookstore.
Uses mysql-connector-python directly (no ORM).
Every function opens a connection from pool, executes, and closes.
"""

import mysql.connector
from mysql.connector import pooling
from config import Config
import logging

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
#  Connection Pool
# ──────────────────────────────────────────────────────────────
_pool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="shelf_pool",
            pool_size=10,
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset='utf8mb4',
            autocommit=False
        )
    return _pool

def get_conn():
    return get_pool().get_connection()


# ──────────────────────────────────────────────────────────────
#  Helper
# ──────────────────────────────────────────────────────────────
def _row_to_dict(cursor, row):
    """Convert a tuple row to a dict using cursor column names."""
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))

def _fetchall_dict(cursor):
    rows = cursor.fetchall()
    return [_row_to_dict(cursor, r) for r in rows]

def _fetchone_dict(cursor):
    row = cursor.fetchone()
    return _row_to_dict(cursor, row) if row else None


# ══════════════════════════════════════════════════════════════
#  USERS
# ══════════════════════════════════════════════════════════════

def create_user(name, email, password_hash, preferences=None):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Users (name, email, password_hash, preferences) VALUES (%s,%s,%s,%s)",
            (name, email, password_hash, preferences)
        )
        conn.commit()
        return cur.lastrowid
    except mysql.connector.IntegrityError:
        return None   # duplicate email
    finally:
        conn.close()

def get_user_by_email(email):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM Users WHERE email=%s LIMIT 1", (email,))
        return _fetchone_dict(cur)
    finally:
        conn.close()

def get_user_by_id(user_id):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id,name,email,preferences,is_admin,created_at FROM Users WHERE user_id=%s", (user_id,))
        return _fetchone_dict(cur)
    finally:
        conn.close()

def update_user_preferences(user_id, preferences_json):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE Users SET preferences=%s WHERE user_id=%s", (preferences_json, user_id))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
#  BOOKS
# ══════════════════════════════════════════════════════════════

def get_all_books(limit=100, offset=0):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT b.book_id, b.title, a.name AS author, b.price, b.stock,
                   b.cover_url, b.language, b.published_year, b.pages,
                   b.avg_rating, b.rating_count, b.mood_tags, b.synopsis
            FROM Books b
            JOIN Authors a ON b.author_id = a.author_id
            WHERE b.is_active = 1
            ORDER BY b.rating_count DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))
        return _fetchall_dict(cur)
    finally:
        conn.close()

def get_book_by_id(book_id):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT b.*, a.name AS author_name, a.bio AS author_bio,
                   a.nationality AS author_nationality
            FROM Books b
            JOIN Authors a ON b.author_id = a.author_id
            WHERE b.book_id=%s AND b.is_active=1
        """, (book_id,))
        book = _fetchone_dict(cur)
        if book:
            # attach categories
            cur.execute("""
                SELECT c.name FROM Categories c
                JOIN BookCategories bc ON c.category_id=bc.category_id
                WHERE bc.book_id=%s
            """, (book_id,))
            book['categories'] = [r[0] for r in cur.fetchall()]
        return book
    finally:
        conn.close()

def get_books_by_ids(book_ids):
    if not book_ids:
        return []
    conn = get_conn()
    try:
        cur = conn.cursor()
        placeholders = ','.join(['%s'] * len(book_ids))
        cur.execute(f"""
            SELECT b.book_id, b.title, a.name AS author, b.price, b.stock,
                   b.cover_url, b.avg_rating, b.rating_count, b.mood_tags, b.synopsis
            FROM Books b
            JOIN Authors a ON b.author_id = a.author_id
            WHERE b.book_id IN ({placeholders}) AND b.is_active=1
        """, book_ids)
        rows = _fetchall_dict(cur)
        # preserve the order of book_ids
        order = {bid: i for i, bid in enumerate(book_ids)}
        rows.sort(key=lambda r: order.get(r['book_id'], 9999))
        return rows
    finally:
        conn.close()

def search_books_keyword(query, limit=20):
    conn = get_conn()
    try:
        cur = conn.cursor()
        like = f'%{query}%'
        cur.execute("""
            SELECT b.book_id, b.title, a.name AS author, b.price, b.stock,
                   b.cover_url, b.avg_rating, b.rating_count, b.mood_tags, b.synopsis
            FROM Books b
            JOIN Authors a ON b.author_id = a.author_id
            WHERE b.is_active=1
              AND (b.title LIKE %s OR a.name LIKE %s OR b.synopsis LIKE %s OR b.mood_tags LIKE %s)
            ORDER BY b.rating_count DESC
            LIMIT %s
        """, (like, like, like, like, limit))
        return _fetchall_dict(cur)
    finally:
        conn.close()

def get_books_by_mood(mood_tag, limit=20):
    conn = get_conn()
    try:
        cur = conn.cursor()
        like = f'%{mood_tag}%'
        cur.execute("""
            SELECT b.book_id, b.title, a.name AS author, b.price, b.stock,
                   b.cover_url, b.avg_rating, b.rating_count, b.mood_tags, b.synopsis
            FROM Books b
            JOIN Authors a ON b.author_id = a.author_id
            WHERE b.is_active=1 AND b.mood_tags LIKE %s
            ORDER BY b.avg_rating DESC
            LIMIT %s
        """, (like, limit))
        return _fetchall_dict(cur)
    finally:
        conn.close()

def add_book(title, author_id, synopsis, price, stock, cover_url, language,
             isbn, published_year, pages, mood_tags):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO Books
              (title,author_id,synopsis,price,stock,cover_url,language,isbn,published_year,pages,mood_tags)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (title, author_id, synopsis, price, stock, cover_url, language,
              isbn, published_year, pages, mood_tags))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

def update_book(book_id, fields: dict):
    """fields is a dict of column→value pairs to update."""
    if not fields:
        return False
    conn = get_conn()
    try:
        cur = conn.cursor()
        set_clause = ', '.join(f'{k}=%s' for k in fields)
        vals = list(fields.values()) + [book_id]
        cur.execute(f"UPDATE Books SET {set_clause} WHERE book_id=%s", vals)
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

def soft_delete_book(book_id):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE Books SET is_active=0 WHERE book_id=%s", (book_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

def decrement_stock(book_id, qty):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE Books SET stock = GREATEST(0, stock-%s) WHERE book_id=%s
        """, (qty, book_id))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

def get_all_books_admin(limit=200):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT b.book_id, b.title, a.name AS author, b.price, b.stock,
                   b.cover_url, b.language, b.isbn, b.published_year,
                   b.avg_rating, b.rating_count, b.mood_tags, b.is_active
            FROM Books b
            JOIN Authors a ON b.author_id=a.author_id
            ORDER BY b.book_id DESC
            LIMIT %s
        """, (limit,))
        return _fetchall_dict(cur)
    finally:
        conn.close()

def get_low_stock_books():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT b.book_id, b.title, a.name AS author, b.stock, b.price
            FROM Books b
            JOIN Authors a ON b.author_id=a.author_id
            WHERE b.stock <= %s AND b.is_active=1
            ORDER BY b.stock ASC
        """, (Config.LOW_STOCK_THRESHOLD,))
        return _fetchall_dict(cur)
    finally:
        conn.close()

def get_all_synopses_for_embedding():
    """Returns list of (book_id, synopsis) for all active books."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT book_id, synopsis FROM Books WHERE is_active=1 ORDER BY book_id")
        return cur.fetchall()
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
#  AUTHORS
# ══════════════════════════════════════════════════════════════

def get_all_authors():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM Authors ORDER BY name")
        return _fetchall_dict(cur)
    finally:
        conn.close()

def get_author_by_id(author_id):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM Authors WHERE author_id=%s", (author_id,))
        author = _fetchone_dict(cur)
        if author:
            cur.execute("""
                SELECT b.book_id, b.title, b.price, b.cover_url, b.avg_rating
                FROM Books b WHERE b.author_id=%s AND b.is_active=1
            """, (author_id,))
            author['books'] = _fetchall_dict(cur)
        return author
    finally:
        conn.close()

def get_or_create_author(name, nationality='', bio=''):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT author_id FROM Authors WHERE name=%s LIMIT 1", (name,))
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute(
            "INSERT INTO Authors (name, nationality, bio) VALUES (%s,%s,%s)",
            (name, nationality, bio)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
#  CATEGORIES
# ══════════════════════════════════════════════════════════════

def get_all_categories():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM Categories ORDER BY name")
        return _fetchall_dict(cur)
    finally:
        conn.close()

def set_book_categories(book_id, category_ids):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM BookCategories WHERE book_id=%s", (book_id,))
        for cid in category_ids:
            cur.execute("INSERT IGNORE INTO BookCategories (book_id,category_id) VALUES (%s,%s)", (book_id, cid))
        conn.commit()
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
#  EMBEDDINGS
# ══════════════════════════════════════════════════════════════

def save_embedding(book_id, vector_json):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO Embeddings (book_id, vector_blob)
            VALUES (%s,%s)
            ON DUPLICATE KEY UPDATE vector_blob=%s, updated_at=NOW()
        """, (book_id, vector_json, vector_json))
        conn.commit()
    finally:
        conn.close()

def get_all_embeddings():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT book_id, vector_blob FROM Embeddings")
        return cur.fetchall()
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
#  CART
# ══════════════════════════════════════════════════════════════

def get_cart(user_id):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.cart_id, c.book_id, c.quantity,
                   b.title, b.price, b.cover_url, a.name AS author, b.stock
            FROM Cart c
            JOIN Books b ON c.book_id=b.book_id
            JOIN Authors a ON b.author_id=a.author_id
            WHERE c.user_id=%s
            ORDER BY c.added_at DESC
        """, (user_id,))
        return _fetchall_dict(cur)
    finally:
        conn.close()

def add_to_cart(user_id, book_id, quantity=1):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO Cart (user_id, book_id, quantity)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE quantity = quantity + %s
        """, (user_id, book_id, quantity, quantity))
        conn.commit()
        return True
    finally:
        conn.close()

def update_cart_quantity(user_id, book_id, quantity):
    conn = get_conn()
    try:
        cur = conn.cursor()
        if quantity <= 0:
            cur.execute("DELETE FROM Cart WHERE user_id=%s AND book_id=%s", (user_id, book_id))
        else:
            cur.execute("UPDATE Cart SET quantity=%s WHERE user_id=%s AND book_id=%s",
                        (quantity, user_id, book_id))
        conn.commit()
        return True
    finally:
        conn.close()

def remove_from_cart(user_id, book_id):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM Cart WHERE user_id=%s AND book_id=%s", (user_id, book_id))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

def clear_cart(user_id):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM Cart WHERE user_id=%s", (user_id,))
        conn.commit()
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
#  WISHLIST
# ══════════════════════════════════════════════════════════════

def get_wishlist(user_id):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT w.wishlist_id, b.book_id, b.title, b.price, b.cover_url,
                   a.name AS author, b.avg_rating, b.stock
            FROM Wishlist w
            JOIN Books b ON w.book_id=b.book_id
            JOIN Authors a ON b.author_id=a.author_id
            WHERE w.user_id=%s
            ORDER BY w.added_at DESC
        """, (user_id,))
        return _fetchall_dict(cur)
    finally:
        conn.close()

def add_to_wishlist(user_id, book_id):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("INSERT IGNORE INTO Wishlist (user_id, book_id) VALUES (%s,%s)",
                    (user_id, book_id))
        conn.commit()
        return True
    finally:
        conn.close()

def remove_from_wishlist(user_id, book_id):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM Wishlist WHERE user_id=%s AND book_id=%s",
                    (user_id, book_id))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
#  REVIEWS
# ══════════════════════════════════════════════════════════════

def get_reviews_for_book(book_id):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT r.review_id, r.rating, r.review_text, r.created_at,
                   u.name AS user_name
            FROM Reviews r
            JOIN Users u ON r.user_id=u.user_id
            WHERE r.book_id=%s
            ORDER BY r.created_at DESC
        """, (book_id,))
        return _fetchall_dict(cur)
    finally:
        conn.close()

def add_review(user_id, book_id, rating, review_text):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO Reviews (user_id, book_id, rating, review_text)
            VALUES (%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE rating=%s, review_text=%s, created_at=NOW()
        """, (user_id, book_id, rating, review_text, rating, review_text))
        conn.commit()
        # recalculate avg_rating and rating_count
        cur.execute("""
            UPDATE Books SET
                avg_rating = (SELECT ROUND(AVG(rating),2) FROM Reviews WHERE book_id=%s),
                rating_count = (SELECT COUNT(*) FROM Reviews WHERE book_id=%s)
            WHERE book_id=%s
        """, (book_id, book_id, book_id))
        conn.commit()
        return True
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
#  ORDERS
# ══════════════════════════════════════════════════════════════

def create_order(user_id, total_amount, discount_amt, coupon_used, address):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO Orders (user_id, total_amount, discount_amt, coupon_used, address)
            VALUES (%s,%s,%s,%s,%s)
        """, (user_id, total_amount, discount_amt, coupon_used, address))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

def add_order_items(order_id, items):
    """items: list of dicts with book_id, quantity, price_at_purchase"""
    conn = get_conn()
    try:
        cur = conn.cursor()
        for item in items:
            cur.execute("""
                INSERT INTO OrderItems (order_id, book_id, quantity, price_at_purchase)
                VALUES (%s,%s,%s,%s)
            """, (order_id, item['book_id'], item['quantity'], item['price_at_purchase']))
            decrement_stock(item['book_id'], item['quantity'])
        conn.commit()
    finally:
        conn.close()

def get_order_history(user_id):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT o.order_id, o.total_amount, o.discount_amt, o.coupon_used,
                   o.status, o.address, o.created_at
            FROM Orders o
            WHERE o.user_id=%s
            ORDER BY o.created_at DESC
        """, (user_id,))
        orders = _fetchall_dict(cur)
        for order in orders:
            cur.execute("""
                SELECT oi.quantity, oi.price_at_purchase,
                       b.title, b.cover_url, a.name AS author
                FROM OrderItems oi
                JOIN Books b ON oi.book_id=b.book_id
                JOIN Authors a ON b.author_id=a.author_id
                WHERE oi.order_id=%s
            """, (order['order_id'],))
            order['items'] = _fetchall_dict(cur)
        return orders
    finally:
        conn.close()

def get_all_orders_admin(limit=200):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT o.order_id, u.name AS customer_name, u.email,
                   o.total_amount, o.discount_amt, o.coupon_used,
                   o.status, o.address, o.created_at, o.updated_at
            FROM Orders o
            JOIN Users u ON o.user_id=u.user_id
            ORDER BY o.created_at DESC
            LIMIT %s
        """, (limit,))
        orders = _fetchall_dict(cur)
        for order in orders:
            cur.execute("""
                SELECT oi.quantity, oi.price_at_purchase, b.title
                FROM OrderItems oi
                JOIN Books b ON oi.book_id=b.book_id
                WHERE oi.order_id=%s
            """, (order['order_id'],))
            order['items'] = _fetchall_dict(cur)
        return orders
    finally:
        conn.close()

def update_order_status(order_id, status):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE Orders SET status=%s WHERE order_id=%s", (status, order_id))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
#  COUPONS
# ══════════════════════════════════════════════════════════════

def validate_coupon(code):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM Coupons
            WHERE code=%s AND is_active=1
              AND (expires_at IS NULL OR expires_at > NOW())
              AND used_count < max_uses
        """, (code,))
        return _fetchone_dict(cur)
    finally:
        conn.close()

def increment_coupon_usage(code):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE Coupons SET used_count=used_count+1 WHERE code=%s", (code,))
        conn.commit()
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
#  SEARCH LOGS
# ══════════════════════════════════════════════════════════════

def log_search(user_id, query_text, search_mode, results_returned):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO SearchLogs (user_id, query_text, search_mode, results_returned)
            VALUES (%s,%s,%s,%s)
        """, (user_id, query_text, search_mode, results_returned))
        conn.commit()
    except Exception as e:
        logger.warning(f"Failed to log search: {e}")
    finally:
        conn.close()

def get_search_logs(limit=100):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT sl.log_id, u.name AS user_name, sl.query_text,
                   sl.search_mode, sl.results_returned, sl.timestamp
            FROM SearchLogs sl
            LEFT JOIN Users u ON sl.user_id=u.user_id
            ORDER BY sl.timestamp DESC
            LIMIT %s
        """, (limit,))
        return _fetchall_dict(cur)
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
#  ADMIN STATS
# ══════════════════════════════════════════════════════════════

def get_admin_stats():
    conn = get_conn()
    try:
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM Books WHERE is_active=1")
        total_books = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM Orders")
        total_orders = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM Users WHERE is_admin=0")
        total_users = cur.fetchone()[0]

        cur.execute("""
            SELECT COALESCE(SUM(total_amount), 0)
            FROM Orders
            WHERE status != 'Cancelled'
              AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """)
        weekly_revenue = float(cur.fetchone()[0])

        cur.execute("""
            SELECT COALESCE(SUM(total_amount), 0) FROM Orders WHERE status != 'Cancelled'
        """)
        total_revenue = float(cur.fetchone()[0])

        cur.execute(f"SELECT COUNT(*) FROM Books WHERE stock <= {Config.LOW_STOCK_THRESHOLD} AND is_active=1")
        low_stock_count = cur.fetchone()[0]

        # weekly revenue by day (last 7 days)
        cur.execute("""
            SELECT DATE(created_at) AS day, COALESCE(SUM(total_amount),0) AS revenue
            FROM Orders
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) AND status != 'Cancelled'
            GROUP BY DATE(created_at)
            ORDER BY day
        """)
        weekly_chart = _fetchall_dict(cur)

        # top 5 selling books
        cur.execute("""
            SELECT b.title, SUM(oi.quantity) AS units_sold
            FROM OrderItems oi
            JOIN Books b ON oi.book_id=b.book_id
            GROUP BY oi.book_id
            ORDER BY units_sold DESC
            LIMIT 5
        """)
        top_books = _fetchall_dict(cur)

        return {
            'total_books':    total_books,
            'total_orders':   total_orders,
            'total_users':    total_users,
            'weekly_revenue': weekly_revenue,
            'total_revenue':  total_revenue,
            'low_stock_count': low_stock_count,
            'weekly_chart':   weekly_chart,
            'top_books':      top_books,
        }
    finally:
        conn.close()
