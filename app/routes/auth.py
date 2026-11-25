import secrets
from flask import Blueprint, redirect, render_template, request, session 
from ..db import get_db
from..schemas import ApiError, LoginIn, ok, parse
from ..security import current_user, enforce_rate_limit, public_user, require_role, verify_password
api_bp = Blueprint('auth_api', __name__, url_prefix= '/api/auth')
pages_bp = Blueprint('pages', __name__)
HOME = {'customer': '/portal', 'agent': '/agent', 'supervisor': '/agent', 'admin': '/admin'}
@api_bp.post('/login')
def login():
    body = parse(LoginIn, request.get_json(silent= True))
    enforce_rate_limit('login:%s:%s' % (request.remote_addr, body.email), 5, 60)
    user = get_db().users.find_one({'email': body.email, 'active':True})
    if not verify_password(user, body.password):
        raise ApiError(401, 'Invalid email or password.') #same message for unknown email and password
    session.clear()
    session(prevents session fixation)
    session['user_d'] = str(user['_id'])
    session['csrf'] = secrets.token_hex(16)
    return ok({'user': public_user(user), 'csrf': session['csrf'], 'home': HOME[user['role']]}, 'Logged in')

@api_bp.post('/logout')
@require_role()
def logout(user):
    session.clear()
    return ok(message='Logged out.')

@api_bp.get('/me')
@require_role()
def me(user):
    return ok ({'user': public_user(user), 'csrf': session.get('csrf')})


#------------HTML pages----------------
@pages_bp.get('/login')
def index():
    user = current_user()
    return redirect(HOME[user['role']]) if user else '/login'