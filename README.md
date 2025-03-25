# RunPulse Document Parser

A web application that processes documents using the RunPulse API and displays both the raw API output and a formatted version in a split-screen interface.

## Features

- File upload interface for document processing
- Integration with RunPulse API for document parsing
- Split-screen display showing:
  - Raw JSON output on the left
  - Formatted content on the right
- Support for various file types (with demo mode for non-PDF files)
- Markdown rendering of document content
- Display of chunking information, extracted schema, tables, and plan information

## Technical Details

- Built with Flask (Python web framework)
- Uses the RunPulse API for document processing
- Frontend built with HTML, CSS, and JavaScript
- Bootstrap for responsive design
- Marked.js for markdown rendering

## Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install flask requests python-dotenv
   ```
3. Run the application:
   ```
   python app.py
   ```

## Usage

1. Access the application at http://localhost:5000
2. Upload a document (PDF, DOCX, TXT, etc.)
3. View the results in the split-screen display

## API Integration

The application integrates with two RunPulse API endpoints:
- `/convert`: For direct file uploads (up to 8MB)
- `/extract`: For processing documents via URL

Note: The RunPulse API only accepts PDF files for actual processing. For non-PDF files, the application provides sample output to demonstrate functionality.

## Response Format

The RunPulse API returns JSON responses containing:
- Markdown content from the document
- Chunked content based on specified methods (semantic, recursive, page, header)
- Schema-based extracted data
- Tables extracted from the document
- Plan information including usage metrics
