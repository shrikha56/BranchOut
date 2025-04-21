# BranchOut

A web application for connecting students based on shared interests, clubs, and languages, helping them branch out and build meaningful connections.

## Features

- Student information collection form
- Directory with advanced filtering capabilities
- Filter by faculty, interests, clubs, and languages spoken
- Name validation against filtered results
- Find students in the same faculty

## Database Schema

```sql
-- Students Table
students (
  id SERIAL PRIMARY KEY,
  name TEXT,
  year INT,
  faculty TEXT
)

-- Interests
interests (id SERIAL PRIMARY KEY, name TEXT)
student_interests (student_id INT, interest_id INT)

-- Clubs
clubs (id SERIAL PRIMARY KEY, name TEXT)
student_clubs (student_id INT, club_id INT)

-- Languages
languages (id SERIAL PRIMARY KEY, name TEXT)
student_languages (student_id INT, language_id INT)
```

## Setup Instructions

1. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up Google OAuth credentials:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Navigate to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Select "Web application" as the application type
   - Add authorized redirect URIs: `http://localhost:8080/authorize`
   - Copy the Client ID and Client Secret
   - Create a `.env` file in the project root with the following content:
     ```
     FLASK_APP=app.py
     FLASK_ENV=development
     SECRET_KEY=your-secret-key-goes-here
     GOOGLE_CLIENT_ID=your-google-client-id
     GOOGLE_CLIENT_SECRET=your-google-client-secret
     ```

4. Initialize the database:
   ```
   python app.py
   ```
   Then visit http://localhost:8080/recreate-db in your browser

5. Run the application:
   ```
   python app.py
   ```

6. Access the application at http://localhost:8080

## Usage

1. Submit student information through the form
2. Navigate to the directory to view all students
3. Use filters to find specific students
4. Use the prompt "Find someone in the same faculty as you" by entering your name
5. Validate names against the filtered results
