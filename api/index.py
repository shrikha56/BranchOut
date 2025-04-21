from flask import Flask, jsonify
import sys
import os

# Add the parent directory to the path so we can import from the parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create a simple Flask app for Vercel
app = Flask(__name__)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return jsonify({
        'message': 'Welcome to BranchOut API',
        'status': 'online',
        'info': 'This is a serverless API for BranchOut. The full application requires a database and is not suitable for serverless deployment.',
        'github_repo': 'https://github.com/shrikha56/BranchOut',
        'deployment_guide': 'For proper deployment, please use a platform that supports persistent storage like Heroku, Railway, or Render.'
    })

# This is the handler for Vercel serverless function
if __name__ == '__main__':
    app.run(debug=True)
