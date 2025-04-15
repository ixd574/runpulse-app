import os
import json
import re
import sys

# Add the lib directory to the Python path for dependencies
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

import markdown
from flask import Flask, request, render_template, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
import requests

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024  # 8MB max upload size
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx', 'doc', 'txt', 'csv', 'xls', 'xlsx', 'jpg', 'jpeg', 'png'}

# Create uploads folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# API key from environment
API_KEY = "rOMPNDmLDkgqFXtsySPU9LJX8fjJ78q4aF5OMZBj"

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Process file with API
        result = process_file(filepath)
        
        # Save result for viewing
        with open('result.json', 'w') as f:
            json.dump(result, f)
        
        # Return the result
        return jsonify(result)
    
    return jsonify({'error': 'File type not allowed'}), 400

def process_file(filepath):
    """Process the file using document parsing API and return the result"""
    file_extension = filepath.rsplit('.', 1)[1].lower()
    
    # Set content type based on file extension
    content_types = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'doc': 'application/msword',
        'txt': 'text/plain',
        'csv': 'text/csv',
        'xls': 'application/vnd.ms-excel',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png'
    }
    
    content_type = content_types.get(file_extension, 'application/octet-stream')
    
    # Prepare the API request
    url = 'https://api.runpulse.com/convert'
    headers = {
        'x-api-key': API_KEY,
        'Content-Type': content_type
    }
    
    try:
        with open(filepath, 'rb') as f:
            response = requests.post(url, headers=headers, data=f)
        
        if response.status_code == 200:
            # Get the presigned URL from the response
            presigned_url = response.json().get('presigned_url')
            
            # Use the presigned URL to extract the content
            extract_url = 'https://api.runpulse.com/extract'
            extract_headers = {
                'x-api-key': API_KEY,
                'Content-Type': 'application/json'
            }
            extract_data = {
                'file-url': presigned_url,
                'chunking': 'semantic,recursive',
                'return_table': True,
                'schema': {}
            }
            
            extract_response = requests.post(extract_url, headers=extract_headers, json=extract_data)
            
            if extract_response.status_code == 200:
                return extract_response.json()
            else:
                return {'error': f'Extract API error: {extract_response.text}'}
        else:
            return {'error': f'Convert API error: {response.text}'}
    
    except Exception as e:
        return {'error': f'Error processing file: {str(e)}'}

def clean_cell_content(cell):
    """Clean cell content by replacing carriage returns with spaces and trimming whitespace"""
    if cell is None:
        return ""
    
    # Convert to string if not already
    cell_str = str(cell)
    
    # Replace carriage returns and multiple spaces with a single space
    cleaned = re.sub(r'\r+', ' ', cell_str)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Trim whitespace
    cleaned = cleaned.strip()
    
    return cleaned

def detect_and_fix_table_structure(table_data):
    """Detect and fix table structure issues"""
    if not table_data or len(table_data) == 0:
        return table_data
    
    # Check if the first row contains large blocks of text that might be incorrectly parsed
    first_row = table_data[0]
    if len(first_row) > 0 and any(len(str(cell)) > 100 for cell in first_row):
        # This might be a malformed table, try to extract proper structure
        
        # Look for patterns that might indicate table headers and rows
        potential_headers = []
        potential_rows = []
        
        # Check if there are rows with consistent structure after the first row
        if len(table_data) > 1:
            # Use the second row as potential headers if it has a reasonable structure
            second_row = table_data[1]
            if len(second_row) >= 2 and all(len(str(cell)) < 100 for cell in second_row):
                potential_headers = second_row
                potential_rows = table_data[2:] if len(table_data) > 2 else []
            else:
                # Try to infer structure from the data
                # Find rows with 2 or more columns that look like key-value pairs
                for row in table_data[1:]:
                    if len(row) >= 2 and len(str(row[0])) < 50:  # Reasonable key length
                        potential_rows.append(row)
                
                if potential_rows:
                    # Use common column names for headers
                    potential_headers = ["Field", "Value"]
        
        # If we found potential headers and rows, use them
        if potential_headers and potential_rows:
            return [potential_headers] + potential_rows
    
    # If no issues detected or fixed, return original data
    return table_data

