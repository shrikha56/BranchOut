from flask import Flask, redirect, url_for, session, request, jsonify, flash, render_template
from flask_login import LoginManager, current_user, login_user, logout_user, login_required, UserMixin
from models.models import db, Student
import os
from authlib.integrations.flask_client import OAuth
from werkzeug.exceptions import HTTPException

# Initialize login manager
login_manager = LoginManager()
login_manager.login_view = 'login'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, student):
        self.id = student.id
        self.student = student
        
    def get_id(self):
        return str(self.id)

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    student = Student.query.get(int(user_id))
    if not student:
        return None
    return User(student)

def init_auth(app):
    """Initialize authentication for the Flask app"""
    login_manager.init_app(app)
    
    # Set secret key for session
    if not app.secret_key:
        app.secret_key = os.environ.get('SECRET_KEY', 'development-key')
    
    # Get application name from config
    app_name = app.config.get('APP_NAME', 'BranchOut')
    
    # Google OAuth credentials
    client_id = os.environ.get('GOOGLE_CLIENT_ID', '')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    app.logger.info(f"Client ID aaaaaaaaa: {client_id}")
    app.logger.info(f"Client secret aaaaaaaaa: {client_secret}")
    


    # Print detailed debug information
    if client_id:
        app.logger.info(f"Client ID length: {len(client_id)} characters")
        app.logger.info(f"Client ID first 8 chars: {client_id[:8]}")
        app.logger.info(f"Client ID last 4 chars: {client_id[-4:]}")
    else:
        app.logger.error("GOOGLE_CLIENT_ID environment variable is not set")
        
    if client_secret:
        app.logger.info(f"Client secret length: {len(client_secret)} characters")
        app.logger.info(f"Client secret first 8 chars: {client_secret[:8]}")
    else:
        app.logger.error("GOOGLE_CLIENT_SECRET environment variable is not set")
    
    # Increase session cookie security and lifetime
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour in seconds
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # OAuth setup
    oauth = OAuth(app)
    oauth.register(
        name='google',
        client_id=os.environ.get('GOOGLE_CLIENT_ID'),
        client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
        access_token_url='https://oauth2.googleapis.com/token',
        access_token_params=None,
        authorize_url='https://accounts.google.com/o/oauth2/auth',
        authorize_params=None,
        api_base_url='https://www.googleapis.com/oauth2/v2/',
        userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
        client_kwargs={'scope': 'openid email profile'},
    )

    # Login route
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'GET':
            return render_template('login.html')
        # Email/password login is deprecated, redirect to Google login
        return redirect(url_for('google_login'))

    @app.route('/login/google')
    def google_login():
        redirect_uri = url_for('google_authorize', _external=True)
        return oauth.google.authorize_redirect(redirect_uri)

    # Google OAuth callback
    @app.route('/authorize')
    def google_authorize():
        try:
            token = oauth.google.authorize_access_token()
            user_info = oauth.google.parse_id_token(token)
        except HTTPException as e:
            flash('Google authentication failed.', 'danger')
            return redirect(url_for('login'))
        except Exception as e:
            flash('An error occurred during authentication.', 'danger')
            return redirect(url_for('login'))

        email = user_info.get('email')
        name = user_info.get('name', 'New Student')
        picture = user_info.get('picture', '/static/img/default-profile.jpg')
        if not email:
            flash('Google account did not return an email.', 'danger')
            return redirect(url_for('login'))

        student = Student.query.filter_by(email=email).first()
        if student:
            login_user(User(student))
            if student.first_login:
                student.first_login = False
                db.session.commit()
                return redirect(url_for('submit', student_id=student.id))
            else:
                return redirect(url_for('directory', student_id=student.id))
        else:
            new_student = Student(
                name=name,
                year=1,
                faculty='',
                email=email,
                profile_picture=picture,
                first_login=True
            )
            db.session.add(new_student)
            db.session.commit()
            login_user(User(new_student))
            return redirect(url_for('submit', student_id=new_student.id))

    @app.route('/logout')
    def logout():
        session.clear()
        logout_user()
        flash('You have been logged out', 'info')
        return redirect(url_for('index'))

    # Print authentication initialization message
    print(f"\nInitialized Google OAuth authentication for {app_name}\n")
