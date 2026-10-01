from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
load_dotenv()

import sqlite3
import os
import jwt
import time
import re
import secrets
import base64
import hashlib
import requests

from datetime import datetime, timedelta
from functools import wraps

# =========================================================
# ShieldScan Configuration
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "shieldscan.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
FRONTEND_DIR = BASE_DIR

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "shieldscan-dev-fallback-change-me"
)

TOKEN_EXP_HOURS = 24

DATABASE_URL = os.environ.get("DATABASE_URL", "")
VIRUSTOTAL_API_KEY = os.environ.get("VT_API_KEY", "")

VT_BASE = "https://www.virustotal.com/api/v3"

MAX_FILE_SIZE = 50 * 1024 * 1024

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, static_folder=None)

app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE

CORS(
    app,
    supports_credentials=True
)


# =========================================================
# Security Headers
# =========================================================

@app.after_request
def security_headers(response):

    response.headers["X-Content-Type-Options"] = "nosniff"

    response.headers["X-Frame-Options"] = "SAMEORIGIN"

    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )

    response.headers["X-XSS-Protection"] = "0"

    response.headers["Cache-Control"] = "no-store"

    return response


# =========================================================
# Database Helpers
# =========================================================

def is_pg():
    return bool(DATABASE_URL)


def ph():
    return "%s" if is_pg() else "?"


def get_db():

    if DATABASE_URL:

        import psycopg2
        from psycopg2.extras import RealDictCursor

        return psycopg2.connect(
            DATABASE_URL,
            cursor_factory=RealDictCursor
        )

    conn = sqlite3.connect(
        DB_PATH,
        timeout=30
    )

    conn.row_factory = sqlite3.Row

    return conn


# =========================================================
# Database Initialization
# =========================================================

