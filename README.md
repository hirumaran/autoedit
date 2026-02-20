# AI Video Editor MVP

A FastAPI-based AI-powered video editing system that transcribes, analyzes, and edits videos automatically.

## Features

- Video upload and processing
- Automatic transcription using Whisper
- AI analysis with GPT-4o for editing decisions
- Basic video edits: trimming, subtitles
- Simple web interface

## Setup

1. Install dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. Install FFmpeg (system-level):
   - macOS: `brew install ffmpeg`
   - Ubuntu: `sudo apt-get install ffmpeg`
   - Windows: Download from https://ffmpeg.org/download.html

3. Set your OpenAI API key in `backend/.env`

4. Run the application (from the repo root):
   ```bash
   chmod +x run.sh   # first time only
   ./run.sh
   ```

5. Open http://localhost:8000 in your browser

## API Endpoints

- `POST /api/upload` - Upload video
- `POST /api/process` - Start processing
- `GET /api/status/{video_id}` - Check status
- `GET /api/download/{video_id}` - Download result
- `GET /api/analysis/{video_id}` - Get AI analysis
# autoedit
