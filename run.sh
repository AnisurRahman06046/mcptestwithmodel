#!/bin/bash
# Start the server
uvicorn src.main:app --host 127.0.0.1 --port 8000