def init_db():

    pg = is_pg()

    conn = get_db()
    c = conn.cursor()

    if pg:

        c.execute("""
            CREATE TABLE IF NOT EXISTS users(
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS scans(
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                type TEXT NOT NULL,
                target TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS messages(
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                subject TEXT,
                message TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS pages(
                id SERIAL PRIMARY KEY,
                page_name TEXT NOT NULL,
                section_name TEXT NOT NULL,
                field_key TEXT NOT NULL,
                field_value TEXT,
                UNIQUE(page_name, section_name, field_key)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS content(
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS design(
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

    else:

        c.execute("""
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS scans(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT NOT NULL,
                target TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS messages(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                subject TEXT,
                message TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS pages(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_name TEXT NOT NULL,
                section_name TEXT NOT NULL,
                field_key TEXT NOT NULL,
                field_value TEXT,
                UNIQUE(page_name, section_name, field_key)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS content(
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS design(
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

    # =====================================================
    # Admin Account
    # =====================================================

    admin_email = os.environ.get(
        "ADMIN_EMAIL",
        "admin@shieldscan.local"
    )

    admin_pass = os.environ.get(
        "ADMIN_PASSWORD",
        "V9!rQ2@Lm7#Zx4$Np8&Tk6"
    )

    p = ph()

    c.execute(
        "SELECT id FROM users WHERE is_admin=1 LIMIT 1"
    )

    if not c.fetchone():

        c.execute(
            f"""
            INSERT INTO users(
                name,
                email,
                password,
                is_admin
            )
            VALUES({p},{p},{p},1)
            """,
            (
                "Admin",
                admin_email,
                generate_password_hash(admin_pass)
            )
        )

    # =====================================================
    # Default Content
    # =====================================================

    default_content = {
        "heroPill": "⚡ مدعوم بمحركات فحص متعددة",
        "heroT1": "افحص أي",
        "heroT2": "قبل أن يفتحه أحد",
        "footCopy": "© 2026 ShieldScan",
        "brand1": "Shield",
        "brand2": "Scan"
    }

    for key, value in default_content.items():

        if pg:

            c.execute(
                """
                INSERT INTO content(key,value)
                VALUES(%s,%s)
                ON CONFLICT (key) DO NOTHING
                """,
                (key, value)
            )

        else:

            c.execute(
                """
                INSERT OR IGNORE INTO content(key,value)
                VALUES(?,?)
                """,
                (key, value)
            )

    # =====================================================
    # Default Design
    # =====================================================

    default_design = {
        "primary": "#6366f1",
        "secondary": "#8b5cf6",
        "accent": "#ec4899",
        "bg": "#f8fafc",
        "text": "#1e293b",
        "muted": "#64748b",
        "size": "100",
        "radius": "100"
    }

    for key, value in default_design.items():

        if pg:

            c.execute(
                """
                INSERT INTO design(key,value)
                VALUES(%s,%s)
                ON CONFLICT (key) DO NOTHING
                """,
                (key, value)
            )

        else:

            c.execute(
                """
                INSERT OR IGNORE INTO design(key,value)
                VALUES(?,?)
                """,
                (key, value)
            )

    conn.commit()
    conn.close()


# =========================================================
# JWT
# =========================================================

def make_token(user):

    return jwt.encode(
        {
            "user_id": user["id"],
            "email": user["email"],
            "is_admin": user["is_admin"],
            "exp": datetime.utcnow()
            + timedelta(hours=TOKEN_EXP_HOURS)
        },
        SECRET_KEY,
        algorithm="HS256"
    )


def get_token_user():

    auth = request.headers.get("Authorization", "")

    if not auth.startswith("Bearer "):
        return None

    try:

        token = auth[7:]

        data = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=["HS256"]
        )

        conn = get_db()
        c = conn.cursor()

        c.execute(
            f"SELECT * FROM users WHERE id={ph()}",
            (data["user_id"],)
        )

        user = c.fetchone()

        conn.close()

        return user

    except Exception:
        return None


def require_auth(f):

    @wraps(f)
    def wrapper(*args, **kwargs):

        user = get_token_user()

        if not user:
            return jsonify({
                "error": "Unauthorized"
            }), 401

        if user["is_banned"]:
            return jsonify({
                "error": "Account banned"
            }), 403

        return f(user, *args, **kwargs)

    return wrapper


def require_admin(f):

    @wraps(f)
    def wrapper(*args, **kwargs):

        user = get_token_user()

        if not user:
            return jsonify({
                "error": "Unauthorized"
            }), 401

        if not user["is_admin"]:
            return jsonify({
                "error": "Admin only"
            }), 403

        return f(user, *args, **kwargs)

    return wrapper


# =========================================================
# Authentication
# =========================================================

@app.route("/api/auth/register", methods=["POST"])
def register():

    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if len(name) < 3:
        return jsonify({"error": "الاسم قصير"}), 400

    if not re.match(
        r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        email
    ):
        return jsonify({"error": "بريد غير صالح"}), 400

    if len(password) < 6:
        return jsonify({
            "error": "كلمة المرور قصيرة"
        }), 400

    conn = get_db()
    c = conn.cursor()
    p = ph()

    try:

        c.execute(
            f"""
            INSERT INTO users(name,email,password)
            VALUES({p},{p},{p})
            """,
            (
                name,
                email,
                generate_password_hash(password)
            )
        )

        conn.commit()

        c.execute(
            f"SELECT * FROM users WHERE email={p}",
            (email,)
        )

        user = c.fetchone()

        token = make_token(user)

        conn.close()

        return jsonify({
            "token": token,
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "is_admin": bool(user["is_admin"])
            }
        }), 201

    except Exception as e:

        conn.rollback()
        conn.close()

        if (
            "unique" in str(e).lower()
            or "duplicate" in str(e).lower()
        ):
            return jsonify({
                "error": "البريد مسجل مسبقاً"
            }), 409

        return jsonify({
            "error": "فشل إنشاء الحساب"
        }), 400


@app.route("/api/auth/login", methods=["POST"])
def login():

    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    conn = get_db()
    c = conn.cursor()

    c.execute(
        f"SELECT * FROM users WHERE email={ph()}",
        (email,)
    )

    user = c.fetchone()

    conn.close()

    if not user or not check_password_hash(
        user["password"],
        password
    ):
        return jsonify({
            "error": "بيانات خاطئة"
        }), 401

    if user["is_banned"]:
        return jsonify({
            "error": "محظور"
        }), 403

    return jsonify({
        "token": make_token(user),
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "is_admin": bool(user["is_admin"])
        }
    })


@app.route("/api/auth/me", methods=["GET"])
@require_auth
def me(user):

    return jsonify({
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "is_admin": bool(user["is_admin"])
        }
    })


# =========================================================
# Scans
# =========================================================

@app.route("/api/scans", methods=["POST"])
def create_scan():

    data = request.get_json(silent=True) or {}

    type_ = data.get("type")
    target = (data.get("target") or "").strip()

    status = data.get("status", "safe")
    details = data.get("details", "")

    if type_ not in (
        "url",
        "file",
        "ip",
        "email"
    ):
        return jsonify({
            "error": "نوع الفحص غير صالح"
        }), 400

    if not target:
        return jsonify({
            "error": "بيانات ناقصة"
        }), 400

    user = get_token_user()

    user_id = user["id"] if user else None

    conn = get_db()
    c = conn.cursor()
    p = ph()

    c.execute(
        f"""
        INSERT INTO scans(
            user_id,
            type,
            target,
            status,
            details
        )
        VALUES({p},{p},{p},{p},{p})
        """,
        (
            user_id,
            type_,
            target,
            status,
            details
        )
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True
    }), 201


@app.route("/api/scans", methods=["GET"])
@require_auth
def my_scans(user):

    conn = get_db()
    c = conn.cursor()

    c.execute(
        f"""
        SELECT *
        FROM scans
        WHERE user_id={ph()}
        ORDER BY id DESC
        LIMIT 100
        """,
        (user["id"],)
    )

    rows = c.fetchall()

    conn.close()

    return jsonify([
        dict(row)
        for row in rows
    ])


@app.route("/api/scans/clear", methods=["DELETE"])
@require_auth
def clear_my_scans(user):

    conn = get_db()
    c = conn.cursor()

    c.execute(
        f"DELETE FROM scans WHERE user_id={ph()}",
        (user["id"],)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True
    })


