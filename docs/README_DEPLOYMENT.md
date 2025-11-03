# Omi Audio Streaming Server Deployment Guide

This server receives real-time audio from your Omi device, analyzes emotions using Hume AI, and optionally stores audio in Google Cloud Storage.

## Prerequisites

1. **Python 3.9+** with dependencies installed:
   ```bash
   pip install -r requirements.txt
   ```

2. **Hume AI API Key** (Required):
   - Get your API key from [Hume AI Platform](https://platform.hume.ai/)

3. **Ngrok** (for local development):
   - Already installed at: `/opt/homebrew/bin/ngrok`
   - Or download from: https://ngrok.com/download

4. **Google Cloud Storage** (Optional):
   - Only needed if you want to store audio files

## Quick Start

### Option 1: Automatic Setup (Easiest)

1. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your HUME_API_KEY
   ```

2. **Run the startup script:**
   ```bash
   ./start_server.sh
   ```

   This will:
   - Start the FastAPI server on port 8080
   - Create an ngrok tunnel
   - Display your public URL

3. **Configure your Omi device** (see Configuration section below)

### Option 2: Manual Setup (More Control)

1. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env and add your HUME_API_KEY
   source .env
   ```

2. **Start the server** (Terminal 1):
   ```bash
   python main.py
   ```

3. **Start ngrok tunnel** (Terminal 2):
   ```bash
   ngrok http 8080
   ```

   Copy the HTTPS URL shown (e.g., `https://abc123.ngrok-free.app`)

4. **Configure your Omi device** (see Configuration section below)

## Omi Device Configuration

1. Open the **Omi App** on your phone
2. Go to **Settings** → **Developer Mode**
3. Find **"Realtime audio bytes"** setting
4. Enter your endpoint URL:
   ```
   https://your-ngrok-url.ngrok-free.app/audio
   ```
5. Set **"Every x seconds"** to your desired interval (e.g., `10` for every 10 seconds)
6. Save the settings

## API Endpoints

### `POST /audio`

Receives audio stream from Omi device.

**Query Parameters:**
- `sample_rate` (required): Audio sample rate (8000 or 16000 Hz)
- `uid` (required): User unique identifier
- `analyze_emotion` (optional): Enable Hume AI analysis (default: `true`)
- `save_to_gcs` (optional): Save to Google Cloud Storage (default: `true`)

**Example:**
```
POST https://your-url.ngrok-free.app/audio?sample_rate=16000&uid=user123
Content-Type: application/octet-stream

[binary audio data]
```

**Response:**
```json
{
  "message": "Audio processed successfully",
  "filename": "user123_20250102_143021_123456.wav",
  "uid": "user123",
  "sample_rate": 16000,
  "data_size_bytes": 32000,
  "timestamp": "20250102_143021_123456",
  "gcs_path": "gs://your-bucket/user123_20250102_143021_123456.wav",
  "hume_analysis": {
    "success": true,
    "predictions": [
      {
        "time": {"begin": 0.0, "end": 2.5},
        "emotions": [
          {"name": "Joy", "score": 0.82},
          {"name": "Interest", "score": 0.65},
          {"name": "Calmness", "score": 0.54}
        ]
      }
    ],
    "total_predictions": 1
  }
}
```

### `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "omi-audio-streaming"
}
```

## Environment Variables

### Required

- `HUME_API_KEY`: Your Hume AI API key

### Optional (for Google Cloud Storage)

- `GOOGLE_APPLICATION_CREDENTIALS_JSON`: Base64-encoded GCP service account credentials
- `GCS_BUCKET_NAME`: Name of your GCS bucket

To disable GCS storage, set `save_to_gcs=false` in the Omi device URL:
```
https://your-url.ngrok-free.app/audio?save_to_gcs=false
```

## Monitoring

### Server Logs
```bash
# If using start_server.sh
tail -f server.log

# If running manually
# Logs appear in the terminal where you ran python main.py
```

### Ngrok Dashboard
Open http://localhost:4040 in your browser to see:
- Request history
- Request/response details
- Traffic statistics

### Test Your Endpoint
```bash
# Health check
curl https://your-ngrok-url.ngrok-free.app/health

# Test audio upload (with sample audio file)
curl -X POST "https://your-ngrok-url.ngrok-free.app/audio?sample_rate=16000&uid=test_user" \
  -H "Content-Type: application/octet-stream" \
  --data-binary "@sample_audio.wav"
```

## Troubleshooting

### Import Errors
Make sure you're using Hume SDK v0.13.1+:
```bash
pip install --upgrade hume
```

### Server Won't Start
1. Check if port 8080 is already in use:
   ```bash
   lsof -i :8080
   ```
2. Check server.log for errors
3. Verify your .env file is configured correctly

### Ngrok Connection Issues
1. Make sure ngrok is authenticated:
   ```bash
   ngrok config add-authtoken <your-token>
   ```
2. Check if port 4040 (ngrok dashboard) is available

### No Emotion Results
1. Verify your HUME_API_KEY is valid
2. Check that audio files are valid WAV format
3. Audio should be at least 0.5 seconds long
4. Check server logs for Hume API errors

## Production Deployment

For production use, deploy to:
- **Google Cloud Run** (recommended for GCP)
- **AWS Lambda + API Gateway**
- **DigitalOcean App Platform**
- **Railway / Render / Fly.io**

Replace ngrok URL with your production domain in the Omi app settings.

## Support

- Omi Documentation: https://docs.omi.me/
- Hume AI Documentation: https://dev.hume.ai/docs
- GitHub Issues: (your repository URL)
