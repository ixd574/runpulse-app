import os
import json
import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from functools import wraps

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024  # 8MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx', 'doc', 'txt', 'jpg', 'jpeg', 'png'}
app.secret_key = 'runpulse_secret_key'  # Required for session

# Password for authentication
PASSWORD = "17lyalin"

# Create uploads folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# API key from environment variable or directly set
API_KEY = "rOMPNDmLDkgqFXtsySPU9LJX8fjJ78q4aF5OMZBj"

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['password'] == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            error = 'Invalid password. Please try again.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/parse', methods=['POST'])
@login_required
def parse_document():
    try:
        # Add debug logging
        app.logger.info("Received parse request")
        
        # Check if a file was uploaded
        if 'file' not in request.files:
            app.logger.error("No file part in request")
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        
        # Check if the file is empty
        if file.filename == '':
            app.logger.error("No selected file")
            return jsonify({'error': 'No selected file'}), 400
        
        # Log file information
        app.logger.info(f"File received: {file.filename}")
        
        # Always return a sample response for demonstration
        sample_response = {
            "markdown": "# Sample Purchase Order\n\n**Example Company Inc** \n123 Main Street \nUnit 2 \nBoston Massachusetts 02101 \nUSA \n\n---\n\n**Purchase Order** \n**# PO-12345**",
            "chunking": {
                "recursive": [
                    {
                        "chunk_number": 1,
                        "content": "# Sample Purchase Order",
                        "length": 29,
                        "method": "recursive"
                    },
                    {
                        "chunk_number": 2,
                        "content": "**Example Company Inc** \n123 Main Street \nUnit 2 \nBoston Massachusetts 02101",
                        "length": 95,
                        "method": "recursive"
                    }
                ],
                "semantic": [
                    {
                        "chunk_number": 1,
                        "content": "Sample Purchase Order from Example Company Inc located at 123 Main Street, Unit 2, Boston Massachusetts 02101",
                        "length": 112,
                        "method": "semantic"
                    }
                ]
            },
            "schema-json": {
                "company": "Example Company Inc",
                "purchase_order_number": "PO-12345",
                "address": {
                    "street": "123 Main Street",
                    "unit": "Unit 2",
                    "city": "Boston",
                    "state": "Massachusetts",
                    "zip": "02101",
                    "country": "USA"
                }
            },
            "tables": [
                {
                    "table_id": 1,
                    "content": "| # | Item & Description | Qty | Rate | Amount |\n|----|-------------------|------|----------|----------|\n| 1 | Setup Fee | 1.00 | 1,000.00 | 1,000.00 |\n| 2 | Product A | 50.00| 30.00 | 1,500.00 |"
                }
            ],
            "plan-info": {
                "pages_used": 19998,
                "tier": "foundation"
            }
        }
        return jsonify(sample_response)
        
    except Exception as e:
        app.logger.error(f"Error processing file: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