@app.route("/api/scans/<int:scan_id>", methods=["DELETE"])
@require_auth
def delete_my_scan(user, scan_id):

    conn = get_db()
    c = conn.cursor()
    p = ph()

    c.execute(
        f"""
        DELETE FROM scans
        WHERE id={p}
        AND user_id={p}
        """,
        (
            scan_id,
            user["id"]
        )
    )

    conn.commit()

    deleted = c.rowcount

    conn.close()

    if deleted == 0:
        return jsonify({
            "error": "not found"
        }), 404

    return jsonify({
        "success": True
    })


# =========================================================
# Messages
# =========================================================

@app.route("/api/messages", methods=["POST"])
def create_message():

    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    subject = (data.get("subject") or "").strip()
    message = (data.get("message") or "").strip()

    if len(name) < 3:
        return jsonify({
            "error": "الاسم غير صالح"
        }), 400

    if not re.match(
        r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        email
    ):
        return jsonify({
            "error": "البريد غير صالح"
        }), 400

    if len(message) < 10:
        return jsonify({
            "error": "الرسالة قصيرة"
        }), 400

    conn = get_db()
    c = conn.cursor()
    p = ph()

    c.execute(
        f"""
        INSERT INTO messages(
            name,
            email,
            subject,
            message
        )
        VALUES({p},{p},{p},{p})
        """,
        (
            name,
            email,
            subject,
            message
        )
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True
    }), 201


# =========================================================
# Content
# =========================================================

@app.route("/api/content", methods=["GET"])
def get_content():

    conn = get_db()
    c = conn.cursor()

    c.execute(
        "SELECT key,value FROM content"
    )

    rows = c.fetchall()

    conn.close()

    return jsonify({
        row["key"]: row["value"]
        for row in rows
    })


