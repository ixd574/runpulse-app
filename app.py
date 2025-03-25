import os
import json
import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from functools import wraps
import time

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
        
        # Check if the file is a PDF (RunPulse API only accepts PDFs)
        if not file.filename.lower().endswith('.pdf'):
            app.logger.warning(f"Non-PDF file uploaded: {file.filename}")
            # Return a sample response with a warning for non-PDF files
            sample_response = {
                "markdown": "# API Limitation Notice\n\nThe RunPulse API only accepts PDF files. You uploaded a non-PDF file: " + file.filename,
                "chunking": {
                    "recursive": [
                        {
                            "chunk_number": 1,
                            "content": "# API Limitation Notice",
                            "length": 29,
                            "method": "recursive"
                        },
                        {
                            "chunk_number": 2,
                            "content": "The RunPulse API only accepts PDF files. You uploaded a non-PDF file: " + file.filename,
                            "length": 95,
                            "method": "recursive"
                        }
                    ],
                    "semantic": [
                        {
                            "chunk_number": 1,
                            "content": "The RunPulse API only accepts PDF files. You uploaded a non-PDF file: " + file.filename,
                            "length": 112,
                            "method": "semantic"
                        }
                    ]
                },
                "schema-json": {
                    "note": "This is sample data. The RunPulse API only accepts PDF files."
                },
                "tables": [],
                "plan-info": {
                    "note": "This is sample data. The RunPulse API only accepts PDF files."
                }
            }
            return jsonify(sample_response)
        
        # Save the file temporarily
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Step 1: Call the RunPulse API to upload the PDF
            upload_url = 'https://api.runpulse.com/convert'
            headers = {
                'x-api-key': API_KEY,
                'Content-Type': 'application/pdf'
            }
            
            with open(filepath, 'rb')  as f:
                file_data = f.read()
                
            # Make the API request to upload the file
            upload_response = requests.post(
                upload_url, 
                headers=headers, 
                data=file_data
            )
            
            # Check if the upload was successful
            if upload_response.status_code == 200:
                # Parse the response to get the S3 object URL
                upload_result = upload_response.json()
                app.logger.info(f"Upload response: {upload_result}")
                
                # Check if we received an S3 object URL
                if 's3_object_url' in upload_result:
                    s3_url = upload_result['s3_object_url']
                    app.logger.info(f"Document uploaded to: {s3_url}")
                    
                    # Step 2: Call the extract endpoint to parse the document
                    extract_url = 'https://api.runpulse.com/extract'
                    extract_headers = {
                        'x-api-key': API_KEY,
                        'Content-Type': 'application/json'
                    }
                    
                    # Prepare the request body for extraction
                    extract_data = {
                        'url': s3_url,
                        'return_markdown': True,
                        'chunking_method': ['semantic', 'recursive'],
                        'return_tables': True
                    }
                    
                    # Wait a moment for the file to be processed
                    time.sleep(2) 
                    
                    # Make the API request to extract content
                    extract_response = requests.post(
                        extract_url,
                        headers=extract_headers,
                        json=extract_data
                    )
                    
                    # Check if the extraction was successful
                    if extract_response.status_code == 200:
                        # Return the extracted content
                        return jsonify(extract_response.json())
                    else:
                        app.logger.error(f"Extraction failed with status code {extract_response.status_code}: {extract_response.text}")
                        return jsonify({
                            'error': f'Extraction failed with status code {extract_response.status_code}',
                            'message': extract_response.text
                        }), extract_response.status_code
                
                # If we couldn't get the S3 URL, return the upload response
                return jsonify(upload_result)
            else:
                # Log the error
                app.logger.error(f"Upload failed with status code {upload_response.status_code}: {upload_response.text}")
                
                # Return error information
                return jsonify({
                    'error': f'Upload failed with status code {upload_response.status_code}',
                    'message': upload_response.text
                }), upload_response.status_code
        
        except Exception as e:
            app.logger.error(f"Error calling API: {str(e)}")
            return jsonify({'error': f'Error calling API: {str(e)}'}), 500
        
        finally:
            # Clean up the temporary file
            if os.path.exists(filepath):
                os.remove(filepath)
    
    except Exception as e:
        app.logger.error(f"Error processing file: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
