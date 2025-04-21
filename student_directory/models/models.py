from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Association tables
class StudentInterest(db.Model):
    __tablename__ = 'student_interests'
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), primary_key=True)
    interest_id = db.Column(db.Integer, db.ForeignKey('interests.id'), primary_key=True)

class StudentClub(db.Model):
    __tablename__ = 'student_clubs'
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id'), primary_key=True)

class StudentLanguage(db.Model):
    __tablename__ = 'student_languages'
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), primary_key=True)
    language_id = db.Column(db.Integer, db.ForeignKey('languages.id'), primary_key=True)

# Main tables
class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    faculty = db.Column(db.String(100), nullable=False)
    profile_picture = db.Column(db.String(255), nullable=False, default='/static/img/default-profile.jpg')
    
    # Google Auth fields
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    email = db.Column(db.String(100), unique=True, nullable=True)
    first_login = db.Column(db.Boolean, default=True)
    
    # Relationships
    interests = db.relationship('Interest', secondary='student_interests', backref=db.backref('students', lazy='dynamic'))
    clubs = db.relationship('Club', secondary='student_clubs', backref=db.backref('students', lazy='dynamic'))
    languages = db.relationship('Language', secondary='student_languages', backref=db.backref('students', lazy='dynamic'))

class Interest(db.Model):
    __tablename__ = 'interests'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

class Club(db.Model):
    __tablename__ = 'clubs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

class Language(db.Model):
    __tablename__ = 'languages'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

class Prompt(db.Model):
    __tablename__ = 'prompts'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(255), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    # Relationships
    creator = db.relationship('Student', foreign_keys=[created_by], backref=db.backref('created_prompts', lazy='dynamic'))

class Match(db.Model):
    __tablename__ = 'matches'
    id = db.Column(db.Integer, primary_key=True)
    prompt_id = db.Column(db.Integer, db.ForeignKey('prompts.id'), nullable=False)
    matched_user_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    submitted_by = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    prompt = db.relationship('Prompt', backref=db.backref('matches', lazy='dynamic'))
    matched_user = db.relationship('Student', foreign_keys=[matched_user_id], backref=db.backref('matches_received', lazy='dynamic'))
    submitter = db.relationship('Student', foreign_keys=[submitted_by], backref=db.backref('matches_submitted', lazy='dynamic'))

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    
    # Relationships
    sender = db.relationship('Student', foreign_keys=[sender_id], backref=db.backref('sent_messages', lazy='dynamic'))
    receiver = db.relationship('Student', foreign_keys=[receiver_id], backref=db.backref('received_messages', lazy='dynamic'))