@app.route("/api/design", methods=["GET"])
def get_design():

    conn = get_db()
    c = conn.cursor()

    c.execute(
        "SELECT key,value FROM design"
    )

    rows = c.fetchall()

    conn.close()

    return jsonify({
        row["key"]: row["value"]
        for row in rows
    })


# =========================================================
# Pages
# =========================================================

@app.route("/api/pages", methods=["GET"])
def get_pages():

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        SELECT
            page_name,
            section_name,
            field_key,
            field_value
        FROM pages
    """)

    rows = c.fetchall()

    conn.close()

    result = {}

    for row in rows:

        page = row["page_name"]
        section = row["section_name"]

        result.setdefault(page, {})
        result[page].setdefault(section, {})

        result[page][section][
            row["field_key"]
        ] = row["field_value"]

    return jsonify(result)


@app.route("/api/admin/pages", methods=["POST"])
@require_admin
def update_pages(user):

    data = request.get_json(silent=True) or {}

    conn = get_db()
    c = conn.cursor()

    pg = is_pg()

    count = 0

    for page, sections in data.items():

        if not isinstance(sections, dict):
            continue

        for section, fields in sections.items():

            if not isinstance(fields, dict):
                continue

            for key, value in fields.items():

                if pg:

                    c.execute(
                        """
                        INSERT INTO pages(
                            page_name,
                            section_name,
                            field_key,
                            field_value
                        )
                        VALUES(%s,%s,%s,%s)
                        ON CONFLICT(
                            page_name,
                            section_name,
                            field_key
                        )
                        DO UPDATE SET
                            field_value=excluded.field_value
                        """,
                        (
                            page,
                            section,
                            key,
                            str(value)
                        )
                    )

                else:

                    c.execute(
                        """
                        INSERT OR REPLACE INTO pages(
                            page_name,
                            section_name,
                            field_key,
                            field_value
                        )
                        VALUES(?,?,?,?)
                        """,
                        (
                            page,
                            section,
                            key,
                            str(value)
                        )
                    )

                count += 1

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "updated": count
    })


# =========================================================
# Admin Statistics
# =========================================================

@app.route("/api/admin/stats", methods=["GET"])
@require_admin
def admin_stats(user):

    conn = get_db()
    c = conn.cursor()

    def count(sql):

        c.execute(sql)

        row = c.fetchone()

        if row is None:
            return 0

        try:
            return row[0]
        except Exception:
            return list(row.values())[0]

    result = {
        "users": count(
            "SELECT COUNT(*) FROM users"
        ),
        "scans": count(
            "SELECT COUNT(*) FROM scans"
        ),
        "url_scans": count(
            "SELECT COUNT(*) FROM scans WHERE type='url'"
        ),
        "file_scans": count(
            "SELECT COUNT(*) FROM scans WHERE type='file'"
        ),
        "email_scans": count(
            "SELECT COUNT(*) FROM scans WHERE type='email'"
        ),
        "threats": count(
            """
            SELECT COUNT(*)
            FROM scans
            WHERE status IN ('danger','warning')
            """
        ),
        "messages": count(
            "SELECT COUNT(*) FROM messages"
        )
    }

    conn.close()

    return jsonify(result)


# =========================================================
# Admin Scans
# =========================================================

@app.route("/api/admin/scans", methods=["GET"])
@require_admin
def admin_scans(user):

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        SELECT *
        FROM scans
        ORDER BY id DESC
        LIMIT 500
    """)

    rows = c.fetchall()

    conn.close()

    return jsonify([
        dict(row)
        for row in rows
    ])


@app.route("/api/admin/scans/clear", methods=["DELETE"])
@require_admin
def admin_clear_scans(user):

    conn = get_db()
    c = conn.cursor()

    c.execute("DELETE FROM scans")

    conn.commit()
    conn.close()

    return jsonify({
        "success": True
    })


# =========================================================
# Admin Users
# =========================================================

