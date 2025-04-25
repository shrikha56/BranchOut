from flask import Flask, redirect, url_for, session, request, jsonify, flash, render_template
from flask_login import LoginManager, current_user, login_user, logout_user, login_required, UserMixin
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
        print("aaaaaaahelp" + app.secret_key)
    
    # Get application name from config
    app_name = app.config.get('APP_NAME', 'BranchOut')
    
    # Increase session cookie security and lifetime
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour in seconds
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # We'll print the redirect URI after all routes are registered
    
    # Login route
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'GET':
            return render_template('login.html')
        
        # Process login form
        if request.method == 'POST':
            email = request.form.get('email')
            name = request.form.get('name', 'New Student')
            
            if not email:
                flash('Email is required', 'danger')
                return redirect(url_for('login'))
            
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
    
    # Mock login functionality has been removed
    
    @app.route('/logout')
    def logout():
        session.clear()
        logout_user()
        flash('You have been logged out', 'info')
        return redirect(url_for('index'))
        
    # Print authentication initialization message
    print(f"\nInitialized simple email authentication for {app_name}\n")
