import os

class Config:
    # ──────────────────────────────────────────────
    # MySQL Database Configuration
    # ──────────────────────────────────────────────
    DB_HOST     = os.getenv('DB_HOST',     'localhost')
    DB_USER     = os.getenv('DB_USER',     'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'your_mysql_password')   # ← change this
    DB_NAME     = os.getenv('DB_NAME',     'shelf_bookstore')
    DB_PORT     = int(os.getenv('DB_PORT', 3306))

    # ──────────────────────────────────────────────
    # JWT Authentication
    # ──────────────────────────────────────────────
    JWT_SECRET_KEY            = os.getenv('JWT_SECRET_KEY', 'shelf-jwt-super-secret-2024-change-me')
    JWT_ACCESS_TOKEN_EXPIRES  = 86400        # 24 hours in seconds

    # ──────────────────────────────────────────────
    # Flask Core
    # ──────────────────────────────────────────────
    SECRET_KEY = os.getenv('SECRET_KEY', 'flask-shelf-secret-key-2024')
    DEBUG      = os.getenv('DEBUG', 'True') == 'True'

    # ──────────────────────────────────────────────
    # HuggingFace NLP Model (runs fully on CPU)
    # Model: all-MiniLM-L6-v2  (~80 MB download on first run)
    # Produces 384-dimensional sentence embeddings
    # ──────────────────────────────────────────────
    EMBEDDING_MODEL   = 'all-MiniLM-L6-v2'
    EMBEDDING_DIM     = 384
    FAISS_INDEX_PATH  = os.getenv('FAISS_INDEX_PATH', 'faiss_index.bin')
    BOOK_IDS_PATH     = os.getenv('BOOK_IDS_PATH',    'book_ids.npy')

    # ──────────────────────────────────────────────
    # Search Behaviour
    # ──────────────────────────────────────────────
    SIMILARITY_THRESHOLD = 0.20   # minimum cosine similarity score to include a result
    MAX_SEARCH_RESULTS   = 20     # cap on results returned per query

    # ──────────────────────────────────────────────
    # Inventory
    # ──────────────────────────────────────────────
    LOW_STOCK_THRESHOLD = 10      # books with stock <= this trigger low-stock alert

    # ──────────────────────────────────────────────
    # Currency  (Indian Rupees)
    # ──────────────────────────────────────────────
    CURRENCY_SYMBOL = '₹'
    CURRENCY_CODE   = 'INR'

    # ──────────────────────────────────────────────
    # Cloudinary  (optional – for book cover uploads)
    # Leave blank to use local static/covers/ folder
    # ──────────────────────────────────────────────
    CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME', '')
    CLOUDINARY_API_KEY    = os.getenv('CLOUDINARY_API_KEY',    '')
    CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET', '')

    # ──────────────────────────────────────────────
    # CORS origins allowed to call the API
    # ──────────────────────────────────────────────
    CORS_ORIGINS = ['http://localhost:5000', 'http://127.0.0.1:5000']

    # ──────────────────────────────────────────────
    # Coupon Codes  (hardcoded for demo; move to DB in production)
    # ──────────────────────────────────────────────
    COUPON_CODES = {
        'SHELF10':  10,   # 10% off
        'SHELF20':  20,   # 20% off
        'WELCOME15': 15,  # 15% off for new users
        'INDIA25':  25,   # 25% off
        'READ50':   50,   # 50% off (special)
    }