@app.route("/api/admin/users", methods=["GET"])
@require_admin
def admin_users(user):

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        SELECT
            id,
            name,
            email,
            is_admin,
            is_banned,
            created_at
        FROM users
        ORDER BY id DESC
    """)

    rows = c.fetchall()

    conn.close()

    return jsonify([
        dict(row)
        for row in rows
    ])


@app.route("/api/admin/users/<int:uid>", methods=["DELETE"])
@require_admin
def admin_del_user(user, uid):

    if uid == user["id"]:
        return jsonify({
            "error": "لا يمكن حذف نفسك"
        }), 400

    conn = get_db()
    c = conn.cursor()

    c.execute(
        f"DELETE FROM users WHERE id={ph()}",
        (uid,)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True
    })


@app.route("/api/admin/users/<int:uid>/ban", methods=["POST"])
@require_admin
def admin_ban_user(user, uid):

    if uid == user["id"]:
        return jsonify({
            "error": "لا يمكن"
        }), 400

    conn = get_db()
    c = conn.cursor()

    c.execute(
        f"""
        UPDATE users
        SET is_banned = 1 - is_banned
        WHERE id={ph()}
        """,
        (uid,)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True
    })


# =========================================================
# Admin Messages
# =========================================================

@app.route("/api/admin/messages", methods=["GET"])
@require_admin
def admin_messages(user):

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        SELECT *
        FROM messages
        ORDER BY id DESC
    """)

    rows = c.fetchall()

    conn.close()

    return jsonify([
        dict(row)
        for row in rows
    ])


@app.route("/api/admin/messages/clear", methods=["DELETE"])
@require_admin
def admin_clear_messages(user):

    conn = get_db()
    c = conn.cursor()

    c.execute("DELETE FROM messages")

    conn.commit()
    conn.close()

    return jsonify({
        "success": True
    })


# =========================================================
# Admin Content
# =========================================================

@app.route("/api/admin/content", methods=["POST"])
@require_admin
def admin_update_content(user):

    data = request.get_json(silent=True) or {}

    conn = get_db()
    c = conn.cursor()

    pg = is_pg()

    for key, value in data.items():

        if pg:

            c.execute(
                """
                INSERT INTO content(key,value)
                VALUES(%s,%s)
                ON CONFLICT(key)
                DO UPDATE SET value=excluded.value
                """,
                (
                    key,
                    str(value)
                )
            )

        else:

            c.execute(
                """
                INSERT OR REPLACE INTO content(key,value)
                VALUES(?,?)
                """,
                (
                    key,
                    str(value)
                )
            )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True
    })


# =========================================================
# Admin Design
# =========================================================

@app.route("/api/admin/design", methods=["POST"])
@require_admin
def admin_update_design(user):

    data = request.get_json(silent=True) or {}

    conn = get_db()
    c = conn.cursor()

    pg = is_pg()

    for key, value in data.items():

        if pg:

            c.execute(
                """
                INSERT INTO design(key,value)
                VALUES(%s,%s)
                ON CONFLICT(key)
                DO UPDATE SET value=excluded.value
                """,
                (
                    key,
                    str(value)
                )
            )

        else:

            c.execute(
                """
                INSERT OR REPLACE INTO design(key,value)
                VALUES(?,?)
                """,
                (
                    key,
                    str(value)
                )
            )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True
    })


# =========================================================
# Admin Password
# =========================================================

@app.route("/api/admin/change-password", methods=["POST"])
@require_admin
def admin_change_password(user):

    data = request.get_json(silent=True) or {}

    old = data.get("old") or ""
    new = data.get("new") or ""

    if len(new) < 8:
        return jsonify({
            "error": "كلمة المرور الجديدة قصيرة"
        }), 400

    if not check_password_hash(
        user["password"],
        old
    ):
        return jsonify({
            "error": "كلمة المرور الحالية خاطئة"
        }), 400

    conn = get_db()
    c = conn.cursor()

    c.execute(
        f"""
        UPDATE users
        SET password={ph()}
        WHERE id={ph()}
        """,
        (
            generate_password_hash(new),
            user["id"]
        )
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True
    })


# =========================================================
# Admin Upload
# =========================================================