def format_markdown_from_json(json_data):
    """Convert JSON response to formatted markdown with improved table handling"""
    markdown_content = ""
    
    # Check for direct markdown field
    if 'markdown' in json_data and json_data['markdown']:
        markdown_content = json_data['markdown']
    
    # If no direct markdown or empty, try to build from chunks
    if not markdown_content and 'chunking' in json_data and isinstance(json_data['chunking'], dict):
        # Process semantic chunks if available
        if 'semantic' in json_data['chunking'] and isinstance(json_data['chunking']['semantic'], list):
            for chunk in json_data['chunking']['semantic']:
                if 'content' in chunk and chunk['content']:
                    markdown_content += chunk['content'] + "\n\n"
        
        # Process recursive chunks if available and semantic was empty
        if not markdown_content and 'recursive' in json_data['chunking'] and isinstance(json_data['chunking']['recursive'], list):
            for chunk in json_data['chunking']['recursive']:
                if 'content' in chunk and chunk['content']:
                    markdown_content += chunk['content'] + "\n\n"
        
        # Process page chunks if available and previous methods were empty
        if not markdown_content and 'page' in json_data['chunking'] and isinstance(json_data['chunking']['page'], list):
            for chunk in json_data['chunking']['page']:
                if 'content' in chunk and chunk['content']:
                    markdown_content += f"## Page {chunk.get('page_number', '')}\n\n{chunk['content']}\n\n"
        
        # Process header chunks if available and previous methods were empty
        if not markdown_content and 'header' in json_data['chunking'] and isinstance(json_data['chunking']['header'], list):
            for chunk in json_data['chunking']['header']:
                if 'content' in chunk and chunk['content']:
                    markdown_content += f"### {chunk.get('header', 'Section')}\n\n{chunk['content']}\n\n"
    
    # Process tables if available (always add tables regardless of other content)
    if 'tables' in json_data and isinstance(json_data['tables'], list) and json_data['tables']:
        table_content = "\n\n## Extracted Tables\n\n"
        has_tables = False
        
        for i, table in enumerate(json_data['tables']):
            if 'data' in table and isinstance(table['data'], list) and len(table['data']) > 0:
                has_tables = True
                table_content += f"### Table {i+1}\n\n"
                
                # Fix table structure if needed
                fixed_table_data = detect_and_fix_table_structure(table['data'])
                
                # Ensure we have data to work with
                if len(fixed_table_data) > 0:
                    # Get headers (first row) or generate placeholder headers
                    if len(fixed_table_data[0]) > 0:
                        headers = [clean_cell_content(h) for h in fixed_table_data[0]]
                    else:
                        # Generate column headers if missing
                        max_cols = max([len(row) for row in fixed_table_data])
                        headers = [f"Column {i+1}" for i in range(max_cols)]
                    
                    # Get rows (skip first row which is headers)
                    rows = fixed_table_data[1:] if len(fixed_table_data) > 1 else []
                    
                    # Table header
                    table_content += "| " + " | ".join(headers) + " |\n"
                    # Table separator
                    table_content += "| " + " | ".join(["---"] * len(headers)) + " |\n"
                    # Table rows
                    for row in rows:
                        # Clean each cell and pad row if needed to match header length
                        cleaned_row = [clean_cell_content(cell) for cell in row]
                        padded_row = cleaned_row + [""] * (len(headers) - len(cleaned_row))
                        table_content += "| " + " | ".join(padded_row) + " |\n"
                    
                    table_content += "\n\n"
        
        if has_tables:
            markdown_content += table_content
    
    # If no content was generated, return a message
    if not markdown_content.strip():
        return "No content available in the response."
    
    return markdown_content

@app.route('/view/<format_type>')
def view_result(format_type):
    """View the result in either JSON or markdown format"""
    try:
        with open('result.json', 'r') as f:
            result = json.load(f)
        
        if format_type == 'json':
            return render_template('view.html', format_type='json', content=json.dumps(result, indent=2))
        else:  # markdown
            markdown_content = format_markdown_from_json(result)
            html_content = markdown.markdown(markdown_content, extensions=['tables'])
            return render_template('view.html', format_type='markdown', content=html_content)
    
    except Exception as e:
        return jsonify({'error': f'Error viewing result: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
