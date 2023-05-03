#!/bin/bash

echo "Connect to http://127.0.0.1:8080"
parallel ::: 'poetry run python3 -m http.server 8080 --directory www' 'poetry run uvicorn api_server:app --reload'
