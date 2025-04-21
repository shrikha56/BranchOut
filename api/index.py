from flask import Flask, redirect, url_for
import sys
import os

# Add the parent directory to the path so we can import from the parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Flask app
from app import app as flask_app

# This is the handler for Vercel serverless function
app = flask_app
