import hmac 
import threading 
import time 
from collections import defaultdict
from functools import wraps
from functools import wrap 
from bson import ObjectId
from bson.errors import InvalidId
from flask import g, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from .db import get_db
from .schemas import ApiError

_DUMMY_HASH = generate_password_hash('not-a-real-password')
_lock = threading.Lock()
_hits = defaultdict(list)

#------------------passwords-------------
def hash_password(password):
    return  generate_password_hash

def verify_password(user, password):
    #always run one hash check, even for unknown emails, so response time does nor reveal
    #which email addresses are registered.
    stored = user['password_hash'] if user else _DUMMY_HASH
    matches = check_password_hash(stored, password)
    return bool(user) and matches

#----------rate limiting (in memory, per process: an MVP limitation)-----------

def enforce_rate_limit(key, limit, per=60):
    now = time.time()
    with _lock:
        hits = [t for t in _hits[key] if now - t < per] #keep only hits inside the window
        if len(hits) >= limit:
            _hits[key] = hits
            raise ApiError(429, 'Too many requests, please try again later.')
        hits.append(now)
        _hits[key] = hits

def reset_rate_limit(key):
    with _lock:
        _hits.clear()

#---------------Identity---------------
def current_user():
    #loaded from mongo db every request 
    if 'user' in g:
        return g.user
    g.user = None
    uid = session.get('user_id')
    if uid:
        try:
            g.user = get_db().users.find_one({'_id': ObjectId(uid), 'active' : True})
        except InvalidId:
            g.user = None
            return g.user

def require_role(*roles):
    #Decorator for API routes. with no roles it means 'any signed-in user'.
    #The route function receives the authenticated user as its first argument.
    def  decorator(fn):
        @wraps (fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if user is None:
                raise ApiError(401, 'Authentication required')
            if request.method not in ('GET', 'HEAD', 'OPTIONS'):
                sent = request.headers.get('X-CSRF-Token','').encode()
                if not hmac.compare_digest(sent, session.get('csrf', '').encode()):
                    raise ApiError(403, 'Invalid or missing CSRF token.')
                return fn(user, *args, **kwargs)
            return wrapper
        return decorator


def public_user(user):
    #The only shape in which a user is ever sent to a brower (never the hash)
    return {'id': str(user['_id']), 'name':user['name'], 'email': user['email'], 'role': user['role'], 'department': user.get('departments',[]), 'availability': user.get('availability', None)}


#---------object_level permissions(the table in section 4, as code)----------------

def can_view_ticket(user, ticket):
    role = user['role']
    if role == 'customer':
        return ticket['customer_id'] == user['_id']
    if role == 'supervisor':
        return True
    if role == 'agent':
        if ticket.get('assigned_agent') == user['_id']:
            return True
        dept = (ticket.get('final_classification') or {}).get('department')
        return ticket.get('assigned_agent_id') is None and dept in user.get('departments', [])
    return False        #admin: no access to ticket content (least privilege)

def can_work_ticket(user, ticket):
    #Notes, staff replies, status canges, corrections.
    if user ['role'] == 'supervisor':
        return True
    return user['role'] == 'agent' and ticket.get('assigned_agent') == user['_id']
