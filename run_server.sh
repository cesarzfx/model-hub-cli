#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start the FastAPI server
python -m uvicorn src.api.main:app --reload