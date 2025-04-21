from flask import Flask, redirect, url_for, session, request, jsonify, flash, render_template
from flask_login import LoginManager, current_user, login_user, logout_user, login_required, UserMixin
from models.models import db, Student
import os
import requests

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
    
    # Google OAuth endpoints
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
    
    # Increase session cookie security and lifetime
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour in seconds
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # We'll print the redirect URI after all routes are registered
    
    # Google login route
    @app.route('/login')
    def login():
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
            # Get the deployment environment
            is_production = os.environ.get('FLASK_ENV') == 'production'
            
            if is_production:
                # Use the configured production URL
                app_url = os.environ.get('APP_URL', 'https://branchout.onrender.com')
                redirect_uri = f'{app_url}/authorize'
                app.logger.info(f"Using production redirect URI: {redirect_uri}")
            else:
                # Local development
                redirect_uri = 'http://localhost:8080/authorize'
                app.logger.info(f"Using development redirect URI: {redirect_uri}")
            
            # Generate and store a state parameter in the session
            session['oauth_state'] = os.urandom(16).hex()
            app.logger.info(f"Generated OAuth state: {session['oauth_state']}")
            
            # Direct OAuth implementation using requests
            scope = "openid email profile"
            auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
            
            auth_params = {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": scope,
                "state": session['oauth_state'],
                "access_type": "offline",
                "prompt": "consent"
            }
            
            # Build the authorization URL
            auth_url_with_params = f"{auth_url}?" + "&".join([f"{k}={v}" for k, v in auth_params.items()])
            app.logger.info(f"Redirecting to OAuth URL: {auth_url_with_params}")
            
            return redirect(auth_url_with_params)
        except Exception as e:
            flash(f'Error initiating Google OAuth: {str(e)}', 'danger')
            return redirect(url_for('index'))
    
    # Google OAuth callback
    @app.route('/authorize')
    def authorize():
        try:
            # Log the incoming state parameter for debugging
            incoming_state = request.args.get('state')
            session_state = session.get('oauth_state')
            app.logger.info(f"Authorize callback - Incoming state: {incoming_state}, Session state: {session_state}")
            
            # Check for error parameter from Google
            if request.args.get('error'):
                error = request.args.get('error')
                error_description = request.args.get('error_description', 'No description provided')
                app.logger.error(f"Google OAuth error: {error} - {error_description}")
                flash(f"Google OAuth error: {error} - {error_description}", 'danger')
                return redirect(url_for('index'))
            
            # Verify state parameter to prevent CSRF
            if incoming_state != session_state:
                app.logger.error(f"State mismatch: {incoming_state} vs {session_state}")
                flash("Invalid state parameter. Try logging in again.", 'danger')
                return redirect(url_for('index'))
            
            # Get the authorization code
            code = request.args.get('code')
            if not code:
                app.logger.error("No authorization code received")
                flash("No authorization code received", 'danger')
                return redirect(url_for('index'))
                
            # Exchange code for tokens
            client_id = os.environ.get('GOOGLE_CLIENT_ID', '')
            client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', '')
            
            # Get the redirect URI
            is_production = os.environ.get('FLASK_ENV') == 'production'
            if is_production:
                app_url = os.environ.get('APP_URL', 'https://branchout.onrender.com')
                redirect_uri = f'{app_url}/authorize'
            else:
                redirect_uri = 'http://localhost:8080/authorize'
            
            token_url = "https://oauth2.googleapis.com/token"
            data = {
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            }
            
            app.logger.info(f"Exchanging code for token with data: {data}")
            
            try:
                token_res = requests.post(token_url, data=data)
                app.logger.info(f"Token response status: {token_res.status_code}")
                
                if token_res.status_code != 200:
                    app.logger.error(f"Error getting token: {token_res.text}")
                    flash(f"Error getting token: {token_res.text}", 'danger')
                    return redirect(url_for('index'))
                    
                tokens = token_res.json()
                access_token = tokens.get("access_token")
                app.logger.info("Successfully obtained access token")
                
                # Get user info
                userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
                headers = {"Authorization": f"Bearer {access_token}"}
                
                userinfo_res = requests.get(userinfo_url, headers=headers)
                if userinfo_res.status_code != 200:
                    app.logger.error(f"Failed to fetch user info: {userinfo_res.text}")
                    flash("Failed to fetch user info", 'danger')
                    return redirect(url_for('index'))
                    
                user_info = userinfo_res.json()
                app.logger.info(f"Successfully fetched user info for: {user_info.get('email')}")
                
            except Exception as e:
                app.logger.error(f"Error in token exchange: {str(e)}")
                flash(f"Error in token exchange: {str(e)}", 'danger')
                return redirect(url_for('index'))
            
            # Check if user exists - note that the user ID field is 'sub' in the response
            google_id = user_info.get('sub')
            if not google_id:
                app.logger.error("No sub/user ID found in user info response")
                app.logger.info(f"User info keys: {user_info.keys()}")
                # Try alternate field names
                google_id = user_info.get('id') or user_info.get('user_id')
                
            app.logger.info(f"Looking up student with google_id: {google_id}")
            student = Student.query.filter_by(google_id=google_id).first()
            
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
                    google_id=google_id,
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
    
    # Mock login functionality has been removed
    
    @app.route('/logout')
    def logout():
        session.clear()
        logout_user()
        flash('You have been logged out', 'info')
        return redirect(url_for('index'))
        
    # Print the redirect URI for debugging
    with app.test_request_context():
        is_production = os.environ.get('FLASK_ENV') == 'production'
        app_url = os.environ.get('APP_URL', '')
        
        if is_production and app_url:
            redirect_uri = f"{app_url}/authorize"
            print(f"\nGoogle OAuth Redirect URI (Production): {redirect_uri}\n")
        else:
            print(f"\nGoogle OAuth Redirect URI (Development): http://localhost:8080/authorize\n")
