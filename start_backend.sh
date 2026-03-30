#!/bin/bash
# Unset any stale env vars so .env file takes effect
unset OPENAI_API_KEY
cd "$(dirname "$0")/backend"
exec "../.venv/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8002 --reload
