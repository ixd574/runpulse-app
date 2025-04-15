#!/bin/bash

# Start the Flask application
cd /home/ubuntu/deployment/app
export PYTHONPATH=/home/ubuntu/deployment/lib:$PYTHONPATH
python3 app.py
