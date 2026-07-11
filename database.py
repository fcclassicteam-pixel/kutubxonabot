import aiosqlite
from datetime import datetime
from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    full_name TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT,
    genre TEXT,
    book_type TEXT NOT NULL,          -- 'audio' yoki 'text'
    description TEXT,
    file_id TEXT,                     -- Telegram file_id (audio yoki document)
    cover_file_id TEXT,               -- muqova rasmi (ixtiyoriy)
    price INTEGER DEFAULT 0,          -- 0 = bepul
    is_active INTEGER DEFAULT 1,
    added_by INTEGER,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    rating INTEGER NOT NULL,          -- 1-5
    comment TEXT,
    created_at TEXT,
    UNIQUE(book_id, user_id)
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    book_title TEXT NOT NULL,
    details TEXT,
    price INTEGER DEFAULT 0,
    status TEXT DEFAULT 'yangi',      -- yangi, jarayonda, bajarildi, bekor qilindi
    payment_status TEXT DEFAULT 'kutilmoqda',  -- kutilmoqda, tolandi, kerak_emas
    payment_provider TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    provider TEXT NOT NULL,           -- click yoki payme
    provider_transaction_id TEXT,
    amount INTEGER,
    state INTEGER DEFAULT 0,          -- provider-specific holat kodi
    status TEXT DEFAULT 'yaratildi',  -- yaratildi, tolandi, bekor_qilindi
    created_at TEXT,
    performed_at TEXT,
    cancelled_at TEXT
);
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


def _now():
    return datetime.utcnow().isoformat()


# ---------- USERS ----------

async def upsert_user(telegram_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO users (telegram_id, username, full_name, created_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(telegram_id) DO UPDATE SET
                   username=excluded.username,
                   full_name=excluded.full_name""",
            (telegram_id, username, full_name, _now()),
        )
        await db.commit()


async def count_users() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users")
        row = await cur.fetchone()
        return row[0]


# ---------- BOOKS ----------

async def add_book(title, author, genre, book_type, description, file_id,
                    cover_file_id, price, added_by) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO books
               (title, author, genre, book_type, description, file_id,
                cover_file_id, price, added_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (title, author, genre, book_type, description, file_id,
             cover_file_id, price, added_by, _now()),
        )
        await db.commit()
        return cur.lastrowid


async def get_book(book_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM books WHERE id=?", (book_id,))
        return await cur.fetchone()


async def search_books(query: str, limit: int = 20):
    like = f"%{query}%"
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT * FROM books
               WHERE is_active=1 AND (title LIKE ? OR author LIKE ?)
               ORDER BY created_at DESC LIMIT ?""",
            (like, like, limit),
        )
        return await cur.fetchall()


async def get_genres():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT DISTINCT genre FROM books WHERE is_active=1 AND genre IS NOT NULL"
        )
        rows = await cur.fetchall()
        return [r[0] for r in rows if r[0]]


async def get_books_by_genre(genre: str, offset: int = 0, limit: int = 6):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT * FROM books WHERE is_active=1 AND genre=?
               ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (genre, limit, offset),
        )
        return await cur.fetchall()


async def get_books_by_type(book_type: str, offset: int = 0, limit: int = 6):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT * FROM books WHERE is_active=1 AND book_type=?
               ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (book_type, limit, offset),
        )
        return await cur.fetchall()


async def deactivate_book(book_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE books SET is_active=0 WHERE id=?", (book_id,))
        await db.commit()


# ---------- RATINGS ----------

async def add_rating(book_id: int, user_id: int, rating: int, comment: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO ratings (book_id, user_id, rating, comment, created_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(book_id, user_id) DO UPDATE SET
                   rating=excluded.rating, comment=excluded.comment""",
            (book_id, user_id, rating, comment, _now()),
        )
        await db.commit()


async def get_book_rating(book_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT AVG(rating), COUNT(*) FROM ratings WHERE book_id=?", (book_id,)
        )
        avg, count = await cur.fetchone()
        return (round(avg, 1) if avg else 0.0, count)


# ---------- ORDERS ----------

async def create_order(user_id: int, book_title: str, details: str, price: int = 0) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO orders (user_id, book_title, details, price, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, book_title, details, price, _now()),
        )
        await db.commit()
        return cur.lastrowid


async def get_order(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM orders WHERE id=?", (order_id,))
        return await cur.fetchone()


async def set_order_price(order_id: int, price: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET price=?, status='jarayonda' WHERE id=?",
            (price, order_id),
        )
        await db.commit()


async def set_order_status(order_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
        await db.commit()


async def set_order_payment_status(order_id: int, payment_status: str, provider: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if provider:
            await db.execute(
                "UPDATE orders SET payment_status=?, payment_provider=? WHERE id=?",
                (payment_status, provider, order_id),
            )
        else:
            await db.execute(
                "UPDATE orders SET payment_status=? WHERE id=?",
                (payment_status, order_id),
            )
        await db.commit()


async def get_pending_orders():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM orders WHERE status IN ('yangi','jarayonda') ORDER BY created_at DESC"
        )
        return await cur.fetchall()


# ---------- PAYMENTS ----------

async def create_payment(order_id: int, provider: str, amount: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO payments (order_id, provider, amount, created_at)
               VALUES (?, ?, ?, ?)""",
            (order_id, provider, amount, _now()),
        )
        await db.commit()
        return cur.lastrowid


async def get_payment_by_transaction(provider: str, transaction_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM payments WHERE provider=? AND provider_transaction_id=?",
            (provider, transaction_id),
        )
        return await cur.fetchone()


async def get_payment(payment_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM payments WHERE id=?", (payment_id,))
        return await cur.fetchone()


async def set_payment_transaction(payment_id: int, provider_transaction_id: str, state: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE payments SET provider_transaction_id=?, state=? WHERE id=?",
            (provider_transaction_id, state, payment_id),
        )
        await db.commit()


async def mark_payment_performed(payment_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPD
