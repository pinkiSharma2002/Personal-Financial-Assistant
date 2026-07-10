"""
MySQL Database Utility
User authentication & registration stored in MySQL
"""
import mysql.connector
import bcrypt
import streamlit as st

# ─── CHANGE THESE TO YOUR MySQL CREDENTIALS ───────────────────────────────────
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",  
    "database": "finance_manager",
}
# ──────────────────────────────────────────────────────────────────────────────


def get_connection():
    """Return a MySQL connection."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as e:
        st.error(f"❌ MySQL Connection Error: {e}")
        return None


def init_db():
    """Create DB and tables if they don't exist."""
    try:
        # Connect without database first to create it
        cfg = {k: v for k, v in DB_CONFIG.items() if k != "database"}
        conn = mysql.connector.connect(**cfg)
        cur = conn.cursor()
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        conn.commit()
        cur.close()
        conn.close()

        # Now connect to the database
        conn = get_connection()
        if not conn:
            return
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                username    VARCHAR(50) UNIQUE NOT NULL,
                email       VARCHAR(100) UNIQUE NOT NULL,
                password    VARCHAR(255) NOT NULL,
                full_name   VARCHAR(100),
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                user_id     INT NOT NULL,
                login_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        conn.commit()
        cur.close()
        conn.close()
    except mysql.connector.Error as e:
        st.error(f"❌ DB Init Error: {e}")


def register_user(username: str, email: str, password: str, full_name: str) -> dict:
    """Register a new user. Returns {'success': bool, 'message': str}."""
    conn = get_connection()
    if not conn:
        return {"success": False, "message": "Database connection failed."}
    try:
        cur = conn.cursor()
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        cur.execute(
            "INSERT INTO users (username, email, password, full_name) VALUES (%s, %s, %s, %s)",
            (username, email, hashed, full_name),
        )
        conn.commit()
        return {"success": True, "message": "Registration successful!"}
    except mysql.connector.IntegrityError:
        return {"success": False, "message": "Username or Email already exists."}
    finally:
        cur.close()
        conn.close()


def login_user(username: str, password: str) -> dict:
    """Authenticate user. Returns user dict or error."""
    conn = get_connection()
    if not conn:
        return {"success": False, "message": "Database connection failed."}
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        if not user:
            return {"success": False, "message": "User not found."}
        if bcrypt.checkpw(password.encode(), user["password"].encode()):
            # Log session
            cur.execute("INSERT INTO user_sessions (user_id) VALUES (%s)", (user["id"],))
            conn.commit()
            return {"success": True, "user": user}
        return {"success": False, "message": "Incorrect password."}
    finally:
        cur.close()
        conn.close()


def get_user_by_id(user_id: int) -> dict | None:
    conn = get_connection()
    if not conn:
        return None
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, username, email, full_name, created_at FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user
