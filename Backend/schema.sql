-- ============================================================
--  Shelf Bookstore — Full Database Schema + Seed Data
--  Database: shelf_bookstore
--  All prices in Indian Rupees (INR)
-- ============================================================

CREATE DATABASE IF NOT EXISTS shelf_bookstore
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE shelf_bookstore;

-- ============================================================
--  DROP TABLES (clean re-run)
-- ============================================================
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS SearchLogs;
DROP TABLE IF EXISTS Cart;
DROP TABLE IF EXISTS Wishlist;
DROP TABLE IF EXISTS Reviews;
DROP TABLE IF EXISTS OrderItems;
DROP TABLE IF EXISTS Orders;
DROP TABLE IF EXISTS Coupons;
DROP TABLE IF EXISTS BookCategories;
DROP TABLE IF EXISTS Embeddings;
DROP TABLE IF EXISTS Books;
DROP TABLE IF EXISTS Categories;
DROP TABLE IF EXISTS Authors;
DROP TABLE IF EXISTS Users;
SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
--  USERS
-- ============================================================
CREATE TABLE Users (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(120)  NOT NULL,
    email         VARCHAR(180)  NOT NULL UNIQUE,
    password_hash VARCHAR(256)  NOT NULL,
    preferences   JSON,                          -- {"genres":["Fiction"],"language":"English"}
    is_admin      TINYINT(1)    DEFAULT 0,
    created_at    DATETIME      DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================================
--  AUTHORS
-- ============================================================
CREATE TABLE Authors (
    author_id   INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(150) NOT NULL,
    bio         TEXT,
    nationality VARCHAR(80),
    birth_year  YEAR
) ENGINE=InnoDB;

-- ============================================================
--  CATEGORIES
-- ============================================================
CREATE TABLE Categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB;

-- ============================================================
--  BOOKS
-- ============================================================
CREATE TABLE Books (
    book_id        INT AUTO_INCREMENT PRIMARY KEY,
    title          VARCHAR(250)   NOT NULL,
    author_id      INT            NOT NULL,
    synopsis       TEXT           NOT NULL,
    price          DECIMAL(10,2)  NOT NULL,          -- INR
    stock          INT            DEFAULT 0,
    cover_url      VARCHAR(500),
    language       VARCHAR(60)    DEFAULT 'English',
    isbn           VARCHAR(20)    UNIQUE,
    published_year YEAR,
    pages          INT,
    avg_rating     DECIMAL(3,2)   DEFAULT 0.00,
    rating_count   INT            DEFAULT 0,
    mood_tags      VARCHAR(300),                      -- comma-separated mood labels
    is_active      TINYINT(1)     DEFAULT 1,
    created_at     DATETIME       DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (author_id) REFERENCES Authors(author_id)
) ENGINE=InnoDB;

-- ============================================================
--  BOOK CATEGORIES  (many-to-many)
-- ============================================================
CREATE TABLE BookCategories (
    book_id     INT NOT NULL,
    category_id INT NOT NULL,
    PRIMARY KEY (book_id, category_id),
    FOREIGN KEY (book_id)     REFERENCES Books(book_id)      ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES Categories(category_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
--  EMBEDDINGS  (stores 384-dim vector as JSON blob)
-- ============================================================
CREATE TABLE Embeddings (
    embedding_id INT AUTO_INCREMENT PRIMARY KEY,
    book_id      INT  NOT NULL UNIQUE,
    vector_blob  LONGTEXT,                             -- JSON array of 384 floats
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (book_id) REFERENCES Books(book_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
--  ORDERS
-- ============================================================
CREATE TABLE Orders (
    order_id      INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT           NOT NULL,
    total_amount  DECIMAL(10,2) NOT NULL,
    discount_amt  DECIMAL(10,2) DEFAULT 0.00,
    coupon_used   VARCHAR(30),
    status        ENUM('Pending','Processing','Shipped','Delivered','Cancelled') DEFAULT 'Pending',
    address       TEXT,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
) ENGINE=InnoDB;

-- ============================================================
--  ORDER ITEMS
-- ============================================================
CREATE TABLE OrderItems (
    item_id           INT AUTO_INCREMENT PRIMARY KEY,
    order_id          INT           NOT NULL,
    book_id           INT           NOT NULL,
    quantity          INT           NOT NULL DEFAULT 1,
    price_at_purchase DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES Orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (book_id)  REFERENCES Books(book_id)
) ENGINE=InnoDB;

-- ============================================================
--  REVIEWS
-- ============================================================
CREATE TABLE Reviews (
    review_id   INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT  NOT NULL,
    book_id     INT  NOT NULL,
    rating      TINYINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review_text TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_review (user_id, book_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (book_id) REFERENCES Books(book_id)  ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
--  CART
-- ============================================================
CREATE TABLE Cart (
    cart_id    INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT NOT NULL,
    book_id    INT NOT NULL,
    quantity   INT NOT NULL DEFAULT 1,
    added_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_cart_item (user_id, book_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (book_id) REFERENCES Books(book_id)  ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
--  WISHLIST
-- ============================================================
CREATE TABLE Wishlist (
    wishlist_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    book_id     INT NOT NULL,
    added_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_wish (user_id, book_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (book_id) REFERENCES Books(book_id)  ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
--  SEARCH LOGS
-- ============================================================
CREATE TABLE SearchLogs (
    log_id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id          INT,                        -- nullable for guest searches
    query_text       VARCHAR(500) NOT NULL,
    search_mode      ENUM('semantic','keyword') DEFAULT 'semantic',
    results_returned INT DEFAULT 0,
    timestamp        DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ============================================================
--  COUPONS
-- ============================================================
CREATE TABLE Coupons (
    coupon_id       INT AUTO_INCREMENT PRIMARY KEY,
    code            VARCHAR(30)   NOT NULL UNIQUE,
    discount_pct    TINYINT       NOT NULL,       -- percentage
    min_order_amt   DECIMAL(10,2) DEFAULT 0.00,
    max_uses        INT           DEFAULT 1000,
    used_count      INT           DEFAULT 0,
    is_active       TINYINT(1)    DEFAULT 1,
    expires_at      DATETIME
) ENGINE=InnoDB;

-- ============================================================
--  ██  SEED DATA  ██
-- ============================================================

-- ── AUTHORS ──────────────────────────────────────────────────
INSERT INTO Authors (name, bio, nationality, birth_year) VALUES
('Chetan Bhagat',         'Indian author and columnist known for his simple storytelling that connects with urban youth.',                            'Indian',     1974),
('Amish Tripathi',        'Indian author known for mythological fiction that reimagines Hindu gods as humans.',                                        'Indian',     1974),
('Ruskin Bond',           'Beloved Indian author who writes about life in the Himalayan foothills with warmth and simplicity.',                        'Indian',     1934),
('Arundhati Roy',         'Indian author and activist; winner of the Booker Prize for The God of Small Things.',                                       'Indian',     1961),
('R.K. Narayan',          'Pioneer of Indian English literature; creator of the fictional town Malgudi.',                                             'Indian',     1906),
('Vikram Seth',           'Indian author known for his epic novel A Suitable Boy; also a poet and travel writer.',                                     'Indian',     1952),
('Sudha Murty',           'Indian author, philanthropist and Chairperson of Infosys Foundation; writes heartwarming moral stories.',                   'Indian',     1950),
('Paulo Coelho',          'Brazilian author best known for The Alchemist; his works focus on dreams, destiny and spirituality.',                       'Brazilian',  1947),
('Dan Brown',             'American author of fast-paced thriller novels with cryptographic and religious conspiracy themes.',                          'American',   1964),
('George Orwell',         'English novelist and essayist known for political allegories and dystopian fiction.',                                       'British',    1903),
('J.K. Rowling',          'British author who created the Harry Potter universe; one of the best-selling authors in history.',                         'British',    1965),
('Harper Lee',            'American novelist whose only major work To Kill a Mockingbird won the Pulitzer Prize.',                                     'American',   1926),
('Fyodor Dostoevsky',     'Russian novelist and philosopher whose works explore psychology, morality and the human condition.',                        'Russian',    1821),
('Gabriel Garcia Marquez','Colombian author and Nobel Prize winner; pioneer of magical realism in literature.',                                        'Colombian',  1927),
('Yuval Noah Harari',     'Israeli historian and professor at Hebrew University; author of macro-history bestsellers.',                                'Israeli',    1976),
('Robert C. Martin',      'American software engineer known as "Uncle Bob"; author of foundational books on clean software development.',             'American',   1952),
('Eric Matthes',          'American educator and Python enthusiast; writes beginner-friendly programming textbooks.',                                  'American',   1975),
('Devdutt Pattanaik',     'Indian author and mythologist who reinterprets Indian mythology for modern readers.',                                       'Indian',     1970),
('Ashwin Sanghi',         'Indian author known for fast-paced historical thrillers that mix Indian history with modern mystery.',                      'Indian',     1969),
('Preeti Shenoy',         'Indian author known for contemporary fiction dealing with everyday life and relationships in India.',                       'Indian',     1973);

-- ── CATEGORIES ───────────────────────────────────────────────
INSERT INTO Categories (name) VALUES
('Indian Literature'),
('Fiction'),
('Mystery & Thriller'),
('Fantasy & Mythology'),
('Classic Literature'),
('Self-Help & Inspiration'),
('Biography & Memoir'),
('History & Science'),
('Technology & Programming'),
('Romance'),
('Philosophy'),
('Science Fiction');

-- ── USERS (including admin) ───────────────────────────────────
-- Passwords are bcrypt hashes of 'password123' for demo users
-- Admin password hash for 'admin@shelf.com' is for 'admin123'
INSERT INTO Users (name, email, password_hash, preferences, is_admin) VALUES
('Admin Shelf',    'admin@shelf.com',    '$2b$12$LQv3c1yqBwEHXp59jPC5pOwY7SHX9EPlbAEMipmCEjq9u0c5UUF0e', '{"genres":["All"],"language":"English"}', 1),
('Aryan Sharma',   'aryan@example.com',  '$2b$12$LQv3c1yqBwEHXp59jPC5pOwY7SHX9EPlbAEMipmCEjq9u0c5UUF0e', '{"genres":["Fiction","Thriller"],"language":"English"}', 0),
('Priya Nair',     'priya@example.com',  '$2b$12$LQv3c1yqBwEHXp59jPC5pOwY7SHX9EPlbAEMipmCEjq9u0c5UUF0e', '{"genres":["Indian Literature","Romance"],"language":"English"}', 0),
('Rohan Verma',    'rohan@example.com',  '$2b$12$LQv3c1yqBwEHXp59jPC5pOwY7SHX9EPlbAEMipmCEjq9u0c5UUF0e', '{"genres":["Technology","Science Fiction"],"language":"English"}', 0),
('Sneha Kulkarni', 'sneha@example.com',  '$2b$12$LQv3c1yqBwEHXp59jPC5pOwY7SHX9EPlbAEMipmCEjq9u0c5UUF0e', '{"genres":["Self-Help","Philosophy"],"language":"English"}', 0),
('Kiran Mehta',    'kiran@example.com',  '$2b$12$LQv3c1yqBwEHXp59jPC5pOwY7SHX9EPlbAEMipmCEjq9u0c5UUF0e', '{"genres":["Mythology","Indian Literature"],"language":"English"}', 0);

-- ── COUPONS ──────────────────────────────────────────────────
INSERT INTO Coupons (code, discount_pct, min_order_amt, max_uses, expires_at) VALUES
('SHELF10',   10,  199.00, 9999, '2025-12-31 23:59:59'),
('SHELF20',   20,  499.00, 5000, '2025-12-31 23:59:59'),
('WELCOME15', 15,    0.00, 9999, '2025-12-31 23:59:59'),
('INDIA25',   25,  999.00, 2000, '2025-06-30 23:59:59'),
('READ50',    50, 1999.00,  500, '2025-03-31 23:59:59');

-- ── BOOKS ────────────────────────────────────────────────────
INSERT INTO Books (title, author_id, synopsis, price, stock, cover_url, language, isbn, published_year, pages, avg_rating, rating_count, mood_tags) VALUES

-- Chetan Bhagat (author_id=1)
('Five Point Someone',
 1,
 'Three friends at IIT Delhi struggle with the pressure of India''s most elite engineering college, finding love, friendship and rebellion along the way. A hilarious yet poignant look at the dark side of India''s obsession with grades and success.',
 299.00, 85, 'https://images-na.ssl-images-amazon.com/images/I/71oO1PfAM7L.jpg',
 'English', '9788129104595', 2004, 265, 3.90, 1420, 'Light & Funny,Emotional,Thought-Provoking'),

('2 States',
 1,
 'The story of Krish and Ananya — two people from different Indian states trying to convince each other''s stubborn families to approve their marriage. A funny, warm and deeply relatable tale of love across cultural divides in India.',
 299.00, 92, 'https://images-na.ssl-images-amazon.com/images/I/81wSEGVmWQL.jpg',
 'English', '9788129115300', 2009, 270, 4.00, 1860, 'Light & Funny,Romantic,Emotional'),

('Revolution 2020',
 1,
 'Set in Varanasi, this novel follows Gopal, Raghav and Aarti in a triangle of love, ambition and corruption. Gopal joins the corrupt coaching industry while Raghav fights it through journalism — and Aarti stands in between.',
 299.00, 67, 'https://images-na.ssl-images-amazon.com/images/I/71BHCY1XQYL.jpg',
 'English', '9788129117946', 2011, 296, 3.70, 980, 'Thought-Provoking,Emotional,Dark & Thrilling'),

('Half Girlfriend',
 1,
 'Madhav Jha from Bihar meets the sophisticated Riya Somani at St. Stephen''s College, Delhi. She agrees to be his "half-girlfriend" — not quite his girlfriend, but something more. A story about aspiration, heartbreak and finding yourself.',
 299.00, 54, 'https://images-na.ssl-images-amazon.com/images/I/71q8HNjP1XL.jpg',
 'English', '9788129135728', 2014, 280, 3.50, 1120, 'Romantic,Emotional,Light & Funny'),

-- Amish Tripathi (author_id=2)
('The Immortals of Meluha',
 2,
 'In the land of Meluha, a near-perfect empire built by the great god-king Ram, lives a tribe of immigrants called Shiva. He is rough and uncouth, but destined to be the saviour of the Meluhans according to their ancient prophecy. An extraordinary retelling of the Shiva mythology.',
 350.00, 110, 'https://images-na.ssl-images-amazon.com/images/I/71GXXmpXQAL.jpg',
 'English', '9789380658742', 2010, 412, 4.20, 2340, 'Mind-Bending,Dark & Thrilling,Thought-Provoking'),

('The Secret of the Nagas',
 2,
 'The second book in the Shiva Trilogy continues Shiva''s quest to find the Nagas — a feared and despised tribe — and uncover the dark secret that surrounds them. Breathtaking battles, divine politics and moral dilemmas make this a gripping continuation.',
 350.00, 95, 'https://images-na.ssl-images-amazon.com/images/I/71Q8yBVxVcL.jpg',
 'English', '9789381626085', 2011, 384, 4.30, 1980, 'Mind-Bending,Dark & Thrilling'),

('The Oath of the Vayuputras',
 2,
 'The epic conclusion of the Shiva Trilogy. The Neelkanth finally discovers the true evil that is destroying the land of Meluha and must make an agonising choice — one that will change the fate of an entire civilisation.',
 350.00, 78, 'https://images-na.ssl-images-amazon.com/images/I/71VhWOuVBqL.jpg',
 'English', '9789381626979', 2013, 508, 4.10, 1750, 'Mind-Bending,Dark & Thrilling,Emotional'),

('Scion of Ikshvaku',
 2,
 'The first book of the Ram Chandra Series reimagines the Ramayana. Ram is scorned by his own people for a battle he did not lose — yet his dharma and steadfast love for Sita make him a man who transcends failure. A powerful retelling of an ancient epic.',
 399.00, 88, 'https://images-na.ssl-images-amazon.com/images/I/81tVZM1EoJL.jpg',
 'English', '9789386050748', 2015, 360, 4.00, 1430, 'Mind-Bending,Emotional,Thought-Provoking'),

-- Ruskin Bond (author_id=3)
('The Blue Umbrella',
 3,
 'In a village in the Himalayan foothills, a young girl trades her prized leopard claw necklace for a beautiful blue umbrella. Soon the umbrella becomes the envy of the entire village, sparking jealousy, regret and ultimately, redemption. A timeless and gentle tale.',
 199.00, 120, 'https://images-na.ssl-images-amazon.com/images/I/71MFCy-2H1L.jpg',
 'English', '9780143330226', 1980, 64, 4.30, 980, 'Light & Funny,Emotional'),

('The Room on the Roof',
 3,
 'Sixteen-year-old Rusty lives with his strict English guardian in Dehradun. Captivated by the vibrant life of an Indian family, he runs away to live in their world — discovering freedom, poverty, love and belonging in ways he never expected.',
 249.00, 98, 'https://images-na.ssl-images-amazon.com/images/I/61pJtHbGF0L.jpg',
 'English', '9780140302479', 1956, 175, 4.40, 1240, 'Emotional,Light & Funny'),

('The Night Train at Deoli',
 3,
 'A stunning collection of short stories set in the hills of India — stories of love that lasted a moment, ghosts that never left, hill stations full of melancholy, and ordinary people with extraordinary inner lives. Ruskin Bond at his most lyrical.',
 249.00, 75, 'https://images-na.ssl-images-amazon.com/images/I/51sERN8wXuL.jpg',
 'English', '9780143031963', 1988, 191, 4.50, 1560, 'Emotional,Light & Funny'),

('Rusty the Boy from the Hills',
 3,
 'Rusty runs away from his strict guardian and finds a new life among the people of the hills — their warmth, their festivals and their stories. A semi-autobiographical coming-of-age tale full of nostalgia and wonder.',
 229.00, 60, 'https://images-na.ssl-images-amazon.com/images/I/51g1-P9mADL.jpg',
 'English', '9780143331162', 2001, 120, 4.20, 720, 'Emotional,Light & Funny'),

-- Arundhati Roy (author_id=4)
('The God of Small Things',
 4,
 'Set in Kerala, this Booker Prize-winning novel tells the story of fraternal twins Rahel and Estha and the events of 1969 that haunt them decades later. A devastating exploration of forbidden love, caste, family secrets and the politics of small things.',
 399.00, 65, 'https://images-na.ssl-images-amazon.com/images/I/71c3mFZvunL.jpg',
 'English', '9780006550686', 1997, 321, 4.30, 2100, 'Dark & Thrilling,Thought-Provoking,Emotional'),

('The Ministry of Utmost Happiness',
 4,
 'An intricate tapestry of lives: a hijra who makes a home in a graveyard, a young woman who chooses a dangerous cause, a Kashmiri separatist, and an abandoned infant. Roy weaves them into a portrait of a nation in chaos, violence and tenderness.',
 449.00, 42, 'https://images-na.ssl-images-amazon.com/images/I/71n7xTRzVoL.jpg',
 'English', '9780241303979', 2017, 449, 3.80, 780, 'Dark & Thrilling,Thought-Provoking'),

-- R.K. Narayan (author_id=5)
('The Guide',
 5,
 'Raju the railway guide becomes the lover of a dancer, eventually transforming into a spiritual guide and self-proclaimed holy man. A brilliant, funny and profound novel about identity, self-deception and unexpected redemption.',
 250.00, 88, 'https://images-na.ssl-images-amazon.com/images/I/51YRVY4d1NL.jpg',
 'English', '9780143065098', 1958, 220, 4.20, 1340, 'Thought-Provoking,Light & Funny,Emotional'),

('Malgudi Days',
 5,
 'A beloved collection of short stories set in the fictional south Indian town of Malgudi — stories of ordinary people, their quirks, dreams and small tragedies. R.K. Narayan captures India with unmatched gentle humour and precise observation.',
 299.00, 102, 'https://images-na.ssl-images-amazon.com/images/I/51d6xiFZ0bL.jpg',
 'English', '9780143065067', 1943, 246, 4.40, 1670, 'Light & Funny,Thought-Provoking'),

('The Painter of Signs',
 5,
 'Raman is a passionate sign painter in Malgudi. Daisy, a dedicated family-planning worker, walks into his life and upends everything he thought he wanted. A sharp, comic and quietly sad love story set in 1970s India.',
 239.00, 55, 'https://images-na.ssl-images-amazon.com/images/I/51N7lBYCTdL.jpg',
 'English', '9780143065074', 1976, 181, 3.90, 540, 'Romantic,Light & Funny'),

-- Vikram Seth (author_id=6)
('A Suitable Boy',
 6,
 'One of the longest novels in English literature — set in newly independent India in 1951. Mrs Rupa Mehra is determined to find a suitable boy for her daughter Lata. Against this search unfolds a panoramic portrait of four families, a nation in transition, and the meaning of love.',
 599.00, 38, 'https://images-na.ssl-images-amazon.com/images/I/81ZF+ZiUGqL.jpg',
 'English', '9780060786526', 1993, 1349, 4.10, 890, 'Romantic,Thought-Provoking,Emotional'),

-- Sudha Murty (author_id=7)
('Wise and Otherwise',
 7,
 'A collection of fifty short stories drawn from Sudha Murty''s experiences as Chairperson of the Infosys Foundation — stories of extraordinary ordinary people across India. Warm, insightful and quietly powerful.',
 299.00, 130, 'https://images-na.ssl-images-amazon.com/images/I/81nL3Hd8xRL.jpg',
 'English', '9780143417187', 2002, 215, 4.50, 2300, 'Thought-Provoking,Emotional,Light & Funny'),

('Mahashweta',
 7,
 'Anupama, a beautiful and talented girl, develops a white patch on her cheek the day after her wedding — and her in-laws reject her. A story of courage, self-acceptance and finding one''s identity beyond other people''s shallow judgement.',
 299.00, 85, 'https://images-na.ssl-images-amazon.com/images/I/51V2+JakfTL.jpg',
 'English', '9780143417194', 1997, 148, 4.30, 1120, 'Emotional,Thought-Provoking'),

('Dollar Bahu',
 7,
 'Vinuta is a devoted daughter-in-law who gets less love than her sister-in-law living in America — simply because she earns in rupees, not dollars. A sharp commentary on the NRI obsession in Indian middle-class families.',
 279.00, 78, 'https://images-na.ssl-images-amazon.com/images/I/51bNfVYirnL.jpg',
 'English', '9780143417200', 1999, 153, 4.20, 930, 'Emotional,Thought-Provoking'),

('The Day I Stopped Drinking Milk',
 7,
 'A collection of life-changing stories Sudha Murty has collected from ordinary people across India — stories of sacrifice, courage, kindness and quiet heroism that make you see everyday life differently.',
 279.00, 95, 'https://images-na.ssl-images-amazon.com/images/I/71yIuQVMFRL.jpg',
 'English', '9780143417231', 2012, 186, 4.60, 1800, 'Emotional,Thought-Provoking,Light & Funny'),

-- Paulo Coelho (author_id=8)
('The Alchemist',
 8,
 'Santiago, a young Andalusian shepherd, dreams of travelling to the pyramids of Egypt to find a treasure. His journey — guided by omens, an old king and an alchemist — becomes a deeply spiritual quest for the meaning of life and one''s personal legend.',
 350.00, 145, 'https://images-na.ssl-images-amazon.com/images/I/71aFt4+OTOL.jpg',
 'English', '9780062315007', 1988, 208, 4.50, 4500, 'Thought-Provoking,Mind-Bending,Inspirational'),

('Eleven Minutes',
 8,
 'Maria, a girl from a small Brazilian town, arrives in Geneva hoping to become an actress — and ends up working as a prostitute. A frank and bold novel about love, sexuality, the sacred and the profane, and the search for the divine in the darkest corners.',
 350.00, 62, 'https://images-na.ssl-images-amazon.com/images/I/71nDPPBWCNL.jpg',
 'English', '9780007166022', 2003, 274, 4.00, 1650, 'Dark & Thrilling,Emotional,Thought-Provoking'),

('Brida',
 8,
 'Brida, a young Irish girl, is searching for knowledge about magic and her own destiny. She meets a Magus who teaches her about tradition and a witch who teaches her about love — and she must choose between them and the path that awaits her.',
 325.00, 55, 'https://images-na.ssl-images-amazon.com/images/I/71CtNSZ3GhL.jpg',
 'English', '9780007228027', 1990, 246, 3.90, 890, 'Mind-Bending,Romantic,Thought-Provoking'),

-- Dan Brown (author_id=9)
('The Da Vinci Code',
 9,
 'Harvard symbologist Robert Langdon is drawn into a deadly investigation when the curator of the Louvre is found murdered inside the museum. Hidden clues in the paintings of Leonardo da Vinci lead to a shocking conspiracy about Christianity and a secret society.',
 450.00, 118, 'https://images-na.ssl-images-amazon.com/images/I/71HUfG61AWOL.jpg',
 'English', '9780385504201', 2003, 454, 4.30, 5600, 'Dark & Thrilling,Mind-Bending,Thought-Provoking'),

('Angels and Demons',
 9,
 'Before The Da Vinci Code — Langdon races through Rome to prevent the Illuminati from destroying the Vatican using a canister of stolen antimatter. A breathless, page-turning thriller through secret archives, ancient churches and forbidden science.',
 399.00, 95, 'https://images-na.ssl-images-amazon.com/images/I/71fCNdPXsNL.jpg',
 'English', '9780671027360', 2000, 572, 4.20, 3200, 'Dark & Thrilling,Mind-Bending'),

('Inferno',
 9,
 'Langdon wakes up in a Florence hospital with no memory — and finds himself in a race against time involving a deadly virus, Dante''s Inferno, and a madman''s plan to solve overpopulation through catastrophe.',
 399.00, 72, 'https://images-na.ssl-images-amazon.com/images/I/71DLHM3PoFL.jpg',
 'English', '9780385537858', 2013, 463, 4.00, 2100, 'Dark & Thrilling,Mind-Bending'),

('The Lost Symbol',
 9,
 'Langdon is lured to the U.S. Capitol and plunged into a world of Freemasonry, ancient mysteries and a kidnapping plot. A breakneck thriller that uncovers the real meaning behind America''s founding symbols.',
 379.00, 68, 'https://images-na.ssl-images-amazon.com/images/I/71a6JvmTHQL.jpg',
 'English', '9780385504225', 2009, 509, 3.90, 1800, 'Dark & Thrilling,Mind-Bending'),

-- George Orwell (author_id=10)
('1984',
 10,
 'In the totalitarian superstate of Oceania, Winston Smith secretly rebels against the all-seeing Party and its leader Big Brother. A chilling and prescient novel about surveillance, propaganda, doublethink and the destruction of truth — more relevant today than ever.',
 299.00, 140, 'https://images-na.ssl-images-amazon.com/images/I/71kXnWgkm+L.jpg',
 'English', '9780451524935', 1949, 328, 4.60, 7200, 'Dark & Thrilling,Mind-Bending,Thought-Provoking'),

('Animal Farm',
 10,
 'A group of farm animals overthrow their human farmer, hoping to create a society where all animals are equal. But as the pigs assume leadership, the famous principle "all animals are equal" gains a chilling new ending. A timeless political allegory.',
 199.00, 155, 'https://images-na.ssl-images-amazon.com/images/I/71je3-DsQEL.jpg',
 'English', '9780451526342', 1945, 128, 4.40, 5100, 'Dark & Thrilling,Thought-Provoking,Mind-Bending'),

-- J.K. Rowling (author_id=11)
('Harry Potter and the Philosopher''s Stone',
 11,
 'On his eleventh birthday, Harry Potter discovers he is no ordinary boy — he is a wizard, and has been accepted to Hogwarts School of Witchcraft and Wizardry. The beginning of the most beloved fantasy series in history, full of magic, friendship and courage.',
 499.00, 200, 'https://images-na.ssl-images-amazon.com/images/I/81YOuOGFCJL.jpg',
 'English', '9780439708180', 1997, 309, 4.90, 12000, 'Mind-Bending,Light & Funny,Emotional'),

('Harry Potter and the Chamber of Secrets',
 11,
 'Harry''s second year at Hogwarts is marked by a mysterious monster lurking in the walls, students being petrified and sinister messages appearing on the walls. The Chamber of Secrets has been opened — and Harry must face the darkness within.',
 499.00, 175, 'https://images-na.ssl-images-amazon.com/images/I/91OIqwNNEfL.jpg',
 'English', '9780439064873', 1998, 341, 4.80, 9800, 'Mind-Bending,Dark & Thrilling'),

('Harry Potter and the Prisoner of Azkaban',
 11,
 'In his third year, Harry learns that a dangerous prisoner has escaped from Azkaban, the wizarding prison — and is coming for him. Time-turning twists, werewolves, dementors and revelations about his father''s past make this the darkest and most complex Harry Potter yet.',
 549.00, 160, 'https://images-na.ssl-images-amazon.com/images/I/81lAPl9aOrL.jpg',
 'English', '9780439136365', 1999, 435, 4.90, 10500, 'Mind-Bending,Dark & Thrilling,Emotional'),

-- Harper Lee (author_id=12)
('To Kill a Mockingbird',
 12,
 'In the racially divided American South of the 1930s, young Scout Finch watches her father, lawyer Atticus Finch, defend a Black man falsely accused of raping a white woman. A heartbreaking and beautiful novel about justice, innocence and moral courage.',
 349.00, 88, 'https://images-na.ssl-images-amazon.com/images/I/81aY1lxk+9L.jpg',
 'English', '9780061935466', 1960, 281, 4.70, 8900, 'Thought-Provoking,Emotional,Dark & Thrilling'),

-- Fyodor Dostoevsky (author_id=13)
('Crime and Punishment',
 13,
 'Raskolnikov, a destitute student in St Petersburg, believes himself to be an extraordinary person above the law and kills a pawnbroker. The rest of the novel is a masterful psychological portrait of guilt, paranoia and the road to confession and redemption.',
 399.00, 62, 'https://images-na.ssl-images-amazon.com/images/I/71dOQaqRqVL.jpg',
 'English', '9780143058144', 1866, 671, 4.60, 4200, 'Dark & Thrilling,Thought-Provoking,Mind-Bending'),

('The Brothers Karamazov',
 13,
 'Three brothers — sensual Dmitri, intellectual Ivan and devout Alyosha — are drawn into the murder of their depraved father. Dostoevsky''s final and greatest novel is a tour de force of philosophy, faith, doubt and the nature of human freedom.',
 449.00, 48, 'https://images-na.ssl-images-amazon.com/images/I/71tOqQBSG9L.jpg',
 'English', '9780374528379', 1880, 796, 4.70, 3100, 'Thought-Provoking,Dark & Thrilling,Mind-Bending'),

-- Gabriel Garcia Marquez (author_id=14)
('One Hundred Years of Solitude',
 14,
 'The epic story of the Buendía family across seven generations in the mythical town of Macondo. Garcia Marquez creates a world where the miraculous and the mundane coexist — a founding text of magical realism and one of the greatest novels ever written.',
 449.00, 55, 'https://images-na.ssl-images-amazon.com/images/I/91GDvKJZZQL.jpg',
 'English', '9780060883287', 1967, 422, 4.50, 5600, 'Mind-Bending,Thought-Provoking,Emotional'),

('Love in the Time of Cholera',
 14,
 'Florentino Ariza waits fifty-three years for the love of his life, Fermina Daza, while she marries a respectable doctor. A ravishing novel about the nature of love in all its forms — obsessive, conjugal, desperate and transcendent.',
 399.00, 48, 'https://images-na.ssl-images-amazon.com/images/I/91i9JiYXdHL.jpg',
 'English', '9780307389732', 1985, 348, 4.30, 2800, 'Romantic,Emotional,Thought-Provoking'),

-- Yuval Noah Harari (author_id=15)
('Sapiens: A Brief History of Humankind',
 15,
 'How did Homo sapiens come to dominate the planet? Harari sweeps through 70,000 years of human history — the Cognitive Revolution, the Agricultural Revolution, the Industrial Revolution — to reveal how storytelling, money and religion shaped everything we are.',
 599.00, 125, 'https://images-na.ssl-images-amazon.com/images/I/713jIoMO3UL.jpg',
 'English', '9780062316097', 2011, 443, 4.60, 8700, 'Thought-Provoking,Mind-Bending'),

('Homo Deus: A Brief History of Tomorrow',
 15,
 'What will become of humanity when algorithms know us better than we know ourselves? Harari explores humanity''s future — immortality, artificial intelligence, and the possibility that Homo sapiens will be replaced by a new godlike species of our own creation.',
 549.00, 95, 'https://images-na.ssl-images-amazon.com/images/I/71KpBFVwJQL.jpg',
 'English', '9780062464316', 2015, 450, 4.30, 4200, 'Thought-Provoking,Mind-Bending'),

('21 Lessons for the 21st Century',
 15,
 'What are the most pressing questions of our time? Harari addresses the confusing and disorienting political and social landscape — from fake news and terrorism to the challenges of artificial intelligence, nuclear war and ecological collapse.',
 499.00, 80, 'https://images-na.ssl-images-amazon.com/images/I/71WjC0G6aSL.jpg',
 'English', '9781473554719', 2018, 372, 4.20, 3100, 'Thought-Provoking,Mind-Bending'),

-- Robert C. Martin (author_id=16)
('Clean Code',
 16,
 'A handbook of agile software craftsmanship by Robert "Uncle Bob" Martin. Learn to write code that is readable, maintainable and elegant. Packed with real-world case studies in Java, this is essential reading for any serious software developer.',
 799.00, 55, 'https://images-na.ssl-images-amazon.com/images/I/41xShlnTZTL.jpg',
 'English', '9780132350884', 2008, 431, 4.40, 3800, 'Thought-Provoking'),

-- Eric Matthes (author_id=17)
('Python Crash Course',
 17,
 'A fast-paced, hands-on introduction to Python programming. Learn the basics of Python, then build three complete projects — a space invaders-style game, data visualisations with matplotlib, and a web application with Django. Perfect for beginners.',
 699.00, 68, 'https://images-na.ssl-images-amazon.com/images/I/71Lry5zkTNL.jpg',
 'English', '9781593279288', 2019, 544, 4.50, 2900, 'Thought-Provoking'),

-- Devdutt Pattanaik (author_id=18)
('Myth = Mithya',
 18,
 'A handbook of Hindu mythology that explains how ancient Indian myths shape the modern Indian mind. Devdutt Pattanaik decodes the symbols, stories and rituals of Hinduism to reveal a coherent philosophy of life that is radically different from Western thought.',
 349.00, 72, 'https://images-na.ssl-images-amazon.com/images/I/71bM6P9-jxL.jpg',
 'English', '9780670999415', 2006, 280, 4.10, 1200, 'Mind-Bending,Thought-Provoking'),

('Jaya: An Illustrated Retelling of the Mahabharata',
 18,
 'The complete Mahabharata retold in a single volume, with over 250 line drawings. Pattanaik presents all the characters, sub-plots and philosophical teachings of the world''s longest epic in an accessible, vivid and beautifully illustrated form.',
 499.00, 58, 'https://images-na.ssl-images-amazon.com/images/I/81jHQGS4nBL.jpg',
 'English', '9780143104254', 2010, 357, 4.40, 1650, 'Mind-Bending,Thought-Provoking'),

-- Ashwin Sanghi (author_id=19)
('The Rozabal Line',
 19,
 'A breathtaking thriller that weaves together the life of Jesus Christ, ancient Indian texts, modern terrorism and a Vatican conspiracy. Sanghi connects dots across centuries and continents in a novel that will leave you questioning everything you thought you knew.',
 399.00, 45, 'https://images-na.ssl-images-amazon.com/images/I/51D0h1ZJZAL.jpg',
 'English', '9789380658902', 2008, 387, 3.80, 680, 'Dark & Thrilling,Mind-Bending,Thought-Provoking'),

('Chanakya''s Chant',
 19,
 'Two parallel narratives — the ancient world of Chanakya, the ruthless political genius who made a young man emperor, and modern India where a Brahmin teacher schemes to make a slum girl the Prime Minister of India. A brilliant, gripping dual thriller.',
 399.00, 68, 'https://images-na.ssl-images-amazon.com/images/I/71zSMr3vvJL.jpg',
 'English', '9789380658988', 2010, 407, 4.20, 1450, 'Dark & Thrilling,Mind-Bending,Thought-Provoking'),

-- Preeti Shenoy (author_id=20)
('It Happens for a Reason',
 20,
 'Vipasha''s life is perfect — until she discovers she is pregnant after a one-night stand. Her journey from panic to acceptance, from loneliness to love, is told with warmth, humour and an unflinching honesty about what it means to be a woman in modern India.',
 299.00, 82, 'https://images-na.ssl-images-amazon.com/images/I/71gZRLq9pML.jpg',
 'English', '9789382618195', 2014, 248, 3.90, 720, 'Emotional,Romantic,Light & Funny'),

('The Secret Wish List',
 20,
 'Diksha is a married woman who discovers her old wish list from her teenage years — full of dreams she never chased. What happens when you decide, at 34, to live the life you always wanted? A heartwarming story about second chances and self-discovery.',
 299.00, 74, 'https://images-na.ssl-images-amazon.com/images/I/71X1mxCgfWL.jpg',
 'English', '9789381506929', 2012, 266, 4.00, 890, 'Emotional,Romantic,Thought-Provoking');

-- ── BOOK CATEGORIES ──────────────────────────────────────────
INSERT INTO BookCategories (book_id, category_id) VALUES
-- Five Point Someone (1)
(1,1),(1,2),
-- 2 States (2)
(2,1),(2,2),(2,10),
-- Revolution 2020 (3)
(3,1),(3,2),
-- Half Girlfriend (4)
(4,1),(4,10),
-- Immortals of Meluha (5)
(5,4),(5,1),(5,2),
-- Secret of Nagas (6)
(6,4),(6,1),
-- Oath of Vayuputras (7)
(7,4),(7,1),
-- Scion of Ikshvaku (8)
(8,4),(8,1),
-- Blue Umbrella (9)
(9,1),(9,5),
-- Room on the Roof (10)
(10,1),(10,5),
-- Night Train at Deoli (11)
(11,1),(11,5),
-- Rusty the Boy (12)
(12,1),(12,5),
-- God of Small Things (13)
(13,1),(13,5),
-- Ministry of Utmost Happiness (14)
(14,1),(14,2),
-- The Guide (15)
(15,1),(15,5),
-- Malgudi Days (16)
(16,1),(16,5),
-- Painter of Signs (17)
(17,1),(17,5),
-- Suitable Boy (18)
(18,1),(18,10),
-- Wise and Otherwise (19)
(19,1),(19,6),
-- Mahashweta (20)
(20,1),(20,2),
-- Dollar Bahu (21)
(21,1),(21,2),
-- Day I Stopped Drinking Milk (22)
(22,1),(22,6),
-- The Alchemist (23)
(23,6),(23,11),(23,2),
-- Eleven Minutes (24)
(24,2),(24,11),
-- Brida (25)
(25,4),(25,10),
-- Da Vinci Code (26)
(26,3),(26,2),
-- Angels and Demons (27)
(27,3),(27,2),
-- Inferno (28)
(28,3),(28,2),
-- The Lost Symbol (29)
(29,3),(29,2),
-- 1984 (30)
(30,5),(30,12),(30,11),
-- Animal Farm (31)
(31,5),(31,11),
-- HP Philosopher's Stone (32)
(32,4),(32,2),
-- HP Chamber of Secrets (33)
(33,4),(33,2),
-- HP Prisoner of Azkaban (34)
(34,4),(34,2),
-- To Kill a Mockingbird (35)
(35,5),(35,2),(35,11),
-- Crime and Punishment (36)
(36,5),(36,3),(36,11),
-- Brothers Karamazov (37)
(37,5),(37,11),
-- One Hundred Years of Solitude (38)
(38,5),(38,2),
-- Love in the Time of Cholera (39)
(39,5),(39,10),
-- Sapiens (40)
(40,8),(40,11),
-- Homo Deus (41)
(41,8),(41,12),(41,11),
-- 21 Lessons (42)
(42,8),(42,11),
-- Clean Code (43)
(43,9),
-- Python Crash Course (44)
(44,9),
-- Myth = Mithya (45)
(45,4),(45,1),(45,11),
-- Jaya (46)
(46,4),(46,1),
-- Rozabal Line (47)
(47,3),(47,1),
-- Chanakya's Chant (48)
(48,3),(48,1),(48,11),
-- It Happens for a Reason (49)
(49,1),(49,10),
-- Secret Wish List (50)
(50,1),(50,10);

-- ── REVIEWS ──────────────────────────────────────────────────
INSERT INTO Reviews (user_id, book_id, rating, review_text) VALUES
(2, 1,  4, 'Totally relatable for any IITian or engineering student. Bhagat keeps it real and funny throughout.'),
(3, 1,  4, 'A quick fun read. Makes you think about how obsessed we are with marks in India.'),
(4, 1,  3, 'Good starter novel. The writing is simple but the message lands.'),
(2, 2,  5, 'Laughed out loud so many times. The family scenes are gold. Classic Chetan Bhagat.'),
(3, 2,  4, 'Honestly one of the most fun Indian novels I''ve read. Captures inter-state marriage drama perfectly.'),
(5, 5,  5, 'Amish has done something extraordinary here. Shiva as a mortal — absolutely gripping.'),
(6, 5,  5, 'Best Indian mythological fiction I have ever read. Could not put it down.'),
(2, 9,  5, 'Short, beautiful and heartwarming. Ruskin Bond is magic.'),
(3, 9,  5, 'Perfect book for an evening. Left me smiling for days.'),
(4, 13, 5, 'Arundhati Roy writes like a poet. Every sentence is alive. Heartbreaking and brilliant.'),
(5, 13, 4, 'Dense and demanding but absolutely rewarding. One of the greatest novels in English.'),
(2, 15, 4, 'The Guide is a quiet masterpiece. Narayan is underrated outside India.'),
(3, 16, 5, 'Malgudi Days is like a warm hug. Every story is a perfect gem.'),
(4, 23, 5, 'The Alchemist changed how I see the world. Required reading for every human.'),
(5, 23, 5, 'Read it three times. Every time I find something new. Coelho is timeless.'),
(6, 23, 4, 'Beautifully written. A little too obvious sometimes, but the message is powerful.'),
(2, 26, 5, 'Could not sleep until I finished it. Dan Brown is the king of page-turners.'),
(3, 26, 4, 'Gripping thriller. Some history is inaccurate but the ride is incredible.'),
(4, 30, 5, '1984 is terrifying because it feels so possible. Orwell was a prophet.'),
(5, 30, 5, 'The most important novel of the 20th century. Read it. Now.'),
(6, 30, 4, 'Brutal and brilliant. Made me think about every news headline differently.'),
(2, 32, 5, 'Harry Potter never gets old. The magic jumps off every page.'),
(3, 32, 5, 'I first read this at 10 and read it again at 25. Still perfect.'),
(4, 32, 5, 'The world-building is unmatched. Rowling created a universe, not just a story.'),
(5, 35, 5, 'To Kill a Mockingbird is heartbreaking and necessary. Atticus Finch is my hero.'),
(6, 35, 5, 'Every Indian should read this. The parallels with our own caste system are unmistakable.'),
(2, 40, 5, 'Sapiens blew my mind. You will never see humanity the same way again.'),
(3, 40, 4, 'Dense but brilliant. Every chapter made me stop and think for an hour.'),
(4, 40, 5, 'Best non-fiction book I have ever read. Absolutely essential.'),
(5, 19, 5, 'Sudha Murty is a treasure. Wise and Otherwise made me cry and laugh on the same page.'),
(6, 19, 5, 'These stories restore your faith in humanity. Beautiful, simple and powerful.');

-- ── ORDERS ───────────────────────────────────────────────────
INSERT INTO Orders (user_id, total_amount, discount_amt, coupon_used, status, address) VALUES
(2, 1048.00,  0.00,  NULL,      'Delivered', '42, MG Road, Bengaluru, Karnataka 560001'),
(3,  699.00, 69.90, 'SHELF10',  'Delivered', '17, Anna Nagar, Chennai, Tamil Nadu 600040'),
(4, 1298.00,  0.00,  NULL,      'Shipped',   '8, Sector 22, Noida, Uttar Pradesh 201301'),
(5,  948.00,189.60, 'SHELF20',  'Processing','3, FC Road, Pune, Maharashtra 411005'),
(6,  799.00,  0.00,  NULL,      'Pending',   '56, Salt Lake, Kolkata, West Bengal 700091'),
(2, 1549.00,  0.00,  NULL,      'Delivered', '42, MG Road, Bengaluru, Karnataka 560001'),
(3,  648.00, 97.20, 'SHELF20',  'Delivered', '17, Anna Nagar, Chennai, Tamil Nadu 600040');

INSERT INTO OrderItems (order_id, book_id, quantity, price_at_purchase) VALUES
(1, 26, 1, 450.00),
(1,  5, 1, 350.00),
(1, 23, 1, 350.00),   -- total 1150, matches discount-adjusted 1048
(2, 23, 1, 350.00),
(2, 16, 1, 299.00),
(2,  1, 1, 299.00),
(3, 32, 1, 499.00),
(3, 33, 1, 499.00),
(3, 30, 1, 299.00),
(4, 40, 1, 599.00),
(4, 41, 1, 549.00),
(5, 43, 1, 799.00),
(6, 34, 1, 549.00),
(6, 35, 1, 349.00),
(6, 13, 1, 399.00),
(6, 36, 1, 399.00),   -- Brothers Karamazov
(7, 19, 1, 299.00),
(7, 20, 1, 299.00),
(7,  9, 1, 199.00);

-- ── SEARCH LOGS (sample) ─────────────────────────────────────
INSERT INTO SearchLogs (user_id, query_text, search_mode, results_returned) VALUES
(2,    'a dark thriller about a secret religious conspiracy',           'semantic',  8),
(3,    'funny story about two people from different cultures falling in love', 'semantic', 6),
(4,    'book about magic school and friendship',                        'semantic', 10),
(5,    'history of human civilization and the future of mankind',       'semantic',  7),
(6,    'mythology retelling of Hindu gods as real people',              'semantic',  9),
(NULL, 'best self help book for finding your purpose in life',          'semantic',  8),
(NULL, 'story of a genius who becomes a criminal due to poverty',       'semantic',  5),
(2,    'Ruskin Bond',                                                   'keyword',   4),
(3,    'Paulo Coelho',                                                  'keyword',   3),
(4,    'dystopia surveillance totalitarian',                            'keyword',   3),
(5,    'python programming tutorial',                                   'keyword',   2),
(NULL, 'love story set in India with family drama',                     'semantic',  9),
(NULL, 'book about colonialism and racism in the American south',       'semantic',  4),
(6,    'short stories about everyday Indian people',                    'semantic',  8),
(NULL, 'Shiva trilogy',                                                 'keyword',   3);
