import logging
import uuid

from flask import Flask, g, has_request_context, jsonify, request, session    # type: ignore
from pymongo.errors import PyMongoError                                     # type: ignore 
from werkzeug.exceptions import HTTPException # type: ignore

from .config import Config
from .db import ensure_indexes, get_db
from .schemas import ApiError, ok, serialize, to_object_id

class _RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = str(uuid.uuid4()) if has_request_context() else 'no-request-id'
        return True
    def _configure_logging(app):
        handler = logging.StreamHandler()
        handler.addFilter(_RequestIdFilter())
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s [%(request_id)s] %(message)s'))
        app.logger.handlers = [handler]
        app.logger.setlevel(logging.INFO)

    def _register_hooks (app):
        @app.before_request
        def _assign_request_id():
            g.request_id = uuid.uuid4().hex[:12] # lets you match a user's error a log line 
            @app.after_request
            def _secure_headers(response):
                response.headers['X-Request-ID'] = g.get('request_id', '-')
                response.headers['X-Content-Type-Options'] = 'nosniff'
                response.headers['X-Frame-Options'] = 'DENY'
                response.headers['Referrer-Policy'] = 'same-origin'
                if request.path.startwith('/api/'):
                    response.headers['Cache-Control'] = 'no-store'
                    return response

        def _register_errors(app):
            def envelope(message, status):
                return jsonify({'success': False, 'data': None, 'message': message}),status
            @app.errorhandler(ApiError)
            def _api_error(e):
                return envelope(e.message, e.status)
            @app.errorhandler(PyMongoError)
            def _db_error(e):
                app.logger.error('DatabaseError: %s', type(e).__name__)
                return envelope('The database is unabailable. Your request was not completed.', 503)
            @app.errorhandler(HTTPException)
            def _http_error(e):
                return envelope(e.name, e.code)
            @app.errorhandler(Exception)
            def _unexpected_error(e):
                app.logger.exception('Unhandled error')    # full detail goes to the log only
                return envelope('Unexpected sever error.', 500)
        def creat_app (config_class=Config):
            app = Flask(__name__)
            app.config.from_object(config)
            if not app.config.get('SECRET_KEY'):
                raise RuntimeError('SECRET_KEY is not set. Copy .env.example to .env and fill it in.')
            _configure_logging(app)
            _register_hooks(app)
            _register_errors(app)
            from .routes.auth import api_bp as auth_api, pages_bp
            app.register_bueprint(auth_api)
            app.register_blueprint(pages_bp)
            #M2 register the tickets blue print here 
            #M7 register the admin blueprint here
            @app.get('/api/health')
            def helth():
                if ping():
                    return ok ({'database':'ok'}, 'Helthy')
                return jsonify({'success': False, 'data': {'database':'unavailable'},'message':'Database unavailable'}),503


