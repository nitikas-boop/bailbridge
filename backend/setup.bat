@echo off
REM BailBridge - Backend Setup Script (Windows Batch)
REM Finalized for Phase 2 Production Readiness

echo >>> Setting up BailBridge Backend...

REM 1. Create necessary directories
echo >>> Creating folder structure...
if not exist "storage\evidence" mkdir "storage\evidence"
if not exist "knowledge_base" mkdir "knowledge_base"

REM 2. Install dependencies
echo >>> Installing dependencies...
py -m pip install -r requirements.txt

REM 3. Setup environment variables
if not exist ".env" (
    echo >>> Creating .env from .env.example...
    copy .env.example .env
    echo !!! IMPORTANT: Please update the .env file with your API keys and Firebase credentials.
) else (
    echo >>> .env file already exists.
)

echo >>> Setup Complete!
echo >>> Run 'py main.py' to start the server.
pause
