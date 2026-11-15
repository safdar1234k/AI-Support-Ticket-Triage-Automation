import os 
from dotenv import load_dotenv

load_dotenv() #loads .env into os.environ (local developement only)

def __int(name, default):
    return int(os.environ.get(name, default))

def _float(name, default):
    return float(os.environ.get(name, default))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    MONGODB_URL = os.environ.get('MONGODB_URl', 'mongodb://localhost:27017/')
    MONGODB_DB = os.environ.get('MONGODB_DB', 'ai_ticket_triage')

    SESSION_COOKIE_HTTPONLY = True      #javascript cannot read the session cookie
    SESSION_COOKIE_SAMESITE = 'Lax'     #cookie is not sent on cross-site POSTs
    SESSION_COOKIE_SECURE = os.environ.get('COOKIE_SECURE', '0') == '1'     #set to 1 behind HTTPS
    MAX_CONTENT_LENGTH = 64 * 1024      #reject request bodies above 64 KB

    #FOR AI Use  (M3)
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    GIMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.8-flash')
    AI_TIMEOUT_MS = __int('AI_TIMEOUt_MS', 20000)
    AI_MAX_ATTEMPTS = __int('AI_MAX_ATTEMPTS', 3)
    CONFIDENCE_THRESHOLD = _float('CONFIDENCE_THRESHOLD', 0.6)
    TRIAGE_INLINE = False               #True = run triage inside the request

    #Business rules (M4 and later)
    DUPLICATE_WINDOW_DAYS = __int('DUPLICATE_WINDOW_DAYS', 14)
    DUPLICATE_MIN_SCORE = _float('DUPLICATE_MIN_SCORE', 0.6)
    REOPEN_WINDOW_DAYS = __int('REOPEN_WINDOW_DAYS', 7)

    #Notifications (M7)
    EMAIL_MODE = os.environ.get('EMAIL_MODE', 'console')   #console | smtp
    EMAIL_FROM = os.environ.get('EMAIL_FROM', 'support@example.test')
    SMTP_HOST = os.environ.get('SMTP_HOST')
    SMTP_PORT = __int('SMTP_PORT', 587)
    SMTP_USER = os.environ.get('SMTP_USER')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
    NOTIFY_MAX_ATTEMPTS = __int('NOTIFY_MAX_ATTEMPTS', 3)


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = 'test-secret-key'
    MONGODB_DB = 'ai_ticket_triage_test'    #tests must never touch the real database
    TRIAGE_INLINE = True
    EMAIL_MODE = 'console'
    AI_MAX_ATTEMPTS = 2 
