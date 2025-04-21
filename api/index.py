from flask import Flask, jsonify

# Create a minimal Flask app for Vercel
app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'message': 'Welcome to BranchOut API',
        'status': 'online',
        'info': 'This is a minimal API for BranchOut',
        'github_repo': 'https://github.com/shrikha56/BranchOut'
    })

@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({
        'status': 'operational',
        'version': '1.0.0',
        'environment': 'production'
    })

