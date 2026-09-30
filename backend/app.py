from dotenv import load_dotenv
load_dotenv()
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3, os, jwt, time, re, secrets, requests, hashlib, base64
from datetime import datetime, timedelta
from functools import wraps

# ============ إعدادات ============
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'shieldscan.db')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
FRONTEND_DIR = os.path.dirname(BASE_DIR)
SECRET_KEY = 'shieldscan-secret-change-me-2025'
TOKEN_EXP_HOURS = 24

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, static_folder=None)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# ============ قاعدة البيانات ============
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS scans(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        type TEXT NOT NULL,
        target TEXT NOT NULL,
        status TEXT NOT NULL,
        details TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        subject TEXT,
        message TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings(
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS content(
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS design(
        key TEXT PRIMARY KEY,
        value TEXT
    )''')

    # حساب الأدمن الافتراضي
    c.execute("SELECT * FROM users WHERE email='admin@shieldscan.local'")
    if not c.fetchone():
        c.execute("INSERT INTO users(name,email,password,is_admin) VALUES(?,?,?,1)",
                  ('Admin', 'admin@shieldscan.local',
                   generate_password_hash('admin123')))

    # محتوى افتراضي
    defaults_content = {
        'heroPill': '⚡ مدعوم بمحركات فحص متعددة',
        'heroT1': 'افحص أي',
        'heroT2': 'قبل أن يفتحه أحد',
        'heroDesc': 'كشف فوري للفيروسات، التصيد الاحتيالي، والبرمجيات الخبيثة — مجاناً وبكل سهولة.',
        'tabUrl': '🔗 رابط',
        'tabFile': '📁 ملف',
        'btnUrl': '🔍 افحص الرابط',
        'btnFile': '🛡️ افحص الملف',
        'footCopy': '© 2025 ShieldScan — جميع الحقوق محفوظة',
        'brand1': 'Shield',
        'brand2': 'Scan'
    }
    for k, v in defaults_content.items():
        c.execute("INSERT OR IGNORE INTO content(key,value) VALUES(?,?)", (k, v))

    defaults_design = {
        'primary': '#6366f1',
        'secondary': '#8b5cf6',
        'accent': '#ec4899',
        'bg': '#f8fafc',
        'text': '#1e293b',
        'muted': '#64748b',
        'size': '100',
        'radius': '100'
    }
    for k, v in defaults_design.items():
        c.execute("INSERT OR IGNORE INTO design(key,value) VALUES(?,?)", (k, v))


    c.execute("""CREATE TABLE IF NOT EXISTS pages_content(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        page TEXT NOT NULL,
        section TEXT NOT NULL,
        key TEXT NOT NULL,
        value TEXT,
        type TEXT DEFAULT 'text',
        UNIQUE(page, section, key)
    )""")
    
    # بيانات افتراضية لكل الصفحات
    default_pages = [
        # ============ الرئيسية - Hero ============
        ('index', 'hero', 'pill', '⚡ مدعوم بمحركات فحص متعددة', 'text'),
        ('index', 'hero', 'title1', 'افحص أي رابط أو ملف', 'text'),
        ('index', 'hero', 'title2', 'قبل أن يفتحه أحد', 'text'),
        ('index', 'hero', 'desc', 'كشف فوري للفيروسات، التصيد الاحتيالي، والبرمجيات الخبيثة — مجاناً وبكل سهولة.', 'text'),
        
        # ============ الرئيسية - Scanner ============
        ('index', 'scanner', 'tabUrl', '🔗 رابط', 'text'),
        ('index', 'scanner', 'tabFile', '📁 ملف', 'text'),
        ('index', 'scanner', 'tabEmail', '📧 بريد إلكتروني', 'text'),
        ('index', 'scanner', 'urlPlaceholder', 'الصق الرابط هنا… https://example.com', 'text'),
        ('index', 'scanner', 'btnUrl', '🔍 افحص الرابط', 'text'),
        ('index', 'scanner', 'btnFile', '🛡️ افحص الملف', 'text'),
        ('index', 'scanner', 'btnEmail', '📧 افحص البريد', 'text'),
        ('index', 'scanner', 'dropText', 'اسحب الملف هنا أو اضغط للاختيار', 'text'),
        ('index', 'scanner', 'dropLimit', 'الحجم الأقصى: 50 ميجابايت', 'text'),
        ('index', 'scanner', 'emailPlaceholder', '📩 الصق نص الرسالة هنا…', 'text'),
        
        # ============ الرئيسية - Quick Cards ============
        ('index', 'quick', 'pill', 'استكشف', 'text'),
        ('index', 'quick', 'title', 'تعرّف على ShieldScan', 'text'),
        ('index', 'quick', 'q1Title', 'المميزات', 'text'),
        ('index', 'quick', 'q1Desc', 'اكتشف كل ما يقدمه ShieldScan لحمايتك', 'text'),
        ('index', 'quick', 'q2Title', 'الأسئلة الشائعة', 'text'),
        ('index', 'quick', 'q2Desc', 'أجوبة لأكثر الأسئلة تكراراً', 'text'),
        ('index', 'quick', 'q3Title', 'اتصل بنا', 'text'),
        ('index', 'quick', 'q3Desc', 'تواصل معنا لأي استفسار أو اقتراح', 'text'),
        ('index', 'quick', 'q4Title', 'سياسة الخصوصية', 'text'),
        ('index', 'quick', 'q4Desc', 'كيف نحمي بياناتك ونحافظ على خصوصيتك', 'text'),
        
        # ============ الرئيسية - CTA ============
        ('index', 'cta', 'title', 'جاهز لفحص أول رابط؟', 'text'),
        ('index', 'cta', 'desc', 'ابدأ الآن مجاناً وبكل سهولة', 'text'),
        ('index', 'cta', 'btn', '🚀 ابدأ الفحص', 'text'),
        
        # ============ المميزات ============
        ('features', 'hero', 'pill', '✨ المميزات', 'text'),
        ('features', 'hero', 'title', 'كل ما يقدمه ShieldScan', 'text'),
        ('features', 'hero', 'desc', 'مجموعة كاملة من الأدوات لحمايتك من التهديدات الإلكترونية', 'text'),
        ('features', 'f1', 'icon', '⚡', 'text'),
        ('features', 'f1', 'title', 'سرعة فائقة', 'text'),
        ('features', 'f1', 'desc', 'نتائج خلال ثوانٍ بفضل محركات متعددة متوازية تعمل في نفس الوقت.', 'text'),
        ('features', 'f2', 'icon', '🔒', 'text'),
        ('features', 'f2', 'title', 'خصوصية تامة', 'text'),
        ('features', 'f2', 'desc', 'لا نخزّن أي ملف أو رابط تفحصه إطلاقاً. كل عملية الفحص مؤقتة بالكامل.', 'text'),
        ('features', 'f3', 'icon', '🛡️', 'text'),
        ('features', 'f3', 'title', 'كشف متقدم للتصيد', 'text'),
        ('features', 'f3', 'desc', 'تقنيات ذكية لكشف المواقع المزيفة والاحتيالية التي تحاول سرقة بياناتك.', 'text'),
        ('features', 'f4', 'icon', '📊', 'text'),
        ('features', 'f4', 'title', 'تقارير واضحة', 'text'),
        ('features', 'f4', 'desc', 'نتائج مفصّلة سهلة الفهم لكل تهديد مع توصيات واضحة للحماية.', 'text'),
        ('features', 'f5', 'icon', '🆓', 'text'),
        ('features', 'f5', 'title', 'مجاني بالكامل', 'text'),
        ('features', 'f5', 'desc', 'جميع الميزات متاحة بدون أي رسوم أو اشتراكات مخفية.', 'text'),
        ('features', 'f6', 'icon', '🌙', 'text'),
        ('features', 'f6', 'title', 'وضع ليلي', 'text'),
        ('features', 'f6', 'desc', 'تصفح مريح للعين في أي وقت من اليوم مع تبديل فوري.', 'text'),
        ('features', 'f7', 'icon', '📱', 'text'),
        ('features', 'f7', 'title', 'متجاوب مع الجوال', 'text'),
        ('features', 'f7', 'desc', 'يعمل بسلاسة على الجوال والتابلت والحاسوب بأي حجم شاشة.', 'text'),
        ('features', 'f8', 'icon', '🚀', 'text'),
        ('features', 'f8', 'title', 'بدون تسجيل إلزامي', 'text'),
        ('features', 'f8', 'desc', 'افحص أي رابط أو ملف مباشرة بدون الحاجة لإنشاء حساب.', 'text'),
        ('features', 'f9', 'icon', '🔄', 'text'),
        ('features', 'f9', 'title', 'تحديثات مستمرة', 'text'),
        ('features', 'f9', 'desc', 'قواعد بيانات محدّثة على مدار الساعة لكشف أحدث التهديدات.', 'text'),
        
        # ============ الأسئلة الشائعة ============
        ('faq', 'hero', 'pill', '❓ الأسئلة الشائعة', 'text'),
        ('faq', 'hero', 'title', 'لديك سؤال؟', 'text'),
        ('faq', 'hero', 'desc', 'جمعنا لك أجوبة أكثر الأسئلة تكراراً', 'text'),
        ('faq', 'q1', 'question', 'هل الموقع مجاني بالكامل؟', 'text'),
        ('faq', 'q1', 'answer', 'نعم، جميع المميزات مجانية 100% بدون أي رسوم أو اشتراكات مخفية.', 'text'),
        ('faq', 'q2', 'question', 'هل تخزّنون ملفاتي أو روابطي؟', 'text'),
        ('faq', 'q2', 'answer', 'لا. لا نخزّن أي ملف أو رابط. جميع عمليات الفحص مؤقتة ويتم حذفها فوراً بعد الانتهاء.', 'text'),
        ('faq', 'q3', 'question', 'ما أنواع الملفات المدعومة؟', 'text'),
        ('faq', 'q3', 'answer', 'ندعم جميع أنواع الملفات: التنفيذية (exe)، المضغوطة (zip, rar)، المستندات (pdf, docx)، التطبيقات (apk)، الصور وغيرها.', 'text'),
        ('faq', 'q4', 'question', 'كم يستغرق الفحص؟', 'text'),
        ('faq', 'q4', 'answer', 'عادة من 3 إلى 15 ثانية حسب حجم الملف وعدد المحركات المستخدمة في الفحص.', 'text'),
        ('faq', 'q5', 'question', 'هل أحتاج حساب للفحص؟', 'text'),
        ('faq', 'q5', 'answer', 'نعم، تحتاج تسجيل الدخول لاستخدام ميزة الفحص. التسجيل مجاني وسريع.', 'text'),
        ('faq', 'q6', 'question', 'ماذا يعني "تهديد مكتشف"؟', 'text'),
        ('faq', 'q6', 'answer', 'يعني أن الرابط أو الملف يحتوي على مؤشرات خطر مثل فيروسات، تصيد احتيالي، أو كود ضار.', 'text'),
        
        # ============ اتصل بنا ============
        ('contact', 'hero', 'pill', '📞 اتصل بنا', 'text'),
        ('contact', 'hero', 'title', 'كيف يمكننا مساعدتك؟', 'text'),
        ('contact', 'hero', 'desc', 'تواصل معنا لأي استفسار أو اقتراح أو مشكلة', 'text'),
        ('contact', 'info', 'title', 'معلومات التواصل', 'text'),
        ('contact', 'info', 'email1Label', 'البريد الإلكتروني', 'text'),
        ('contact', 'info', 'email1Value', 'support@shieldscan.com', 'text'),
        ('contact', 'info', 'email2Label', 'الدعم الفني', 'text'),
        ('contact', 'info', 'email2Value', 'help@shieldscan.com', 'text'),
        ('contact', 'info', 'locationLabel', 'الموقع', 'text'),
        ('contact', 'info', 'locationValue', 'متاح عالمياً 24/7', 'text'),
        ('contact', 'info', 'responseLabel', 'وقت الاستجابة', 'text'),
        ('contact', 'info', 'responseValue', 'خلال 24 ساعة', 'text'),
        
        # ============ الخصوصية ============
        ('privacy', 'hero', 'pill', '🔒 سياسة الخصوصية', 'text'),
        ('privacy', 'hero', 'title', 'خصوصيتك أولويتنا', 'text'),
        ('privacy', 'hero', 'desc', 'آخر تحديث: يناير 2026', 'text'),
        ('privacy', 's1', 'title', '🛡️ مقدمة', 'text'),
        ('privacy', 's1', 'content', 'في ShieldScan، نأخذ خصوصيتك على محمل الجد. توضح هذه السياسة كيفية تعاملنا مع بياناتك عند استخدام خدماتنا.', 'text'),
        ('privacy', 's2', 'title', '📊 البيانات التي نجمعها', 'text'),
        ('privacy', 's2', 'content', 'بيانات الحساب: الاسم والبريد الإلكتروني (فقط عند التسجيل)\nبيانات الفحص: تتم محلياً في متصفحك ولا تُرسل لأي سيرفر\nلا نجمع: ملفاتك، روابطك المفحوصة، عنوان IP', 'textarea'),
        ('privacy', 's3', 'title', '🔐 كيف نحمي بياناتك', 'text'),
        ('privacy', 's3', 'content', 'جميع عمليات الفحص تتم في متصفحك بدون رفع للملفات\nكلمات المرور تُخزّن مشفرة\nلا نشارك بياناتك مع أي طرف ثالث', 'textarea'),
        
        # ============ الفوتر ============
        ('footer', 'main', 'desc', 'منصتك الآمنة لفحص الروابط والملفات من الفيروسات والتهديدات الإلكترونية.', 'text'),
        ('footer', 'main', 'copyright', '© 2026 ShieldScan — جميع الحقوق محفوظة', 'text'),
        ('footer', 'links', 'title1', 'روابط', 'text'),
        ('footer', 'links', 'title2', 'المزيد', 'text'),
        
        # ============ الهوية ============
        ('brand', 'main', 'name1', 'Shield', 'text'),
        ('brand', 'main', 'name2', 'Scan', 'text'),
        ('brand', 'main', 'logo', '🛡️', 'text'),
    ]
    
    for page, section, key, value, type_ in default_pages:
        try:
            c.execute("INSERT OR IGNORE INTO pages_content(page,section,key,value,type) VALUES(?,?,?,?,?)",
                      (page, section, key, value, type_))
        except:
            pass
    conn.commit()
    conn.close()

# ============ JWT ============
def make_token(user):
    payload = {
        'user_id': user['id'],
        'email': user['email'],
        'is_admin': user['is_admin'],
        'exp': datetime.utcnow() + timedelta(hours=TOKEN_EXP_HOURS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def get_token_user():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return None
    token = auth[7:]
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE id=?", (data['user_id'],)).fetchone()
        conn.close()
        return user
    except Exception:
        return None

def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        u = get_token_user()
        if not u:
            return jsonify({'error': 'Unauthorized'}), 401
        if u['is_banned']:
            return jsonify({'error': 'Account banned'}), 403
        return f(u, *args, **kwargs)
    return wrapper

def require_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        u = get_token_user()
        if not u:
            return jsonify({'error': 'Unauthorized'}), 401
        if not u['is_admin']:
            return jsonify({'error': 'Admin only'}), 403
        return f(u, *args, **kwargs)
    return wrapper

# ============ API: Auth ============

# ============ Email Validation ============
import re

TEMP_DOMAINS = {
    'mailinator.com','guerrillamail.com','10minutemail.com','tempmail.com',
    'throwaway.email','yopmail.com','sharklasers.com','trashmail.com',
    'getnada.com','dispostable.com','fakeinbox.com','maildrop.cc',
    'temp-mail.org','mailnesia.com','spam4.me','guerrillamail.org'
}

TYPOS = {
    'gmal.com':'gmail.com','gmial.com':'gmail.com','gmai.com':'gmail.com',
    'gmail.co':'gmail.com','gmail.con':'gmail.com','gmail.cm':'gmail.com',
    'gmaill.com':'gmail.com','yaho.com':'yahoo.com','yahooo.com':'yahoo.com',
    'hotmal.com':'hotmail.com','hotmai.com':'hotmail.com',
    'outlok.com':'outlook.com','outloo.com':'outlook.com'
}

def is_real_email(email):
    email = (email or '').strip().lower()
    if not re.match(r'^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$', email):
        return False, 'صيغة بريد غير صالحة'
    domain = email.split('@')[1]
    if domain in TEMP_DOMAINS:
        return False, 'لا يمكن التسجيل ببريد مؤقت'
    if domain in TYPOS:
        return False, f'النطاق غير صحيح (ربما تقصد {TYPOS[domain]}؟)'
    return True, ''


# ============================================================
#                    SECURITY LAYER
# ============================================================
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
import bleach, ipaddress, urllib.parse, secrets, threading
from collections import defaultdict

# ============ [A07] Rate Limiting & IP Ban ============
MAX_FAILED_ATTEMPTS = 10
BAN_DURATION = 3600

failed_logins = defaultdict(list)
banned_ips = {}
lock = threading.Lock()

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    if request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    return request.remote_addr or '0.0.0.0'

def is_banned(ip):
    with lock:
        if ip in banned_ips:
            if time.time() < banned_ips[ip]:
                return True
            else:
                del banned_ips[ip]
        return False

def is_rate_limited(ip):
    now = time.time()
    with lock:
        failed_logins[ip] = [t for t in failed_logins[ip] if now - t < BAN_DURATION]
        count = len(failed_logins[ip])
        if count >= MAX_FAILED_ATTEMPTS:
            banned_ips[ip] = now + BAN_DURATION
            failed_logins[ip] = []
            return True
        return False

def record_failure(ip):
    with lock:
        failed_logins[ip].append(time.time())
        return len(failed_logins[ip])

def clear_failures(ip):
    with lock:
        failed_logins[ip] = []
        if ip in banned_ips:
            del banned_ips[ip]

# ============ [A03] XSS Protection ============
ALLOWED_TAGS = []
ALLOWED_ATTRS = {}

def sanitize_html(text, max_len=5000):
    if not isinstance(text, str):
        return ''
    cleaned = bleach.clean(text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)
    return cleaned[:max_len]

def contains_xss(text):
    if not isinstance(text, str):
        return False
    patterns = [
        r'<script', r'javascript:', r'on\w+\s*=', r'<iframe',
        r'<object', r'<embed', r'eval\s*\(', r'expression\s*\(',
        r'<svg', r'<img[^>]*onerror'
    ]
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False

# ============ [A10] SSRF Protection ============
BLOCKED_HOSTS = {
    'localhost', '127.0.0.1', '0.0.0.0', '::1',
    'metadata.google.internal', 'metadata',
    '169.254.169.254', '169.254.170.2',
}

def is_safe_url(url):
    if not url or not isinstance(url, str):
        return False, 'URL فارغ'
    if len(url) > 2000:
        return False, 'URL طويل جداً'
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return False, 'URL غير صالح'
    if parsed.scheme not in ('http', 'https'):
        return False, 'البروتوكول غير مسموح'
    host = parsed.hostname
    if not host:
        return False, 'لا يوجد مضيف'
    host_lower = host.lower()
    if host_lower in BLOCKED_HOSTS:
        return False, 'النطاق محظور'
    try:
        ip = ipaddress.ip_address(host_lower)
        if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
            return False, 'عنوان IP داخلي محظور'
    except ValueError:
        pass
    if any(host_lower.endswith('.' + h) for h in BLOCKED_HOSTS):
        return False, 'نطاق فرعي محظور'
    return True, 'OK'

# ============ [A03] Path Traversal ============
def is_safe_filename(filename):
    if not filename:
        return False
    dangerous = ['..', '/', '\\', '\x00', '%2e%2e', '....', '~', '\n', '\r']
    return not any(d in filename for d in dangerous)

# ============ [A04] File Upload ============
ALLOWED_EXTENSIONS = {
    'pdf','doc','docx','xls','xlsx','ppt','pptx','txt','csv',
    'jpg','jpeg','png','gif','webp','svg','bmp',
    'zip','rar','7z','tar','gz',
    'exe','apk','dmg','deb','rpm','msi',
    'html','htm','js','css','json','xml','md'
}

DANGEROUS_EXTENSIONS = {
    'php','phtml','php3','php4','php5','phar',
    'jsp','asp','aspx','cgi','pl','py','rb','sh',
    'bat','cmd','com','scr','vbs','ps1','psm1'
}

MAX_FILE_SIZE = 50 * 1024 * 1024

def is_safe_file(file):
    if not file or not file.filename:
        return False, 'لا يوجد ملف'
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_FILE_SIZE:
        return False, 'حجم الملف كبير جداً'
    if size == 0:
        return False, 'الملف فارغ'
    filename = file.filename
    if not is_safe_filename(filename):
        return False, 'اسم ملف غير آمن'
    if len(filename) > 255:
        return False, 'اسم الملف طويل جداً'
    if '.' not in filename:
        return False, 'الملف بدون امتداد'
    ext = filename.rsplit('.', 1)[1].lower()
    if ext in DANGEROUS_EXTENSIONS:
        return False, 'نوع الملف محظور'
    if ext not in ALLOWED_EXTENSIONS:
        return False, 'نوع الملف غير مسموح'
    return True, 'OK'

# ============ [A05] Security Headers ============
Talisman(
    app,
    force_https=False,
    frame_options='SAMEORIGIN',
    content_security_policy={
        'default-src': ["'self'"],
        'script-src': ["'self'", "'unsafe-inline'", 'https://fonts.googleapis.com'],
        'style-src': ["'self'", "'unsafe-inline'", 'https://fonts.googleapis.com'],
        'font-src': ["'self'", 'https://fonts.gstatic.com', 'data:'],
        'img-src': ["'self'", 'data:', 'https:'],
        'connect-src': ["'self'"],
    }
)

# ============ [A07] Rate Limiter ============
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["2000 per day", "300 per hour"],
    storage_uri="memory://"
)

# ============ CORS ============
ALLOWED_ORIGINS = ['http://localhost:8080', 'http://127.0.0.1:8080']

@app.after_request
def apply_cors(response):
    origin = request.headers.get('Origin')
    if origin in ALLOWED_ORIGINS:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

# ============ [A09] Security Logging ============
security_log = []
security_log_lock = threading.Lock()

def log_security(event, details, ip=None):
    with security_log_lock:
        security_log.append({
            'event': event,
            'details': details,
            'ip': ip or get_client_ip(),
            'time': datetime.utcnow().isoformat()
        })
        if len(security_log) > 1000:
            security_log.pop(0)

# ============ Global Guard ============
@app.before_request
def security_guard():
    ip = get_client_ip()
    if is_banned(ip):
        remaining = int((banned_ips.get(ip, 0) - time.time()) / 60)
        return jsonify({'error': f'تم حظر IP مؤقتاً — جرب بعد {remaining} دقيقة'}), 429
    if request.method in ('POST', 'PUT', 'PATCH'):
        if request.is_json:
            try:
                data = request.get_json(silent=True)
                if data and isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, str) and contains_xss(value):
                            log_security('XSS_ATTEMPT', {'field': key, 'value': value[:100]})
                            return jsonify({'error': 'مدخلات غير صالحة'}), 400
            except Exception:
                pass
    return None

@app.route('/api/auth/register', methods=['POST'])
@limiter.limit("5 per hour")
def register():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if len(name) < 3:
        return jsonify({'error': 'الاسم قصير جداً'}), 400
    valid, err = is_real_email(email)
    if not valid:
        return jsonify({'error': err}), 400
    if len(password) < 6:
        return jsonify({'error': 'كلمة المرور قصيرة'}), 400

    conn = get_db()
    try:
        conn.execute("INSERT INTO users(name,email,password) VALUES(?,?,?)",
                     (name, email, generate_password_hash(password)))
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        token = make_token(user)
        conn.close()
        return jsonify({
            'token': token,
            'user': {'id': user['id'], 'name': user['name'],
                     'email': user['email'], 'is_admin': bool(user['is_admin'])}
        }), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'البريد مسجل مسبقاً'}), 409

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("20 per minute")
def login():
    ip = get_client_ip()

    if is_banned(ip):
        remaining = int((banned_ips.get(ip, 0) - time.time()) / 60)
        return jsonify({'error': f'محظور مؤقتاً — جرب بعد {remaining} دقيقة'}), 429

    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({'error': 'البريد وكلمة المرور مطلوبان'}), 400
    if len(email) > 254 or len(password) > 200:
        return jsonify({'error': 'مدخلات طويلة جداً'}), 400

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()

    if not user or not check_password_hash(user['password'], password):
        count = record_failure(ip)
        remaining = MAX_FAILED_ATTEMPTS - count
        log_security('LOGIN_FAILED', {'email': email, 'attempt': count}, ip)

        if count >= MAX_FAILED_ATTEMPTS:
            log_security('IP_BANNED', {'reason': 'too many failed logins'}, ip)
            return jsonify({
                'error': f'تم حظر IP بعد {MAX_FAILED_ATTEMPTS} محاولات فاشلة — جرب بعد ساعة'
            }), 429

        return jsonify({
            'error': f'بيانات غير صحيحة — تبقّى {remaining} محاولة'
        }), 401

    if user['is_banned']:
        return jsonify({'error': 'هذا الحساب محظور'}), 403

    clear_failures(ip)
    log_security('LOGIN_SUCCESS', {'email': email}, ip)

    token = make_token(user)
    return jsonify({
        'token': token,
        'user': {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'is_admin': bool(user['is_admin'])
        }
    })

@app.route('/api/auth/me', methods=['GET'])
@require_auth
def me(u):
    return jsonify({'user': {'id': u['id'], 'name': u['name'],
                             'email': u['email'], 'is_admin': bool(u['is_admin'])}})



# ============ VirusTotal ============
VT_API_KEY = os.environ.get('VT_API_KEY', '')
VT_BASE = 'https://www.virustotal.com/api/v3'

def vt_headers():
    return {'x-apikey': VT_API_KEY}

@app.route('/api/scan/status', methods=['GET'])
def vt_status():
    return jsonify({
        'configured': bool(VT_API_KEY),
        'message': 'VirusTotal جاهز ✅' if VT_API_KEY else 'مفتاح مفقود'
    })

@app.route('/api/scan/url', methods=['POST'])
@limiter.limit("30 per hour")
def scan_url_real():
    data = request.get_json() or {}
    url = (data.get('url') or '').strip()
    if not url:
        return jsonify({'error': 'الرابط مطلوب'}), 400
    if len(url) > 2000:
        return jsonify({'error': 'الرابط طويل جداً'}), 400
    safe, reason = is_safe_url(url)
    if not safe:
        return jsonify({'error': 'الرابط غير مسموح: ' + reason}), 400
    if not VT_API_KEY:
        return jsonify({'error': 'مفتاح VirusTotal غير مُعد'}), 500
    try:
        r = requests.post(VT_BASE + '/urls', headers=vt_headers(),
                          data={'url': url}, timeout=20)
        if r.status_code != 200:
            return jsonify({'error': f'VirusTotal: {r.status_code}'}), 500
        url_id = base64.urlsafe_b64encode(url.encode()).decode().strip('=')
        time.sleep(2)
        r2 = requests.get(VT_BASE + '/urls/' + url_id,
                          headers=vt_headers(), timeout=20)
        if r2.status_code != 200:
            return jsonify({'error': 'فشل جلب التقرير'}), 500
        d = r2.json().get('data', {}).get('attributes', {})
        s = d.get('last_analysis_stats', {})
        m = s.get('malicious', 0)
        su = s.get('suspicious', 0)
        h = s.get('harmless', 0)
        u = s.get('undetected', 0)
        status = 'danger' if m > 0 else ('warning' if su > 0 else 'safe')
        return jsonify({
            'status': status, 'malicious': m, 'suspicious': su,
            'harmless': h, 'undetected': u, 'total': m+su+h+u
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scan/file', methods=['POST'])
@limiter.limit("20 per hour")
def scan_file_real():
    if 'file' not in request.files:
        return jsonify({'error': 'الملف مطلوب'}), 400
    if not VT_API_KEY:
        return jsonify({'error': 'مفتاح VirusTotal غير مُعد'}), 500
    f = request.files['file']
    safe, reason = is_safe_file(f)
    if not safe:
        return jsonify({'error': 'الملف غير مسموح: ' + reason}), 400
    fb = f.read()
    try:
        h = hashlib.sha256(fb).hexdigest()
        r = requests.get(VT_BASE + '/files/' + h,
                         headers=vt_headers(), timeout=20)
        if r.status_code == 200:
            d = r.json().get('data', {}).get('attributes', {})
            s = d.get('last_analysis_stats', {})
            m = s.get('malicious', 0)
            su = s.get('suspicious', 0)
            ha = s.get('harmless', 0)
            u = s.get('undetected', 0)
            status = 'danger' if m > 0 else ('warning' if su > 0 else 'safe')
            return jsonify({
                'status': status, 'malicious': m, 'suspicious': su,
                'harmless': ha, 'undetected': u,
                'total': m+su+ha+u, 'hash': h, 'found_in_db': True
            })
        files = {'file': (f.filename or 'file', fb)}
        r2 = requests.post(VT_BASE + '/files', headers=vt_headers(),
                           files=files, timeout=90)
        if r2.status_code != 200:
            return jsonify({'error': f'فشل الرفع: {r2.status_code}'}), 500
        return jsonify({
            'status': 'warning', 'message': 'تم رفع الملف — قيد الفحص',
            'hash': h, 'queued': True
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ نهاية VirusTotal ============


# ============ Email Body Scanner ============
import re as _re

@app.route('/api/scan/email', methods=['POST'])
@limiter.limit("30 per hour")
def scan_email_real():
    data = request.get_json() or {}
    body = (data.get('body') or '').strip()

    if not body:
        return jsonify({'error': 'النص مطلوب'}), 400

    result = {
        'status': 'safe',
        'issues': [],
        'summary': {'total_urls': 0, 'danger_urls': 0, 'warning_urls': 0, 'safe_urls': 0},
        'url_results': []
    }

    # 1. استخراج الروابط
    urls = _re.findall(r'https?://[^\s<>"\'\)\]\}]+', body, _re.IGNORECASE)
    urls = [u.rstrip('.,;:!?') for u in urls]
    urls = list(dict.fromkeys(urls))

    # 2. كلمات مشبوهة
    suspicious = ['verify','urgent','suspended','click here','confirm','account',
                  'login','secure','update','password','winner','prize','claim','free']
    found = [w for w in suspicious if w in body.lower()]
    if found:
        result['issues'].append({'level':'warn','msg':'يحتوي على كلمات تصيد: ' + ', '.join(found[:3])})
        if result['status'] == 'safe':
            result['status'] = 'warning'

    # 3. فحص كل رابط
    if urls and VT_API_KEY:
        for url in urls[:5]:
            try:
                r = requests.post(VT_BASE + '/urls', headers=vt_headers(),
                                  data={'url':url}, timeout=15)
                if r.status_code != 200:
                    result['url_results'].append({'url':url,'status':'error'})
                    continue
                uid = base64.urlsafe_b64encode(url.encode()).decode().strip('=')
                time.sleep(1.2)
                r2 = requests.get(VT_BASE + '/urls/' + uid, headers=vt_headers(), timeout=15)
                if r2.status_code != 200:
                    result['url_results'].append({'url':url,'status':'error'})
                    continue
                d = r2.json().get('data',{}).get('attributes',{})
                s = d.get('last_analysis_stats',{})
                m = s.get('malicious',0); su = s.get('suspicious',0)
                st = 'danger' if m > 0 else ('warning' if su > 0 else 'safe')
                result['url_results'].append({'url':url,'status':st,'malicious':m,'suspicious':su})
                if st == 'danger':
                    result['status'] = 'danger'
                elif st == 'warning' and result['status'] == 'safe':
                    result['status'] = 'warning'
            except Exception:
                result['url_results'].append({'url':url,'status':'error'})

    # 4. الملخص
    result['summary']['total_urls'] = len(urls)
    result['summary']['danger_urls'] = len([u for u in result['url_results'] if u.get('status')=='danger'])
    result['summary']['warning_urls'] = len([u for u in result['url_results'] if u.get('status')=='warning'])
    result['summary']['safe_urls'] = len([u for u in result['url_results'] if u.get('status')=='safe'])

    return jsonify(result)


# ============ Pages Content API ============
@app.route('/api/admin/pages/reset', methods=['POST'])
@require_admin
def reset_pages(u):
    """إعادة الصفحات للافتراضي"""
    conn = get_db()
    conn.execute("DELETE FROM pages_content")
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'أعد تشغيل السيرفر لإعادة التهيئة'})

# ============ API: Scans ============
@app.route('/api/scans', methods=['POST'])
def create_scan():
    data = request.get_json() or {}
    type_ = data.get('type')
    target = (data.get('target') or '').strip()
    status = data.get('status', 'safe')
    details = data.get('details', '')

    if type_ not in ('url', 'file', 'ip', 'email') or not target:
        return jsonify({'error': 'بيانات ناقصة'}), 400

    u = get_token_user()
    user_id = u['id'] if u else None

    conn = get_db()
    conn.execute("INSERT INTO scans(user_id,type,target,status,details) VALUES(?,?,?,?,?)",
                 (user_id, type_, target, status, details))
    conn.commit()
    conn.close()
    return jsonify({'success': True}), 201

@app.route('/api/scans', methods=['GET'])
@require_auth
def my_scans(u):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM scans WHERE user_id=? ORDER BY id DESC LIMIT 100",
        (u['id'],)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/scans/clear', methods=['DELETE'])
@require_auth
def clear_my_scans(u):
    conn=get_db(); conn.execute("DELETE FROM scans WHERE user_id=?",(u['id'],)); conn.commit(); conn.close()
    return jsonify({'success':True})

@app.route('/api/scans/<int:scan_id>', methods=['DELETE'])
@require_auth
def delete_my_scan(u, scan_id):
    conn=get_db()
    r=conn.execute("DELETE FROM scans WHERE id=? AND user_id=?",(scan_id,u['id']))
    conn.commit(); conn.close()
    return jsonify({'success':True}) if r.rowcount else (jsonify({'error':'not found'}),404)

# ============ API: Messages ============
@app.route('/api/messages', methods=['POST'])
@limiter.limit("5 per hour")
def create_message():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    subject = (data.get('subject') or '').strip()
    message = (data.get('message') or '').strip()

    if len(name) < 3 or '@' not in email or len(message) < 10:
        return jsonify({'error': 'بيانات غير مكتملة'}), 400

    name = sanitize_html(name, 100)
    email = sanitize_html(email, 254)
    subject = sanitize_html(subject, 200)
    message = sanitize_html(message, 5000)

    conn = get_db()
    conn.execute("INSERT INTO messages(name,email,subject,message) VALUES(?,?,?,?)",
                 (name, email, subject, message))
    conn.commit()
    conn.close()
    return jsonify({'success': True}), 201

# ============ API: Content & Design ============
@app.route('/api/content', methods=['GET'])
def get_content():
    conn = get_db()
    rows = conn.execute("SELECT key,value FROM content").fetchall()
    conn.close()
    return jsonify({r['key']: r['value'] for r in rows})

@app.route('/api/design', methods=['GET'])
def get_design():
    conn = get_db()
    rows = conn.execute("SELECT key,value FROM design").fetchall()
    conn.close()
    return jsonify({r['key']: r['value'] for r in rows})

# ============ API: Admin ============
@app.route('/api/admin/stats', methods=['GET'])
@require_admin
def admin_stats(u):
    conn = get_db()
    total_users = conn.execute("SELECT COUNT(*) c FROM users").fetchone()['c']
    total_scans = conn.execute("SELECT COUNT(*) c FROM scans").fetchone()['c']
    url_scans = conn.execute("SELECT COUNT(*) c FROM scans WHERE type='url'").fetchone()['c']
    file_scans = conn.execute("SELECT COUNT(*) c FROM scans WHERE type='file'").fetchone()['c']
    email_scans = conn.execute("SELECT COUNT(*) c FROM scans WHERE type='email'").fetchone()['c']
    threats = conn.execute("SELECT COUNT(*) c FROM scans WHERE status IN ('danger','warning')").fetchone()['c']
    msgs = conn.execute("SELECT COUNT(*) c FROM messages").fetchone()['c']
    conn.close()
    return jsonify({
        'users': total_users, 'scans': total_scans,
        'url_scans': url_scans, 'file_scans': file_scans,
        'email_scans': email_scans,
        'threats': threats, 'messages': msgs
    })

@app.route('/api/admin/scans', methods=['GET'])
@require_admin
def admin_scans(u):
    conn = get_db()
    rows = conn.execute("SELECT * FROM scans ORDER BY id DESC LIMIT 500").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/admin/scans/clear', methods=['DELETE'])
@require_admin
def admin_clear_scans(u):
    conn = get_db()
    conn.execute("DELETE FROM scans")
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/admin/users', methods=['GET'])
@require_admin
def admin_users(u):
    conn = get_db()
    rows = conn.execute("SELECT id,name,email,is_admin,is_banned,created_at FROM users ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/admin/users/<int:uid>', methods=['DELETE'])
@require_admin
def admin_del_user(u, uid):
    # لا يمكن حذف النفس
    if uid == u['id']:
        return jsonify({'error': 'لا يمكنك حذف حسابك الحالي — أنشئ أدمن آخر أولاً'}), 400

    conn = get_db()
    target = conn.execute("SELECT id, email, is_admin FROM users WHERE id=?", (uid,)).fetchone()
    if not target:
        conn.close()
        return jsonify({'error': 'المستخدم غير موجود'}), 404

    # حماية: لا تحذف آخر أدمن
    if target['is_admin']:
        admins_count = conn.execute("SELECT COUNT(*) c FROM users WHERE is_admin=1").fetchone()['c']
        if admins_count <= 1:
            conn.close()
            return jsonify({'error': 'لا يمكن حذف آخر أدمن في النظام'}), 400

    conn.execute("DELETE FROM users WHERE id=?", (uid,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/admin/users/<int:uid>/ban', methods=['POST'])
@require_admin
def admin_ban_user(u, uid):
    if uid == u['id']:
        return jsonify({'error': 'لا يمكنك حظر نفسك'}), 400
    conn = get_db()
    conn.execute("UPDATE users SET is_banned=1-is_banned WHERE id=?", (uid,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/admin/messages', methods=['GET'])
@require_admin
def admin_messages(u):
    conn = get_db()
    rows = conn.execute("SELECT * FROM messages ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/admin/messages/clear', methods=['DELETE'])
@require_admin
def admin_clear_messages(u):
    conn = get_db()
    conn.execute("DELETE FROM messages")
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/admin/content', methods=['POST'])
@require_admin
def admin_update_content(u):
    data = request.get_json() or {}
    conn = get_db()
    for k, v in data.items():
        conn.execute("INSERT INTO content(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                     (k, str(v)))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/admin/design', methods=['POST'])
@require_admin
def admin_update_design(u):
    data = request.get_json() or {}
    conn = get_db()
    for k, v in data.items():
        conn.execute("INSERT INTO design(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                     (k, str(v)))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/admin/change-password', methods=['POST'])
@require_admin
def admin_change_password(u):
    data = request.get_json() or {}
    old = data.get('old') or ''
    new = data.get('new') or ''
    if len(new) < 6:
        return jsonify({'error': 'كلمة المرور الجديدة قصيرة'}), 400
    if not check_password_hash(u['password'], old):
        return jsonify({'error': 'كلمة المرور الحالية خاطئة'}), 400
    conn = get_db()
    conn.execute("UPDATE users SET password=? WHERE id=?",
                 (generate_password_hash(new), u['id']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ============ رفع الملفات ============
@app.route('/api/admin/upload', methods=['POST'])
@require_admin
def admin_upload(u):
    if 'file' not in request.files:
        return jsonify({'error': 'لا يوجد ملف'}), 400
    f = request.files['file']
    if not f.filename:
        return jsonify({'error': 'اسم ملف فارغ'}), 400
    safe, reason = is_safe_file(f)
    if not safe:
        return jsonify({'error': reason}), 400

    ext = f.filename.rsplit('.', 1)[1].lower()
    name = f"upload_{int(time.time())}_{secrets.token_hex(8)}.{ext}"
    path = os.path.join(UPLOAD_DIR, name)

    real_path = os.path.realpath(path)
    real_dir = os.path.realpath(UPLOAD_DIR)
    if not real_path.startswith(real_dir):
        return jsonify({'error': 'مسار غير آمن'}), 400

    f.save(path)
    return jsonify({'url': f'/uploads/{name}'})

@app.route('/uploads/<path:name>')
def serve_upload(name):
    return send_from_directory(UPLOAD_DIR, name)

# ============ تقديم Frontend ============
@app.route('/')
def root():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:path>')
def serve_front(path):
    full = os.path.join(FRONTEND_DIR, path)
    if os.path.isfile(full):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, 'index.html')

# ============ التشغيل ============

# ============================================
#                    RUN
# ============================================

@app.route('/api/admin/users/cleanup-admins', methods=['DELETE'])
@require_admin
def cleanup_admins(u):
    """يحذف كل الأدمن عدا الحساب الحالي"""
    conn = get_db()
    r = conn.execute("DELETE FROM users WHERE is_admin=1 AND id != ?", (u['id'],))
    deleted = r.rowcount
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'deleted': deleted})


@app.route('/api/pages', methods=['GET'])
def get_pages():
    conn = get_db()
    rows = conn.execute("SELECT page_name, section_name, field_key, field_value FROM pages").fetchall()
    conn.close()
    result = {}
    for r in rows:
        p = r['page_name']
        if p not in result: result[p] = {}
        if r['section_name'] not in result[p]: result[p][r['section_name']] = {}
        result[p][r['section_name']][r['field_key']] = r['field_value']
    return jsonify(result)

@app.route('/api/admin/pages', methods=['POST'])
@require_admin
def update_pages(u):
    data = request.get_json() or {}
    conn = get_db()
    count = 0
    for page, sections in data.items():
        for section, fields in sections.items():
            for key, value in fields.items():
                conn.execute("INSERT INTO pages(page_name,section_name,field_key,field_value) VALUES(?,?,?,?) ON CONFLICT(page_name,section_name,field_key) DO UPDATE SET field_value=excluded.field_value",
                             (page, section, key, str(value)))
                count += 1
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'updated': count})

if __name__ == '__main__':
    init_db()
    print("=" * 50)
    print("🛡️  ShieldScan Backend يعمل")
    print("=" * 50)
    print("📍 http://localhost:8080")
    print("🔑 admin@shieldscan.local")
    print("=" * 50)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False, use_reloader=False)
