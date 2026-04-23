"""
seed_books.py — One-time setup script for Shelf Bookstore.

Run this AFTER:
  1. Creating the MySQL database:  mysql -u root -p < schema.sql
  2. Installing requirements:      pip install -r requirements.txt

What this script does:
  - Verifies the DB connection and checks that books are loaded.
  - Generates sentence embeddings for every book synopsis using
    the HuggingFace all-MiniLM-L6-v2 model.
  - Saves each embedding to the Embeddings table in MySQL.
  - Builds the FAISS index and saves it to disk.

Usage:
  python seed_books.py
"""

import json
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def check_db():
    """Verify DB connection and that books have been inserted."""
    logger.info("Checking database connection...")
    try:
        import mysql.connector
        from config import Config
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset='utf8mb4'
        )
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM Books WHERE is_active=1")
        count = cur.fetchone()[0]
        conn.close()
        logger.info(f"Database OK — {count} active books found.")
        return count
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        logger.error("Make sure MySQL is running and you ran: mysql -u root -p < schema.sql")
        sys.exit(1)


def generate_embeddings():
    """Generate and store embeddings for all books without one."""
    import models

    logger.info("Loading book synopses from database...")
    rows = models.get_all_synopses_for_embedding()   # [(book_id, synopsis), ...]
    if not rows:
        logger.error("No books found. Run schema.sql first.")
        sys.exit(1)

    logger.info(f"Found {len(rows)} books to embed.")

    # Check which books already have embeddings
    existing = {r[0] for r in models.get_all_embeddings()}
    to_embed = [(bid, syn) for bid, syn in rows if bid not in existing]

    if not to_embed:
        logger.info("All books already have embeddings. Nothing to do.")
        return

    logger.info(f"{len(to_embed)} books need embeddings. Loading model...")

    from sentence_transformers import SentenceTransformer
    from config import Config

    model = SentenceTransformer(Config.EMBEDDING_MODEL)
    logger.info("Model loaded. Generating embeddings (batch size=16)...")

    book_ids = [r[0] for r in to_embed]
    synopses = [r[1] for r in to_embed]

    import numpy as np
    vectors = model.encode(
        synopses,
        convert_to_numpy=True,
        normalize_embeddings=True,
        batch_size=16,
        show_progress_bar=True
    ).astype(np.float32)

    logger.info("Saving embeddings to database...")
    saved = 0
    for book_id, vec in zip(book_ids, vectors):
        try:
            models.save_embedding(book_id, json.dumps(vec.tolist()))
            saved += 1
        except Exception as e:
            logger.warning(f"Failed to save embedding for book_id={book_id}: {e}")

    logger.info(f"Saved {saved}/{len(book_ids)} embeddings to DB.")


def build_faiss_index():
    """Build the FAISS index from all stored embeddings."""
    logger.info("Building FAISS index...")
    try:
        import embeddings as emb
        emb.rebuild_index()
        logger.info("FAISS index built and saved to disk successfully.")
    except Exception as e:
        logger.error(f"Failed to build FAISS index: {e}")
        sys.exit(1)


def verify_search():
    """Run a quick test search to confirm everything works."""
    logger.info("Running test semantic search: 'a boy who discovers he can do magic'")
    try:
        import embeddings as emb
        emb.load_index()
        results = emb.semantic_search("a boy who discovers he can do magic", top_k=5)
        if results:
            import models
            books = models.get_books_by_ids([r['book_id'] for r in results])
            logger.info("Top results:")
            for book, res in zip(books, results):
                logger.info(f"  [{res['score']:.3f}] {book['title']} — {book['author']}")
        else:
            logger.warning("No results returned. Check similarity threshold in config.py.")
    except Exception as e:
        logger.error(f"Test search failed: {e}")


def print_summary():
    """Print a summary of what was seeded."""
    import models
    try:
        stats = models.get_admin_stats()
        print("\n" + "═" * 55)
        print("  SHELF BOOKSTORE — SEED COMPLETE")
        print("═" * 55)
        print(f"  📚 Total Books   : {stats['total_books']}")
        print(f"  👤 Total Users   : {stats['total_users']}")
        print(f"  🛒 Total Orders  : {stats['total_orders']}")
        print(f"  📉 Low Stock     : {stats['low_stock_count']} books")
        print("═" * 55)
        print("  Admin Login:")
        print("    Email   : admin@shelf.com")
        print("    Password: admin123")
        print("─" * 55)
        print("  Demo User Login:")
        print("    Email   : aryan@example.com")
        print("    Password: password123")
        print("─" * 55)
        print("  Available Coupon Codes:")
        print("    SHELF10   → 10% off (min ₹199)")
        print("    SHELF20   → 20% off (min ₹499)")
        print("    WELCOME15 → 15% off (no minimum)")
        print("    INDIA25   → 25% off (min ₹999)")
        print("    READ50    → 50% off (min ₹1999)")
        print("─" * 55)
        print("  Start the app: python app.py")
        print("  Open browser : http://localhost:5000")
        print("═" * 55 + "\n")
    except Exception as e:
        logger.error(f"Could not print summary: {e}")


if __name__ == '__main__':
    print("\n" + "═" * 55)
    print("  SHELF BOOKSTORE — SEEDING & EMBEDDING")
    print("═" * 55 + "\n")

    # Step 1: Verify DB
    book_count = check_db()
    if book_count == 0:
        logger.error("No books in DB. Make sure you ran schema.sql first.")
        sys.exit(1)

    # Step 2: Generate embeddings for any books missing them
    generate_embeddings()

    # Step 3: Build FAISS index
    build_faiss_index()

    # Step 4: Quick search test
    verify_search()

    # Step 5: Summary
    print_summary()
