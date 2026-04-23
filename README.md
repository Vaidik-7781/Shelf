# 📚 Shelf — AI-Powered Smart Bookstore

> An intelligent online bookstore that lets you find books by describing what you *feel* like reading — not just by title or keyword.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0.3-black?style=flat-square&logo=flask)
![MySQL](https://img.shields.io/badge/MySQL-8.0-orange?style=flat-square&logo=mysql)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-CDN-38bdf8?style=flat-square&logo=tailwindcss)
![HuggingFace](https://img.shields.io/badge/HuggingFace-all--MiniLM--L6--v2-yellow?style=flat-square)
![FAISS](https://img.shields.io/badge/FAISS-Vector_Search-purple?style=flat-square)

---

## 🧠 What Makes This Different?

Traditional bookstores require you to know the **exact title or author**. Shelf uses **AI Semantic Search** — type anything you feel like reading and the AI finds the closest matching books by *meaning*.

**Example:** Type `"a dark story about a genius student who commits a crime and feels guilty"` → Gets **Crime and Punishment** by Dostoevsky

This works using a **HuggingFace sentence transformer model** that converts text into mathematical vectors and finds similarity using **FAISS (Facebook AI Similarity Search)**.

---

## ✨ Features

### 🔍 Search & Discovery
- **AI Semantic Search** — search by concept, emotion, plot — not keywords
- **Keyword Search** — classic title/author search with a toggle switch
- **Mood Filters** — Light & Funny, Dark & Thrilling, Romantic, Mind-Bending, Emotional
- **More Like This** — AI-powered similar books on every book page

### 📚 Books & Browsing
- 50 books across 20 authors with real cover images
- Full book detail pages — synopsis, ISBN, language, pages, published year
- Star ratings and review counts
- Stock availability badges

### 🛒 Shopping
- Add to cart, update quantity, remove items
- **5 discount coupon codes** at checkout
- Place orders with delivery address
- Free shipping on orders above ₹499
- Complete order history with status tracking

### 👤 User Accounts
- Register with favorite genres and preferred language
- Secure login with **JWT authentication**
- Write 1–5 star reviews on any book
- Personal wishlist

### 🔐 Admin Dashboard
- **Dashboard** — Live stats: total books, orders, weekly revenue (₹), low stock alerts
- **Inventory** — Add, edit, delete books (auto-generates AI embedding on add/edit)
- **Orders** — View all orders, update fulfilment status inline
- **Analytics** — Total revenue, avg order value, top 5 sellers chart
- **Search Logs** — See exactly what users are searching for
- **Rebuild AI Index** — Regenerate FAISS index after bulk changes

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | HTML, Tailwind CSS, Vanilla JS | UI — 5 pages |
| **Backend** | Python, Flask | REST API server |
| **Database** | MySQL 8.0 | All persistent data |
| **AI Model** | `all-MiniLM-L6-v2` (HuggingFace) | Sentence embeddings |
| **Vector Search** | FAISS (CPU) | Cosine similarity search |
| **Auth** | Flask-JWT-Extended | JWT token authentication |
| **Password** | bcrypt | One-way password hashing |
| **Fonts** | Newsreader + Manrope (Google Fonts) | Typography |
| **Styling** | Tailwind CSS via CDN | Utility-first CSS |

---

## 📁 Project Structure

```
Shelf/
├── Backend/
│   ├── app.py              ← Flask server — all 30+ API routes
│   ├── config.py           ← All configuration (DB, JWT, model, coupons)
│   ├── models.py           ← All MySQL query functions
│   ├── embeddings.py       ← HuggingFace + FAISS AI search engine
│   ├── seed_books.py       ← One-time setup: embeddings + FAISS index
│   ├── schema.sql          ← Full DB schema + 50 books seed data
│   ├── requirements.txt    ← Python dependencies
│   └── README.md           ← Backend setup guide
└── Frontend/
    ├── templates/
    │   ├── index.html      ← Homepage — search + catalog
    │   ├── book.html       ← Book detail + reviews + similar books
    │   ├── auth.html       ← Login + Register
    │   ├── cart.html       ← Cart + Checkout + Order History
    │   └── admin.html      ← Admin Dashboard (5 sections)
    └── static/
        ├── style.css       ← Global styles — all components
        └── app.js          ← Shared JS — API client, auth, cart, utilities
```

---

## 🚀 How to Run Locally

### Prerequisites
- Python 3.10+
- MySQL 8.0
- Git

### Step 1 — Clone the Repository
```bash
git clone https://github.com/Vaidik-7781/Shelf.git
cd Shelf
```

### Step 2 — Set Up MySQL Database
Open Command Prompt and run:
```bash
mysql -u root -p < Backend/schema.sql
```
This creates the database, all 11 tables, and seeds 50 books automatically.

### Step 3 — Configure Database Password
Open `Backend/config.py` and update:
```python
DB_PASSWORD = 'your_mysql_password'
```

### Step 4 — Update app.py Flask Path
Open `Backend/app.py` and change:
```python
# Find this line:
app = Flask(__name__)

# Change to:
app = Flask(__name__,
    template_folder='../Frontend/templates',
    static_folder='../Frontend/static'
)
```

### Step 5 — Create Virtual Environment
```bash
cd Backend
python -m venv venv

# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate
```

### Step 6 — Install Dependencies
```bash
pip install -r requirements.txt
```
> Note: torch and sentence-transformers are ~1.5GB. Allow 10–15 minutes.

### Step 7 — Generate AI Embeddings
```bash
python seed_books.py
```
This downloads the AI model (~80MB, first time only), generates embeddings for all 50 books, and builds the FAISS index.

### Step 8 — Start the Server
```bash
python app.py
```

### Step 9 — Open in Browser
```
http://localhost:5000
```

---

## 🔑 Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| **Admin** | admin@shelf.com | admin123 |
| **User** | aryan@example.com | password123 |
| **User** | priya@example.com | password123 |

---

## 🏷️ Coupon Codes

| Code | Discount | Minimum Order |
|------|----------|---------------|
| `WELCOME15` | 15% off | No minimum |
| `SHELF10` | 10% off | ₹199 |
| `SHELF20` | 20% off | ₹499 |
| `INDIA25` | 25% off | ₹999 |
| `READ50` | 50% off | ₹1,999 |

---

## 🧩 How the AI Search Works

```
User types: "a boy who discovers magical powers at a school for wizards"
                              ↓
         Query converted to 384-dimensional vector
         [0.12, -0.34, 0.87, 0.23, ... × 384]
                              ↓
         FAISS computes cosine similarity against
         all 50 book vectors stored in index
                              ↓
         Top matches returned ranked by similarity score
                              ↓
         Harry Potter appears at top — even without
         the words "Harry Potter" in the query
```

The model `all-MiniLM-L6-v2` learned from billions of text examples that concepts like *magic*, *school*, *wizards*, and *Harry Potter* are semantically related — so it finds them even without exact word matches.

---

## 🗄️ Database Schema

11 tables: `Users` · `Books` · `Authors` · `Categories` · `BookCategories` · `Embeddings` · `Orders` · `OrderItems` · `Reviews` · `Cart` · `Wishlist` · `SearchLogs` · `Coupons`

---

## 📸 Pages

| Page | Route | Description |
|------|-------|-------------|
| Homepage | `/` | AI search + mood filters + book catalog |
| Book Detail | `/book/<id>` | Synopsis + reviews + similar books |
| Auth | `/auth` | Login + Register |
| Cart | `/cart` | Cart + checkout + order history |
| Admin | `/admin` | Full admin dashboard |

---

## 👨‍💻 Developer

**Vaidik Gupta** — [@Vaidik-7781](https://github.com/Vaidik-7781)

---

*Built as a college project demonstrating full-stack development with AI/ML integration.*
