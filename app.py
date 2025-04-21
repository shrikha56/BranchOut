from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import login_required, current_user
from models.models import db, Student, Interest, Club, Language, StudentInterest, StudentClub, StudentLanguage, Prompt, Match, Message
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from auth import init_auth

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///student_directory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'development-key')
app.config['APP_NAME'] = os.environ.get('APP_NAME', 'BranchOut')
# Using SERVER_NAME can cause routing issues in development
# app.config['PREFERRED_URL_SCHEME'] = 'http'

db.init_app(app)

# Initialize authentication
init_auth(app)

# Make APP_NAME available to all templates
@app.context_processor
def inject_app_name():
    return {'app_name': app.config.get('APP_NAME', 'BranchOut')}

# Ensure upload and img directories exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

img_dir = os.path.join(app.static_folder, 'img')
if not os.path.exists(img_dir):
    os.makedirs(img_dir)

# Create a default profile picture if it doesn't exist
default_img_path = os.path.join(img_dir, 'default-profile.jpg')
if not os.path.exists(default_img_path):
    # Create a simple default profile image (a colored circle)
    try:
        from PIL import Image, ImageDraw
        
        # Create a 200x200 white image with a blue circle
        img = Image.new('RGB', (200, 200), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.ellipse((20, 20, 180, 180), fill=(66, 133, 244))
        img.save(default_img_path)
    except ImportError:
        print("PIL not installed. Default profile picture will not be created.")
        print("Install PIL with: pip install pillow")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    if current_user.is_authenticated:
        # Redirect to directory if already logged in
        return redirect(url_for('directory', student_id=current_user.id))
    return render_template('index.html')

@app.route('/submit', methods=['GET', 'POST'])
@login_required
def submit():
    # Get the student_id from the URL parameter or current user
    student_id = request.args.get('student_id', None, type=int)
    
    # If no student_id provided, use the current user's ID
    if not student_id and current_user.is_authenticated:
        student_id = current_user.id
    
    # Get the student from the database
    student = Student.query.get(student_id)
    
    # If student not found, redirect to index
    if not student:
        flash('Student not found', 'danger')
        return redirect(url_for('index'))
    
    # If this is a GET request, show the form
    if request.method == 'GET':
        # Get all interests, clubs, and languages for the form
        interests = Interest.query.all()
        clubs = Club.query.all()
        languages = Language.query.all()
        return render_template('submit.html', student=student, interests=interests, clubs=clubs, languages=languages)
    
    # If this is a POST request, process the form
    # Get form data
    name = request.form.get('name')
    year = request.form.get('year')
    faculty = request.form.get('faculty')
    interests = request.form.getlist('interests')
    clubs = request.form.getlist('clubs')
    languages = request.form.getlist('languages')
    
    # Handle profile picture upload
    profile_picture_path = student.profile_picture  # Keep existing picture by default
    
    if 'profile_picture' in request.files:
        file = request.files['profile_picture']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Create a unique filename using student name and timestamp
            import time
            unique_filename = f"{name.replace(' ', '_')}_{int(time.time())}.{filename.rsplit('.', 1)[1].lower()}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            profile_picture_path = f"/static/uploads/{unique_filename}"
    
    # Update student information
    student.name = name
    student.year = year
    student.faculty = faculty
    student.profile_picture = profile_picture_path
    student.first_login = False  # Mark as not first login anymore
    
    # Add interests
    for interest_name in interests:
        interest = Interest.query.filter_by(name=interest_name).first()
        if not interest:
            interest = Interest(name=interest_name)
            db.session.add(interest)
            db.session.flush()
        student_interest = StudentInterest(student_id=student.id, interest_id=interest.id)
        db.session.add(student_interest)
    
    # Add clubs
    for club_name in clubs:
        club = Club.query.filter_by(name=club_name).first()
        if not club:
            club = Club(name=club_name)
            db.session.add(club)
            db.session.flush()
        student_club = StudentClub(student_id=student.id, club_id=club.id)
        db.session.add(student_club)
    
    # Add languages
    for language_name in languages:
        language = Language.query.filter_by(name=language_name).first()
        if not language:
            language = Language(name=language_name)
            db.session.add(language)
            db.session.flush()
        student_language = StudentLanguage(student_id=student.id, language_id=language.id)
        db.session.add(student_language)
    
    # Commit all changes
    db.session.commit()
    
    # Redirect to directory with student_id parameter for welcome message
    return redirect(url_for('directory', student_id=student.id))

@app.route('/directory')
@login_required
def directory():
    # Get student_id from query parameter or current user
    student_id = request.args.get('student_id', None, type=int)
    
    # If no student_id provided, use the current user's ID
    if not student_id and current_user.is_authenticated:
        student_id = current_user.id
        
    current_student = None
    
    if student_id:
        current_student = Student.query.get(student_id)
    
    students_query = Student.query.all()
    interests = Interest.query.all()
    clubs = Club.query.all()
    languages = Language.query.all()
    faculties = db.session.query(Student.faculty).distinct().all()
    faculties = [f[0] for f in faculties]
    
    # Convert student objects to JSON-serializable dictionaries
    students = []
    for student in students_query:
        # Check if student has profile_picture attribute
        profile_pic = getattr(student, 'profile_picture', '/static/img/default-profile.jpg')
        
        student_data = {
            'id': student.id,
            'name': student.name,
            'year': student.year,
            'faculty': student.faculty,
            'interests': [i.name for i in student.interests],
            'clubs': [c.name for c in student.clubs],
            'languages': [l.name for l in student.languages],
            'profile_picture': profile_pic
        }
        students.append(student_data)
    
    return render_template('directory.html', 
                          students=students, 
                          interests=interests, 
                          clubs=clubs, 
                          languages=languages,
                          faculties=faculties,
                          current_student=current_student)

@app.route('/api/filter', methods=['POST'])
def filter_students():
    data = request.json
    
    # Start with all students
    query = Student.query
    
    # Filter by faculty if provided
    if 'faculty' in data and data['faculty']:
        query = query.filter(Student.faculty == data['faculty'])
    
    # Filter by interests if provided
    if 'interests' in data and data['interests']:
        for interest in data['interests']:
            query = query.join(StudentInterest).join(Interest).filter(Interest.name == interest)
    
    # Filter by clubs if provided
    if 'clubs' in data and data['clubs']:
        for club in data['clubs']:
            query = query.join(StudentClub).join(Club).filter(Club.name == club)
    
    # Filter by languages if provided
    if 'languages' in data and data['languages']:
        for language in data['languages']:
            query = query.join(StudentLanguage).join(Language).filter(Language.name == language)
    
    # Get the filtered students
    students = query.all()
    
    # Format the results
    result = []
    for student in students:
        student_data = {
            'id': student.id,
            'name': student.name,
            'year': student.year,
            'faculty': student.faculty,
            'interests': [i.name for i in student.interests],
            'clubs': [c.name for c in student.clubs],
            'languages': [l.name for l in student.languages],
            'profile_picture': student.profile_picture
        }
        result.append(student_data)
    
    return jsonify(result)

@app.route('/api/validate-name', methods=['POST'])
def validate_name():
    data = request.json
    name = data.get('name')
    filters = data.get('filters', {})
    
    # Get the user's faculty if name is provided for faculty filtering
    user_faculty = None
    if 'user_name' in data and data['user_name']:
        user = Student.query.filter_by(name=data['user_name']).first()
        if user:
            user_faculty = user.faculty
            filters['faculty'] = user_faculty
    
    # Start with all students
    query = Student.query
    
    # Apply filters
    if 'faculty' in filters and filters['faculty']:
        query = query.filter(Student.faculty == filters['faculty'])
    
    if 'interests' in filters and filters['interests']:
        for interest in filters['interests']:
            query = query.join(StudentInterest).join(Interest).filter(Interest.name == interest)
    
    if 'clubs' in filters and filters['clubs']:
        for club in filters['clubs']:
            query = query.join(StudentClub).join(Club).filter(Club.name == club)
    
    if 'languages' in filters and filters['languages']:
        for language in filters['languages']:
            query = query.join(StudentLanguage).join(Language).filter(Language.name == language)
    
    # Check if the name exists in the filtered list
    student = query.filter(Student.name == name).first()
    
    if student:
        return jsonify({'valid': True, 'student': {
            'id': student.id,
            'name': student.name,
            'year': student.year,
            'faculty': student.faculty,
            'interests': [i.name for i in student.interests],
            'clubs': [c.name for c in student.clubs],
            'languages': [l.name for l in student.languages],
            'profile_picture': student.profile_picture
        }})
    else:
        return jsonify({'valid': False})

@app.route('/api/dynamic-prompt', methods=['POST'])
def dynamic_prompt():
    data = request.json
    logged_in_user_name = data.get('logged_in_user')
    prompt_type = data.get('prompt_type')
    
    # Get the logged-in user
    logged_in_user = None
    if logged_in_user_name:
        logged_in_user = Student.query.filter_by(name=logged_in_user_name).first()
        if not logged_in_user:
            return jsonify({'error': 'Logged in user not found'}), 404
    
    # Start with all students except the logged-in user
    query = Student.query
    if logged_in_user:
        query = query.filter(Student.id != logged_in_user.id)
    
    # Apply filters based on prompt type
    if prompt_type == 'same_faculty':
        # Find someone in the same faculty
        if logged_in_user:
            query = query.filter(Student.faculty == logged_in_user.faculty)
        else:
            return jsonify({'error': 'Need logged in user for this prompt'}), 400
    
    elif prompt_type == 'same_language_and_hobby':
        # Find someone who speaks the same language and has the same hobby
        if logged_in_user:
            # Get user's languages and interests
            user_languages = [lang.id for lang in logged_in_user.languages]
            user_interests = [interest.id for interest in logged_in_user.interests]
            
            if not user_languages or not user_interests:
                return jsonify({'error': 'User needs languages and interests for this prompt'}), 400
            
            # Find students with at least one matching language and interest
            language_matches = StudentLanguage.query.filter(
                StudentLanguage.language_id.in_(user_languages)
            ).with_entities(StudentLanguage.student_id).distinct().subquery()
            
            interest_matches = StudentInterest.query.filter(
                StudentInterest.interest_id.in_(user_interests)
            ).with_entities(StudentInterest.student_id).distinct().subquery()
            
            query = query.filter(Student.id.in_(language_matches)).filter(Student.id.in_(interest_matches))
        else:
            return jsonify({'error': 'Need logged in user for this prompt'}), 400
    
    elif prompt_type == 'different_year_same_club':
        # Find someone in a different year but in the same club
        if logged_in_user:
            # Get user's clubs
            user_clubs = [club.id for club in logged_in_user.clubs]
            
            if not user_clubs:
                return jsonify({'error': 'User needs clubs for this prompt'}), 400
            
            # Find students in different year but with at least one matching club
            club_matches = StudentClub.query.filter(
                StudentClub.club_id.in_(user_clubs)
            ).with_entities(StudentClub.student_id).distinct().subquery()
            
            query = query.filter(Student.year != logged_in_user.year).filter(Student.id.in_(club_matches))
        else:
            return jsonify({'error': 'Need logged in user for this prompt'}), 400
    
    # Get the filtered students
    students = query.all()
    
    # Format the results
    result = []
    for student in students:
        # Check if student has profile_picture attribute
        profile_pic = getattr(student, 'profile_picture', '/static/img/default-profile.jpg')
        
        student_data = {
            'id': student.id,
            'name': student.name,
            'year': student.year,
            'faculty': student.faculty,
            'interests': [i.name for i in student.interests],
            'clubs': [c.name for c in student.clubs],
            'languages': [l.name for l in student.languages],
            'profile_picture': profile_pic
        }
        result.append(student_data)
    
    return jsonify(result)

@app.route('/api/match', methods=['POST'])
def create_match():
    data = request.json
    prompt_id = data.get('prompt_id')
    matched_user_name = data.get('matched_user_name')
    submitted_by = data.get('submitted_by')
    prompt_type = data.get('prompt_type')
    
    # Validate input
    if not prompt_id or not matched_user_name or not submitted_by:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Check if the matched user exists
    matched_user = Student.query.filter_by(name=matched_user_name).first()
    if not matched_user:
        return jsonify({'error': 'Matched user not found'}), 404
    
    # Check if the submitter exists
    submitter = Student.query.get(submitted_by)
    if not submitter:
        return jsonify({'error': 'Submitter not found'}), 404
    
    # Get or create the prompt based on prompt_id
    prompt = None
    if prompt_id == "1":
        prompt_text = "Find someone in the same faculty as you"
        prompt = Prompt.query.filter_by(text=prompt_text).first()
        if not prompt:
            prompt = Prompt(text=prompt_text, created_by=submitted_by)
            db.session.add(prompt)
            db.session.commit()
    elif prompt_id == "2":
        prompt_text = "Find someone who speaks the same language and shares a hobby"
        prompt = Prompt.query.filter_by(text=prompt_text).first()
        if not prompt:
            prompt = Prompt(text=prompt_text, created_by=submitted_by)
            db.session.add(prompt)
            db.session.commit()
    elif prompt_id == "3":
        prompt_text = "Find someone in a different year but in the same club"
        prompt = Prompt.query.filter_by(text=prompt_text).first()
        if not prompt:
            prompt = Prompt(text=prompt_text, created_by=submitted_by)
            db.session.add(prompt)
            db.session.commit()
    else:
        # Try to find an existing prompt by ID
        try:
            prompt_id_int = int(prompt_id)
            prompt = Prompt.query.get(prompt_id_int)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid prompt ID'}), 400
    
    if not prompt:
        return jsonify({'error': 'Prompt not found'}), 404
    
    # Check if this prompt has already been matched by this user
    existing_match = Match.query.filter_by(
        prompt_id=prompt.id,
        submitted_by=submitted_by
    ).first()
    
    if existing_match:
        return jsonify({'error': 'You have already matched someone to this prompt'}), 400
    
    # Validate the match based on the prompt criteria
    is_valid = True
    error_message = ""
    
    # Apply validation based on prompt type
    if prompt_type == "same_faculty":
        # Validate same faculty
        if submitter.faculty != matched_user.faculty:
            is_valid = False
            error_message = f"This prompt requires someone from your faculty ({submitter.faculty})"
    
    elif prompt_type == "same_language_and_hobby":
        # Validate same language and hobby
        submitter_languages = [lang.id for lang in submitter.languages]
        matched_languages = [lang.id for lang in matched_user.languages]
        
        submitter_interests = [interest.id for interest in submitter.interests]
        matched_interests = [interest.id for interest in matched_user.interests]
        
        has_matching_language = any(lang_id in matched_languages for lang_id in submitter_languages)
        has_matching_interest = any(interest_id in matched_interests for interest_id in submitter_interests)
        
        if not has_matching_language:
            is_valid = False
            error_message = "This prompt requires someone who speaks at least one of your languages"
        elif not has_matching_interest:
            is_valid = False
            error_message = "This prompt requires someone who shares at least one of your interests"
    
    elif prompt_type == "different_year_same_club":
        # Validate different year and same club
        if submitter.year == matched_user.year:
            is_valid = False
            error_message = "This prompt requires someone from a different year than you"
        else:
            # Check for same club only if the user has clubs
            if submitter.clubs:
                submitter_clubs = [club.id for club in submitter.clubs]
                matched_clubs = [club.id for club in matched_user.clubs]
                
                has_matching_club = any(club_id in matched_clubs for club_id in submitter_clubs)
                
                if not has_matching_club:
                    is_valid = False
                    error_message = "This prompt requires someone who is in at least one of your clubs"
            # If user has no clubs, we don't validate club matching
    
    if not is_valid:
        return jsonify({'error': error_message}), 400
    
    # Create the match
    match = Match(
        prompt_id=prompt.id,
        matched_user_id=matched_user.id,
        submitted_by=submitted_by
    )
    
    db.session.add(match)
    db.session.commit()
    
    return jsonify({
        'id': match.id,
        'prompt_id': match.prompt_id,
        'matched_user_id': match.matched_user_id,
        'matched_user_name': matched_user.name,
        'submitted_by': match.submitted_by,
        'timestamp': match.timestamp
    }), 201

@app.route('/api/prompts', methods=['GET'])
def get_prompts():
    prompts = Prompt.query.all()
    result = []
    
    for prompt in prompts:
        result.append({
            'id': prompt.id,
            'text': prompt.text,
            'created_by': prompt.created_by,
            'created_at': prompt.created_at
        })
    
    return jsonify(result)

@app.route('/api/prompts', methods=['POST'])
def create_prompt():
    data = request.json
    text = data.get('text')
    created_by = data.get('created_by')
    
    # Validate input
    if not text or not created_by:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Check if the creator exists
    creator = Student.query.get(created_by)
    if not creator:
        return jsonify({'error': 'Creator not found'}), 404
    
    # Create the prompt
    prompt = Prompt(
        text=text,
        created_by=created_by
    )
    
    db.session.add(prompt)
    db.session.commit()
    
    return jsonify({
        'id': prompt.id,
        'text': prompt.text,
        'created_by': prompt.created_by,
        'created_at': prompt.created_at
    }), 201

@app.route('/api/matches', methods=['GET'])
def get_matches():
    user_id = request.args.get('user_id', type=int)
    
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
    
    # Get matches submitted by the user
    submitted_matches = Match.query.filter_by(submitted_by=user_id).all()
    result = []
    
    for match in submitted_matches:
        prompt = Prompt.query.get(match.prompt_id)
        matched_user = Student.query.get(match.matched_user_id)
        
        result.append({
            'id': match.id,
            'prompt_id': match.prompt_id,
            'prompt_text': prompt.text if prompt else 'Unknown prompt',
            'matched_user_id': match.matched_user_id,
            'matched_user_name': matched_user.name if matched_user else 'Unknown user',
            'matched_user_profile_picture': matched_user.profile_picture if matched_user else '/static/img/default-profile.jpg',
            'submitted_by': match.submitted_by,
            'timestamp': match.timestamp
        })
    
    return jsonify(result)

@app.route('/matches')
@login_required
def matches_page():
    # Get student_id from query parameter or current user
    student_id = request.args.get('student_id', None, type=int)
    
    # If no student_id provided, use the current user's ID
    if not student_id and current_user.is_authenticated:
        student_id = current_user.id
        
    current_student = None
    
    if student_id:
        current_student = Student.query.get(student_id)
    
    # Get all students for the dropdown
    students = Student.query.all()
    
    return render_template('match.html', 
                          current_student=current_student,
                          students=students)

@app.route('/get_messages')
def get_messages_legacy():
    # Get user_id and other_id from query parameters
    user_id = request.args.get('user_id', None, type=int)
    other_id = request.args.get('other_id', None, type=int)
    
    if not user_id:
        return jsonify({'error': 'Missing user_id parameter'}), 400
    
    # Get all messages between the two users
    if other_id:
        # Get messages between the two users
        messages = Message.query.filter(
            ((Message.sender_id == user_id) & (Message.receiver_id == other_id)) |
            ((Message.sender_id == other_id) & (Message.receiver_id == user_id))
        ).order_by(Message.timestamp).all()
    else:
        # Get all messages for the user
        messages = Message.query.filter(
            (Message.sender_id == user_id) | (Message.receiver_id == user_id)
        ).order_by(Message.timestamp).all()
    
    # Mark messages as read if other_id is specified
    if other_id:
        unread_messages = Message.query.filter(
            (Message.receiver_id == user_id) & 
            (Message.sender_id == other_id) &
            (Message.read == False)
        ).all()
        
        for message in unread_messages:
            message.read = True
        
        db.session.commit()
    
    # Convert messages to JSON
    messages_json = [{
        'id': message.id,
        'sender_id': message.sender_id,
        'receiver_id': message.receiver_id,
        'content': message.content,
        'timestamp': message.timestamp.isoformat(),
        'read': message.read
    } for message in messages]
    
    return jsonify(messages_json)

@app.route('/api/unread_messages')
def unread_messages():
    # Get user_id from query parameters
    user_id = request.args.get('user_id', None, type=int)
    
    if not user_id:
        return jsonify({'error': 'Missing user_id parameter'}), 400
    
    # Get all unread messages for the user
    unread_messages = Message.query.filter(
        (Message.receiver_id == user_id) &
        (Message.read == False)
    ).all()
    
    # Group messages by sender
    unread_by_sender = {}
    for message in unread_messages:
        if message.sender_id not in unread_by_sender:
            sender = Student.query.get(message.sender_id)
            unread_by_sender[message.sender_id] = {
                'count': 0,
                'sender_name': sender.name if sender else 'Unknown',
                'sender_id': message.sender_id
            }
        unread_by_sender[message.sender_id]['count'] += 1
    
    return jsonify(list(unread_by_sender.values()))

@app.route('/api/messages', methods=['GET'])
def get_messages():
    # Get the user IDs from the query parameters
    user_id = request.args.get('user_id', type=int)
    other_id = request.args.get('other_id', type=int)
    
    if not user_id or not other_id:
        return jsonify({'error': 'Missing user IDs'}), 400
    
    # Get messages between the two users
    messages = Message.query.filter(
        ((Message.sender_id == user_id) & (Message.receiver_id == other_id)) |
        ((Message.sender_id == other_id) & (Message.receiver_id == user_id))
    ).order_by(Message.timestamp).all()
    
    # Mark messages as read if current user is the receiver
    for message in messages:
        if message.receiver_id == user_id and not message.read:
            message.read = True
    
    db.session.commit()
    
    # Format the messages
    result = []
    for message in messages:
        result.append({
            'id': message.id,
            'sender_id': message.sender_id,
            'receiver_id': message.receiver_id,
            'content': message.content,
            'timestamp': message.timestamp.isoformat(),
            'read': message.read
        })
    
    return jsonify(result)

@app.route('/api/messages', methods=['POST'])
def send_message():
    data = request.json
    sender_id = data.get('sender_id')
    receiver_id = data.get('receiver_id')
    content = data.get('content')
    
    # Validate input
    if not sender_id or not receiver_id or not content:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Check if the sender exists
    sender = Student.query.get(sender_id)
    if not sender:
        return jsonify({'error': 'Sender not found'}), 404
    
    # Check if the receiver exists
    receiver = Student.query.get(receiver_id)
    if not receiver:
        return jsonify({'error': 'Receiver not found'}), 404
    
    # Create the message
    message = Message(
        sender_id=sender_id,
        receiver_id=receiver_id,
        content=content
    )
    
    db.session.add(message)
    db.session.commit()
    
    return jsonify({
        'id': message.id,
        'sender_id': message.sender_id,
        'receiver_id': message.receiver_id,
        'content': message.content,
        'timestamp': message.timestamp.isoformat(),
        'read': message.read
    }), 201

@app.route('/messages')
@login_required
def messages_page():
    # Get student_id from query parameter or current user
    student_id = request.args.get('student_id', None, type=int)
    other_id = request.args.get('other_id', None, type=int)
    
    # If no student_id provided, use the current user's ID
    if not student_id and current_user.is_authenticated:
        student_id = current_user.id
        
    current_student = None
    other_student = None
    
    if student_id:
        current_student = Student.query.get(student_id)
    
    if other_id:
        other_student = Student.query.get(other_id)
    
    # Get all students for the dropdown
    students = Student.query.all()
    
    return render_template('messages.html', 
                          current_student=current_student,
                          other_student=other_student,
                          students=students)

@app.route('/recreate-db')
def recreate_db():
    with app.app_context():
        # Drop all tables
        db.drop_all()
        
        # Create all tables with the updated schema
        db.create_all()
        
        # Initialize with sample data
        if not Language.query.first():
            languages = ['English', 'Mandarin', 'Spanish', 'French', 'German', 'Japanese', 'Korean', 'Arabic', 'Russian', 'Hindi']
            for lang in languages:
                db.session.add(Language(name=lang))
        
        if not Interest.query.first():
            interests = ['Reading', 'Sports', 'Music', 'Art', 'Gaming', 'Cooking', 'Travel', 'Photography', 'Coding', 'Dancing']
            for interest in interests:
                db.session.add(Interest(name=interest))
        
        if not Club.query.first():
            clubs = ['Chess Club', 'Debate Society', 'Drama Club', 'Music Society', 'Sports Club', 'Coding Club', 'Photography Club', 'Art Club', 'Dance Club', 'Book Club']
            for club in clubs:
                db.session.add(Club(name=club))
        
        # Add sample prompts
        prompts = [
            "Who's the most helpful person this week?",
            "Who made you smile today?",
            "Most creative person this week?",
            "Who would you like to collaborate with?",
            "Who gave the best presentation recently?",
            "Who helped you learn something new?",
            "Who has the most interesting hobby?",
            "Who would you recommend as a study partner?",
            "Who has the most positive energy?",
            "Who would you like to know better?"
        ]
        
        # Add sample prompts if there are students
        students = Student.query.all()
        if students and not Prompt.query.first():
            for i, prompt_text in enumerate(prompts):
                # Use the first student as the creator for sample prompts
                creator_id = students[0].id if students else 1
                prompt = Prompt(text=prompt_text, created_by=creator_id)
                db.session.add(prompt)
                
        db.session.commit()
        
    return "Database recreated with updated schema and sample data!"

# Initialize the database when the app starts
with app.app_context():
    db.create_all()

# For local development
if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=8080)

# For Vercel deployment
app.wsgi_app
