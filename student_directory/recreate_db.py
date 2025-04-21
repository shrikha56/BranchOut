from app import app, db
from models.models import Language, Interest, Club

# Run this script to recreate the database with the updated schema
with app.app_context():
    # Drop all tables
    db.drop_all()
    
    # Create all tables with the updated schema
    db.create_all()
    
    # Initialize with sample data
    languages = ['English', 'Mandarin', 'Spanish', 'French', 'German', 'Japanese', 'Korean', 'Arabic', 'Russian', 'Hindi']
    for lang in languages:
        db.session.add(Language(name=lang))
    
    interests = ['Reading', 'Sports', 'Music', 'Art', 'Gaming', 'Cooking', 'Travel', 'Photography', 'Coding', 'Dancing']
    for interest in interests:
        db.session.add(Interest(name=interest))
    
    clubs = ['Chess Club', 'Debate Society', 'Drama Club', 'Music Society', 'Sports Club', 'Coding Club', 'Photography Club', 'Art Club', 'Dance Club', 'Book Club']
    for club in clubs:
        db.session.add(Club(name=club))
            
    db.session.commit()
    
    print("Database recreated with updated schema and sample data!")