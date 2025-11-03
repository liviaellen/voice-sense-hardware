# Quick Start Guide: Omi + Hume AI Integration

This guide will help you get started quickly with receiving audio from your Omi device and analyzing emotions with Hume AI.

## Prerequisites Checklist

- [ ] Omi DevKit1 or DevKit2 device
- [ ] Google Cloud account with billing enabled
- [ ] Hume AI account ([Sign up here](https://www.hume.ai/))
- [ ] Python 3.11+ installed

## Step-by-Step Setup (15 minutes)

### 1. Clone and Setup Project (2 minutes)

```bash
cd /path/to/your/projects
# If you haven't already, create the directory
mkdir omi-audio && cd omi-audio

# Install dependencies
pip install -r requirements.txt
```

### 2. Google Cloud Storage Setup (5 minutes)

```bash
# Create a GCS bucket (replace with your unique bucket name)
gsutil mb gs://my-omi-audio-bucket

# Create service account
gcloud iam service-accounts create omi-audio-service \
    --display-name="Omi Audio Service Account"

# Grant permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:omi-audio-service@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectCreator"

# Create and download key
gcloud iam service-accounts keys create credentials.json \
    --iam-account=omi-audio-service@YOUR_PROJECT_ID.iam.gserviceaccount.com

# Encode credentials to base64
base64 -i credentials.json -o credentials-base64.txt
```

### 3. Get Your Hume AI API Key (2 minutes)

1. Go to [Hume AI Dashboard](https://platform.hume.ai/)
2. Sign in or create an account
3. Navigate to API Keys section
4. Click "Create API Key"
5. Copy the key (you won't be able to see it again!)

### 4. Configure Environment Variables (1 minute)

```bash
# Copy the example file
cp .env.example .env

# Edit .env file
# Set these values:
# - GOOGLE_APPLICATION_CREDENTIALS_JSON (from credentials-base64.txt)
# - GCS_BUCKET_NAME (e.g., my-omi-audio-bucket)
# - HUME_API_KEY (from Hume AI dashboard)
```

### 5. Run the Service Locally (1 minute)

```bash
# Load environment variables
export $(cat .env | xargs)

# Run the server
python main.py
```

You should see:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8080
```

### 6. Test the Service (2 minutes)

In a new terminal:

```bash
# Health check
curl http://localhost:8080/health

# Expected response:
# {"status":"healthy","service":"omi-audio-streaming"}
```

### 7. Configure Omi App (2 minutes)

For local testing with ngrok:

```bash
# Install ngrok if you haven't: https://ngrok.com/download
ngrok http 8080
```

Then in the Omi App:
1. Open **Settings**
2. Enable **Developer Mode**
3. Scroll to **Realtime audio bytes**
4. Enter your endpoint: `https://YOUR-NGROK-URL.ngrok.io/audio`
5. Set **Every x seconds** to `10` (or your preferred interval)
6. Save

### 8. Start Receiving Audio!

Your Omi device will now send audio every 10 seconds to your endpoint. Check your terminal logs to see:
- Audio received
- Hume analysis results
- GCS upload confirmation

## Example Response

When your Omi device sends audio, you'll get a response like:

```json
{
  "message": "Audio processed successfully",
  "filename": "user123_20250102_143022_123456.wav",
  "gcs_path": "gs://my-omi-audio-bucket/user123_20250102_143022_123456.wav",
  "uid": "user123",
  "sample_rate": 16000,
  "data_size_bytes": 160000,
  "timestamp": "20250102_143022_123456",
  "hume_analysis": {
    "success": true,
    "total_predictions": 2,
    "predictions": [
      {
        "time": {"begin": 0.0, "end": 2.5},
        "emotions": [
          {"name": "Joy", "score": 0.85},
          {"name": "Excitement", "score": 0.72},
          {"name": "Interest", "score": 0.68}
        ]
      },
      {
        "time": {"begin": 2.5, "end": 5.0},
        "emotions": [
          {"name": "Calmness", "score": 0.78},
          {"name": "Contentment", "score": 0.65}
        ]
      }
    ]
  }
}
```

## Deploy to Production

### Option 1: Google Cloud Run (Recommended)

```bash
# Build and push
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/omi-audio-streaming

# Deploy
gcloud run deploy omi-audio-streaming \
  --image gcr.io/YOUR_PROJECT_ID/omi-audio-streaming \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_APPLICATION_CREDENTIALS_JSON=$(cat credentials-base64.txt) \
  --set-env-vars GCS_BUCKET_NAME=my-omi-audio-bucket \
  --set-env-vars HUME_API_KEY=your_hume_api_key

# Get your URL
gcloud run services describe omi-audio-streaming --region us-central1 --format 'value(status.url)'
```

Then update your Omi app with the Cloud Run URL + `/audio`

### Option 2: Docker Anywhere

```bash
# Build
docker build -t omi-audio-streaming .

# Run
docker run -d -p 8080:8080 \
  -e GOOGLE_APPLICATION_CREDENTIALS_JSON="$(cat credentials-base64.txt)" \
  -e GCS_BUCKET_NAME="my-omi-audio-bucket" \
  -e HUME_API_KEY="your_hume_api_key" \
  --name omi-audio \
  omi-audio-streaming

# Check logs
docker logs -f omi-audio
```

## Monitoring Your Data

### View Files in GCS

```bash
# List all audio files
gsutil ls gs://my-omi-audio-bucket/

# Download a file
gsutil cp gs://my-omi-audio-bucket/user123_20250102_143022_123456.wav ./
```

### Access GCS Console

Visit: https://console.cloud.google.com/storage/browser/my-omi-audio-bucket

## Common Issues

### "Connection refused" when testing
- Make sure the server is running (`python main.py`)
- Check if port 8080 is available
- Try `curl http://127.0.0.1:8080/health` instead

### "HUME_API_KEY environment variable not set"
- Verify `.env` file has `HUME_API_KEY=...`
- Make sure you ran `export $(cat .env | xargs)`
- Check no extra spaces around the `=` sign

### No audio received from Omi
- Verify ngrok is running and URL is correct
- Check Omi app settings have the correct endpoint
- Ensure Omi device is connected to internet
- Try restarting the Omi app

### Hume analysis returns errors
- Verify your Hume API key is valid
- Check you haven't exceeded rate limits
- Ensure audio file is long enough (>100ms recommended)

## Next Steps

- Build a dashboard to visualize emotion trends over time
- Set up a database to store emotion data for analysis
- Create alerts for specific emotional patterns
- Integrate with other services (Slack notifications, etc.)
- Fine-tune emotion thresholds for your use case

## Need Help?

- Check the main [README.md](README.md) for detailed documentation
- Review [Hume AI Documentation](https://docs.hume.ai/)
- Check [Omi Documentation](https://docs.omi.me/)

Happy emotion tracking! 🎭
