from flask import Flask, redirect, url_for, session, request, jsonify, flash, render_template
from flask_login import LoginManager, current_user, login_user, logout_user, login_required, UserMixin
from authlib.integrations.flask_client import OAuth
from models.models import db, Student
import os

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
    
    # Initialize OAuth
    oauth = OAuth(app)
    
    # Get application name from config
    app_name = app.config.get('APP_NAME', 'BranchOut')
    
    # Register Google OAuth client
    google = oauth.register(
        name='google',
        client_id=os.environ.get('GOOGLE_CLIENT_ID', ''),
        client_secret=os.environ.get('GOOGLE_CLIENT_SECRET', ''),
        access_token_url='https://accounts.google.com/o/oauth2/token',
        access_token_params=None,
        authorize_url='https://accounts.google.com/o/oauth2/auth',
        authorize_params=None,
        api_base_url='https://www.googleapis.com/oauth2/v1/',
        client_kwargs={'scope': 'openid email profile'},
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration'
    )
    
    # We'll print the redirect URI after all routes are registered
    
    # Google login route
    @app.route('/login')
    def login():
        # For demonstration, also provide a mock login option
        if request.args.get('mock'):
            return render_template('mock_login.html')
        
        # Check if Google credentials are configured
        client_id = os.environ.get('GOOGLE_CLIENT_ID', '')
        client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', '')
        
        if not client_id or client_id == 'your-google-client-id':
            flash('Google Client ID is missing or invalid. Please check your .env file.', 'danger')
            return redirect(url_for('index'))
            
        if not client_secret or client_secret == 'your-google-client-secret':
            flash('Google Client Secret is missing or invalid. Please check your .env file.', 'danger')
            return redirect(url_for('index'))
            
        # Redirect to Google OAuth
        try:
            # Get the deployment environment from environment variable
            is_vercel = os.environ.get('VERCEL', '0') == '1'
            
            if is_vercel:
                # Use Vercel deployment URL
                vercel_url = os.environ.get('VERCEL_URL', '')
                if vercel_url:
                    redirect_uri = f'https://{vercel_url}/authorize'
                else:
                    # Fallback to configured URL
                    redirect_uri = os.environ.get('OAUTH_REDIRECT_URI', 'http://localhost:8080/authorize')
            else:
                # Local development
                redirect_uri = 'http://localhost:8080/authorize'
                
            return google.authorize_redirect(redirect_uri)
        except Exception as e:
            flash(f'Error initiating Google OAuth: {str(e)}', 'danger')
            return redirect(url_for('index'))
    
    # Google OAuth callback
    @app.route('/authorize')
    def authorize():
        try:
            token = google.authorize_access_token()
            user_info = google.parse_id_token(token)
            
            # Check if user exists
            student = Student.query.filter_by(google_id=user_info['sub']).first()
            
            if student:
                # Existing user - log them in
                login_user(User(student))
                
                # Check if it's their first login
                if student.first_login:
                    student.first_login = False
                    db.session.commit()
                    return redirect(url_for('submit', student_id=student.id))
                else:
                    return redirect(url_for('directory', student_id=student.id))
            else:
                # New user - create a placeholder student record
                new_student = Student(
                    name=user_info.get('name', 'New Student'),
                    year=1,  # Default value, will be updated in the form
                    faculty='',  # Will be updated in the form
                    google_id=user_info['sub'],
                    email=user_info.get('email'),
                    profile_picture=user_info.get('picture', '/static/img/default-profile.jpg'),
                    first_login=True
                )
                db.session.add(new_student)
                db.session.commit()
                
                # Log in the new user
                login_user(User(new_student))
                
                # Redirect to the registration form
                return redirect(url_for('submit', student_id=new_student.id))
        except Exception as e:
            # Provide detailed error information
            error_message = str(e)
            app.logger.error(f"OAuth Error: {error_message}")
            
            if 'invalid_client' in error_message:
                flash('Google OAuth client error: Your client ID or client secret may be incorrect or not authorized.', 'danger')
                flash('Make sure you have: 1) Added the correct client secret to .env file, 2) Configured the OAuth consent screen, 3) Added your email as a test user', 'warning')
            elif 'redirect_uri_mismatch' in error_message:
                flash('Redirect URI mismatch: The redirect URI in your Google Console does not match the application URI.', 'danger')
                flash(f'Please add this exact URI to your Google Console: {url_for("authorize", _external=True)}', 'warning')
            else:
                flash(f'Google authentication error: {error_message}', 'danger')
                
            return redirect(url_for('index'))
    
    # Mock login for testing
    @app.route('/login/mock', methods=['POST'])
    def mock_login():
        email = request.form.get('email')
        name = request.form.get('name', 'New Student')
        
        if not email:
            flash('Email is required', 'danger')
            return redirect(url_for('login', mock=True))
        
        # Check if user exists
        student = Student.query.filter_by(email=email).first()
        
        if student:
            # Existing user - log them in
            login_user(User(student))
            
            # Check if it's their first login
            if student.first_login:
                student.first_login = False
                db.session.commit()
                return redirect(url_for('submit', student_id=student.id))
            else:
                return redirect(url_for('directory', student_id=student.id))
        else:
            # New user - create a placeholder student record
            new_student = Student(
                name=name,
                year=1,  # Default value, will be updated in the form
                faculty='',  # Will be updated in the form
                google_id=email,  # Use email as google_id for mock
                email=email,
                profile_picture='/static/img/default-profile.jpg',
                first_login=True
            )
            db.session.add(new_student)
            db.session.commit()
            
            # Log in the new user
            login_user(User(new_student))
            
            # Redirect to the registration form
            return redirect(url_for('submit', student_id=new_student.id))
    
    @app.route('/logout')
    def logout():
        session.clear()
        logout_user()
        flash('You have been logged out', 'info')
        return redirect(url_for('index'))
        
    # Print the redirect URI for debugging
    print(f"\nGoogle OAuth Redirect URI: http://localhost:8080/authorize\n")