@app.route("/api/admin/upload", methods=["POST"])
@require_admin
def admin_upload(user):

    if "file" not in request.files:
        return jsonify({
            "error": "لا يوجد ملف"
        }), 400

    file = request.files["file"]

    if not file.filename:
        return jsonify({
            "error": "اسم فارغ"
        }), 400

    filename = secure_filename(
        file.filename
    )

    if not filename:
        return jsonify({
            "error": "اسم الملف غير صالح"
        }), 400

    extension = ""

    if "." in filename:
        extension = filename.rsplit(
            ".",
            1
        )[1].lower()

    new_name = (
        f"upload_"
        f"{int(time.time())}_"
        f"{secrets.token_hex(8)}"
    )

    if extension:
        new_name += "." + extension

    path = os.path.join(
        UPLOAD_DIR,
        new_name
    )

    file.save(path)

    return jsonify({
        "url": f"/uploads/{new_name}"
    })


@app.route("/uploads/<path:name>")
def serve_upload(name):

    return send_from_directory(
        UPLOAD_DIR,
        name
    )


# =========================================================
# VirusTotal
# =========================================================

def vt_headers():

    return {
        "x-apikey": VIRUSTOTAL_API_KEY
    }


def vt_url_id(url):

    return base64.urlsafe_b64encode(
        url.encode()
    ).decode().strip("=")


def vt_result(stats):

    malicious = int(
        stats.get("malicious", 0)
    )

    suspicious = int(
        stats.get("suspicious", 0)
    )

    harmless = int(
        stats.get("harmless", 0)
    )

    undetected = int(
        stats.get("undetected", 0)
    )

    if malicious > 0:
        status = "danger"

    elif suspicious > 0:
        status = "warning"

    else:
        status = "safe"

    return {
        "status": status,
        "malicious": malicious,
        "suspicious": suspicious,
        "harmless": harmless,
        "undetected": undetected,
        "total": (
            malicious
            + suspicious
            + harmless
            + undetected
        )
    }


# =========================================================
# VirusTotal Status
# =========================================================

@app.route("/api/scan/status", methods=["GET"])
def vt_status():

    return jsonify({
        "configured": bool(
            VIRUSTOTAL_API_KEY
        ),
        "message": (
            "VirusTotal جاهز"
            if VIRUSTOTAL_API_KEY
            else "مفتاح VirusTotal مفقود"
        )
    })


# =========================================================
# VirusTotal URL Scan
# =========================================================

@app.route("/api/scan/url", methods=["POST"])
def scan_url_real():

    data = request.get_json(silent=True) or {}

    url = (data.get("url") or "").strip()

    if not url:
        return jsonify({
            "error": "الرابط مطلوب"
        }), 400

    if len(url) > 2000:
        return jsonify({
            "error": "الرابط طويل جداً"
        }), 400

    if not re.match(
        r"^https?://",
        url,
        re.IGNORECASE
    ):
        return jsonify({
            "error": "الرابط يجب أن يبدأ بـ http أو https"
        }), 400

    if not VIRUSTOTAL_API_KEY:
        return jsonify({
            "error": "مفتاح VirusTotal مفقود"
        }), 500

    try:

        response = requests.post(
            VT_BASE + "/urls",
            headers=vt_headers(),
            data={
                "url": url
            },
            timeout=20
        )

        if response.status_code not in (200, 201):
            return jsonify({
                "error": "فشل إرسال الرابط إلى VirusTotal"
            }), 502

        url_id = vt_url_id(url)

        time.sleep(2)

        report = requests.get(
            VT_BASE + "/urls/" + url_id,
            headers=vt_headers(),
            timeout=20
        )

        if report.status_code != 200:
            return jsonify({
                "error": "التقرير غير جاهز"
            }), 202

        attributes = (
            report.json()
            .get("data", {})
            .get("attributes", {})
        )

        result = vt_result(
            attributes.get(
                "last_analysis_stats",
                {}
            )
        )

        result["url"] = url

        return jsonify(result)

    except requests.RequestException:

        return jsonify({
            "error": "تعذر الاتصال بـ VirusTotal"
        }), 502

    except Exception:

        return jsonify({
            "error": "حدث خطأ أثناء الفحص"
        }), 500


