# 📚 Shelf — Smart Bookstore with Semantic Search

An AI-powered online bookstore that lets users find books by describing what they
feel like reading in plain English — not just by title or keyword.

---

## Tech Stack

| Layer      | Technology                      |
|------------|---------------------------------|
| Frontend   | HTML, CSS, Vanilla JS           |
| Backend    | Flask (Python)                  |
| Database   | MySQL                           |
| NLP Model  | `all-MiniLM-L6-v2` (HuggingFace) |
| Vector DB  | FAISS (CPU, local)              |
| Auth       | Flask-JWT-Extended (Bearer)     |

---

## Setup Instructions

### 1. Clone / Download the Project

```bash
cd shelf_bookstore
```

### 2. Create a Python Virtual Environment

```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Mac/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `torch` and `sentence-transformers` are ~1.5 GB. The HuggingFace model
> (`all-MiniLM-L6-v2`, ~80 MB) downloads automatically on first run.

### 4. Set Up MySQL Database

Make sure MySQL is running, then:

```bash
mysql -u root -p < schema.sql
```

This creates the `shelf_bookstore` database, all tables, and inserts:
- 20 authors
- 50 books (with Indian pricing in ₹)
- 12 categories
- 6 demo users (including admin)
- Sample orders, reviews, search logs and coupons

### 5. Configure Database Password

Open `config.py` and update:

```python
DB_PASSWORD = 'your_mysql_password'   # ← change this to your MySQL root password
```

Alternatively, create a `.env` file:

```
DB_PASSWORD=your_mysql_password
JWT_SECRET_KEY=your-random-secret-key
```

### 6. Generate Embeddings & Build FAISS Index

```bash
python seed_books.py
```

This will:
- Download the NLP model on first run (~80 MB)
- Generate 384-dim embeddings for all 50 book synopses
- Save embeddings to MySQL
- Build the FAISS index and save it as `faiss_index.bin`
- Run a test search to confirm everything works

### 7. Start the App

```bash
python app.py
```

Open your browser at: **http://localhost:5000**

---

## Default Login Credentials

| Role  | Email                | Password    |
|-------|----------------------|-------------|
| Admin | admin@shelf.com      | admin123    |
| User  | aryan@example.com    | password123 |
| User  | priya@example.com    | password123 |

---

## Coupon Codes (for testing)

| Code       | Discount | Minimum Order |
|------------|----------|---------------|
| WELCOME15  | 15% off  | No minimum    |
| SHELF10    | 10% off  | ₹199          |
| SHELF20    | 20% off  | ₹499          |
| INDIA25    | 25% off  | ₹999          |
| READ50     | 50% off  | ₹1,999        |

---

## API Reference

### Auth
| Method | Endpoint                | Auth     | Description         |
|--------|-------------------------|----------|---------------------|
| POST   | `/api/auth/register`    | None     | Register new user   |
| POST   | `/api/auth/login`       | None     | Login, get JWT      |
| GET    | `/api/auth/me`          | Required | Get current user    |
| PUT    | `/api/auth/preferences` | Required | Update preferences  |

### Books & Search
| Method | Endpoint                          | Auth     | Description             |
|--------|-----------------------------------|----------|-------------------------|
| GET    | `/api/books`                      | None     | List all books          |
| GET    | `/api/books/<id>`                 | None     | Get single book detail  |
| GET    | `/api/books/categories`           | None     | List all categories     |
| GET    | `/api/search?q=<query>&mode=semantic` | None | Semantic/keyword search |
| GET    | `/api/search/similar/<book_id>`   | None     | More Like This          |

### Cart
| Method | Endpoint                      | Auth     | Description     |
|--------|-------------------------------|----------|-----------------|
| GET    | `/api/cart`                   | Required | View cart       |
| POST   | `/api/cart/add`               | Required | Add item        |
| PUT    | `/api/cart/update`            | Required | Update quantity |
| DELETE | `/api/cart/remove/<book_id>`  | Required | Remove item     |

### Orders
| Method | Endpoint              | Auth     | Description        |
|--------|-----------------------|----------|--------------------|
| POST   | `/api/orders/place`   | Required | Place order        |
| GET    | `/api/orders/history` | Required | Order history      |

### Reviews & Wishlist
| Method | Endpoint                          | Auth     | Description          |
|--------|-----------------------------------|----------|----------------------|
| GET    | `/api/reviews/<book_id>`          | None     | Get book reviews     |
| POST   | `/api/reviews/add`                | Required | Submit a review      |
| GET    | `/api/wishlist`                   | Required | View wishlist        |
| POST   | `/api/wishlist/add`               | Required | Add to wishlist      |
| DELETE | `/api/wishlist/remove/<book_id>`  | Required | Remove from wishlist |

### Coupons
| Method | Endpoint              | Auth     | Description       |
|--------|-----------------------|----------|-------------------|
| POST   | `/api/coupons/apply`  | Required | Validate coupon   |

### Admin (admin JWT required)
| Method | Endpoint                              | Description              |
|--------|---------------------------------------|--------------------------|
| GET    | `/api/admin/stats`                    | Dashboard stats          |
| GET    | `/api/admin/books`                    | All books list           |
| POST   | `/api/admin/books/add`                | Add new book             |
| PUT    | `/api/admin/books/edit/<id>`          | Edit book                |
| DELETE | `/api/admin/books/delete/<id>`        | Soft-delete book         |
| GET    | `/api/admin/orders`                   | All orders               |
| PUT    | `/api/admin/orders/update/<id>`       | Update order status      |
| GET    | `/api/admin/search-logs`              | Search query logs        |
| GET    | `/api/admin/low-stock`                | Low stock alerts         |
| POST   | `/api/admin/rebuild-index`            | Rebuild FAISS index      |

---

## Project Structure

```
shelf_bookstore/
├── app.py              ← Flask app + all routes
├── config.py           ← All configuration (DB, JWT, model paths)
├── models.py           ← MySQL query functions (no ORM)
├── embeddings.py       ← HuggingFace + FAISS semantic search engine
├── seed_books.py       ← One-time DB population + embedding generation
├── schema.sql          ← Full DB schema + 50 books seed data
├── requirements.txt    ← Python dependencies
├── faiss_index.bin     ← FAISS index (auto-generated by seed_books.py)
├── book_ids.npy        ← FAISS position → book_id map (auto-generated)
├── static/
│   ├── style.css       ← All CSS styles
│   └── app.js          ← All frontend JavaScript
└── templates/
    ├── index.html      ← Homepage (search + catalog)
    ├── book.html       ← Book detail page
    ├── auth.html       ← Login + Register
    ├── cart.html       ← Cart + Checkout + Order History
    └── admin.html      ← Admin Dashboard
```

---

## How Semantic Search Works

1. Every book synopsis is encoded into a **384-dimensional vector** by the
   `all-MiniLM-L6-v2` sentence transformer model.
2. Vectors are stored in MySQL (`Embeddings` table) and loaded into a
   **FAISS IndexFlatIP** (inner-product index, equivalent to cosine similarity
   on unit-normalised vectors).
3. When a user searches, their query is encoded with the same model.
4. **Cosine similarity** between query vector and all book vectors is computed
   instantly via FAISS.
5. Books above the similarity threshold (0.20 by default) are returned ranked
   by score.

This means a query like *"a boy who discovers magical powers at school"* will
surface Harry Potter even if neither "magic" nor "school" appears in the synopsis.

---

## Troubleshooting

**MySQL connection error:**
→ Check `DB_PASSWORD` in `config.py` matches your MySQL root password.

**Model download fails:**
→ Ensure internet access on first run. The model downloads from HuggingFace (~80 MB).

**`faiss` install fails on Windows:**
→ Use `pip install faiss-cpu` (not just `faiss`).

**Port 5000 already in use:**
→ Change the port in `app.py`: `app.run(port=5001)`

**Embeddings missing / search returns nothing:**
→ Re-run `python seed_books.py`
