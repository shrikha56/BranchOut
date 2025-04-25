from flask import Flask, request, redirect, url_for, session
import requests
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "development-key")

# Your client credentials and redirect URI
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = "https://branchout.onrender.com/authorize"

# Google OAuth endpoints
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

@app.route('/')
def index():
    return '<a href="/login">Login with Google</a>'

@app.route('/login')
def login():
    # Generate a state parameter for CSRF protection
    state = os.urandom(16).hex()
    session['oauth_state'] = state
    
    # Build the authorization URL
    scope = "openid email profile"
    auth_params = {
        "response_type": "code",
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": scope,
        "state": state,
        "access_type": "offline",
        "prompt": "consent"
    }
    
    auth_url = f"{AUTH_URL}?" + "&".join([f"{k}={v}" for k, v in auth_params.items()])
    logger.info(f"Redirecting to: {auth_url}")
    
    return redirect(auth_url)

@app.route('/authorize')
def authorize():
    # Log all request parameters for debugging
    logger.info(f"Received callback with args: {request.args}")
    
    # Check for errors
    if "error" in request.args:
        error = request.args.get("error")
        error_description = request.args.get("error_description", "No description provided")
        logger.error(f"OAuth error: {error} - {error_description}")
        return f"Error: {error} - {error_description}", 400
    
    # Verify state parameter
    state = request.args.get("state")
    if state != session.get("oauth_state"):
        logger.error(f"State mismatch: {state} vs {session.get('oauth_state')}")
        return "Invalid state parameter", 400
    
    # Get authorization code
    code = request.args.get("code")
    if not code:
        logger.error("No authorization code received")
        return "No authorization code received", 400
    
    # Exchange code for tokens
    logger.info(f"Exchanging code for token with redirect_uri: {REDIRECT_URI}")
    
    try:
        token_response = requests.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code"
            }
        )
        
        logger.info(f"Token response status: {token_response.status_code}")
        
        # Check if we received a valid response
        if token_response.status_code == 200:
            token_info = token_response.json()
            access_token = token_info.get("access_token")
            
            # Get user info
            userinfo_response = requests.get(
                USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if userinfo_response.status_code == 200:
                user_info = userinfo_response.json()
                logger.info(f"User info: {user_info}")
                return f"Successfully authenticated as: {user_info.get('email')}"
            else:
                logger.error(f"Error getting user info: {userinfo_response.text}")
                return f"Error getting user info: {userinfo_response.text}", 400
        else:
            logger.error(f"Error getting token: {token_response.text}")
            return f"Error getting token: {token_response.text}", 400
    except Exception as e:
        logger.exception("Exception during token exchange")
        return f"Exception during token exchange: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True, port=8081)