# =========================================================
# VirusTotal File Scan
# =========================================================

@app.route("/api/scan/file", methods=["POST"])
def scan_file_real():

    if "file" not in request.files:
        return jsonify({
            "error": "الملف مطلوب"
        }), 400

    if not VIRUSTOTAL_API_KEY:
        return jsonify({
            "error": "مفتاح VirusTotal مفقود"
        }), 500

    file = request.files["file"]

    if not file.filename:
        return jsonify({
            "error": "اسم الملف مفقود"
        }), 400

    try:

        file_bytes = file.read()

        if not file_bytes:
            return jsonify({
                "error": "الملف فارغ"
            }), 400

        if len(file_bytes) > MAX_FILE_SIZE:
            return jsonify({
                "error": "حجم الملف كبير جداً"
            }), 413

        sha256 = hashlib.sha256(
            file_bytes
        ).hexdigest()

        # ---------------------------------------------
        # Check existing VirusTotal report
        # ---------------------------------------------

        report = requests.get(
            VT_BASE + "/files/" + sha256,
            headers=vt_headers(),
            timeout=20
        )

        if report.status_code == 200:

            attributes = (
                report.json()
                .get("data", {})
                .get("attributes", {})
            )

            result = vt_result(
                attributes.get(
                    "last_analysis_stats",
                    {}
                )
            )

            result.update({
                "hash": sha256,
                "found_in_db": True
            })

            return jsonify(result)

        # ---------------------------------------------
        # Upload new file
        # ---------------------------------------------

        files = {
            "file": (
                secure_filename(
                    file.filename
                ) or "file",
                file_bytes
            )
        }

        upload = requests.post(
            VT_BASE + "/files",
            headers=vt_headers(),
            files=files,
            timeout=90
        )

        if upload.status_code not in (200, 201):
            return jsonify({
                "error": "فشل رفع الملف إلى VirusTotal"
            }), 502

        upload_data = upload.json()

        analysis_id = (
            upload_data
            .get("data", {})
            .get("id")
        )

        return jsonify({
            "status": "pending",
            "message": "تم رفع الملف وقيد التحليل",
            "hash": sha256,
            "analysis_id": analysis_id,
            "queued": True
        }), 202

    except requests.RequestException:

        return jsonify({
            "error": "تعذر الاتصال بـ VirusTotal"
        }), 502

    except Exception:

        return jsonify({
            "error": "حدث خطأ أثناء فحص الملف"
        }), 500


# =========================================================
# VirusTotal Analysis Polling
# =========================================================

@app.route(
    "/api/scan/analysis/<analysis_id>",
    methods=["GET"]
)
def vt_analysis_status(analysis_id):

    if not VIRUSTOTAL_API_KEY:
        return jsonify({
            "error": "مفتاح VirusTotal مفقود"
        }), 500

    if not re.match(
        r"^[A-Za-z0-9_-]+$",
        analysis_id
    ):
        return jsonify({
            "error": "معرف تحليل غير صالح"
        }), 400

    try:

        response = requests.get(
            VT_BASE + "/analyses/" + analysis_id,
            headers=vt_headers(),
            timeout=20
        )

        if response.status_code != 200:
            return jsonify({
                "error": "التحليل غير موجود"
            }), 404

        data = response.json().get(
            "data",
            {}
        )

        attributes = data.get(
            "attributes",
            {}
        )

        status = attributes.get(
            "status",
            "queued"
        )

        if status != "completed":

            return jsonify({
                "status": "pending",
                "analysis_status": status
            })

        stats = attributes.get(
            "stats",
            {}
        )

        result = vt_result(stats)

        result["analysis_status"] = "completed"

        return jsonify(result)

    except requests.RequestException:

        return jsonify({
            "error": "تعذر الاتصال بـ VirusTotal"
        }), 502

    except Exception:

        return jsonify({
            "error": "حدث خطأ أثناء الحصول على التقرير"
        }), 500


# =========================================================
# Email Scan
# =========================================================

