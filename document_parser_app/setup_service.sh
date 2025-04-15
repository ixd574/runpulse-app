#!/bin/bash

# Make the run script executable
chmod +x /home/ubuntu/deployment/run.sh

# Create a systemd service file for the application
cat > /tmp/document-parser.service << EOF
[Unit]
Description=Document Parsing Application
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/deployment/app
Environment="PYTHONPATH=/home/ubuntu/deployment/lib"
ExecStart=/usr/bin/python3 /home/ubuntu/deployment/app/app.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Instructions for installing the service
echo "To install as a system service, run:"
echo "sudo cp /tmp/document-parser.service /etc/systemd/system/"
echo "sudo systemctl daemon-reload"
echo "sudo systemctl enable document-parser.service"
echo "sudo systemctl start document-parser.service"