@app.route("/api/scan/email", methods=["POST"])
def scan_email_real():

    data = request.get_json(silent=True) or {}

    body = (data.get("body") or "").strip()

    if not body:
        return jsonify({
            "error": "النص مطلوب"
        }), 400

    result = {
        "status": "safe",
        "issues": [],
        "summary": {},
        "url_results": []
    }

    urls = re.findall(
        r'https?://[^\s<>"\'\)\]\}]+',
        body,
        re.IGNORECASE
    )

    urls = [
        url.rstrip(".,;:!?")
        for url in urls
    ]

    urls = list(dict.fromkeys(urls))[:5]

    suspicious_words = [
        "verify",
        "urgent",
        "suspended",
        "confirm",
        "account",
        "login",
        "secure",
        "update",
        "password",
        "winner",
        "prize"
    ]

    lower_body = body.lower()

    found = [
        word
        for word in suspicious_words
        if word in lower_body
    ]

    if found:

        result["issues"].append({
            "level": "warn",
            "msg": (
                "كلمات قد تكون مرتبطة بالتصيد: "
                + ", ".join(found[:3])
            )
        })

        result["status"] = "warning"

    # -----------------------------------------------------
    # VirusTotal URL checks
    # -----------------------------------------------------

    if urls and VIRUSTOTAL_API_KEY:

        for url in urls:

            try:

                response = requests.post(
                    VT_BASE + "/urls",
                    headers=vt_headers(),
                    data={
                        "url": url
                    },
                    timeout=15
                )

                if response.status_code not in (
                    200,
                    201
                ):
                    continue

                url_id = vt_url_id(url)

                time.sleep(1.2)

                report = requests.get(
                    VT_BASE + "/urls/" + url_id,
                    headers=vt_headers(),
                    timeout=15
                )

                if report.status_code != 200:
                    continue

                attributes = (
                    report.json()
                    .get("data", {})
                    .get("attributes", {})
                )

                result_data = vt_result(
                    attributes.get(
                        "last_analysis_stats",
                        {}
                    )
                )

                result_data["url"] = url

                result["url_results"].append(
                    result_data
                )

                if result_data["status"] == "danger":
                    result["status"] = "danger"

                elif (
                    result_data["status"] == "warning"
                    and result["status"] != "danger"
                ):
                    result["status"] = "warning"

            except Exception:
                continue

    result["summary"] = {
        "total_urls": len(urls)
    }

    return jsonify(result)


# =========================================================
# Frontend
# =========================================================

@app.route("/")
def root():

    return send_from_directory(
        FRONTEND_DIR,
        "index.html"
    )


@app.route("/<path:path>")
def serve_front(path):

    full_path = os.path.join(
        FRONTEND_DIR,
        path
    )

    if os.path.isfile(full_path):

        return send_from_directory(
            FRONTEND_DIR,
            path
        )

    return send_from_directory(
        FRONTEND_DIR,
        "index.html"
    )


# =========================================================
# Error Handlers
# =========================================================

@app.errorhandler(413)
def file_too_large(error):

    return jsonify({
        "error": "حجم الملف يتجاوز الحد المسموح"
    }), 413


@app.errorhandler(404)
def not_found(error):

    if request.path.startswith("/api/"):

        return jsonify({
            "error": "API endpoint not found"
        }), 404

    return send_from_directory(
        FRONTEND_DIR,
        "index.html"
    )


@app.errorhandler(500)
def internal_error(error):

    return jsonify({
        "error": "خطأ داخلي في الخادم"
    }), 500


# =========================================================
# Run
# =========================================================

if __name__ == "__main__":

    init_db()

    port = int(
        os.environ.get(
            "PORT",
            8080
        )
    )

    print("=" * 50)
    print("ShieldScan Backend يعمل")
    print("=" * 50)
    print(
        f"Database: "
        f"{'PostgreSQL' if DATABASE_URL else 'SQLite'}"
    )
    print(
        f"VirusTotal: "
        f"{'Enabled' if VIRUSTOTAL_API_KEY else 'Disabled'}"
    )
    print("=" * 50)

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False
    )
