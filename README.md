# 🎭 Real-time Voice Emotion Analysis

A Python FastAPI service that receives real-time audio streams, analyzes emotions using Hume EVI API, sends automatic notifications, and provides a beautiful dashboard with emotion statistics.

**Powered by [Hume EVI API](https://www.hume.ai/) | Demo performed with [Omi AI Voice](https://www.omi.me/)**

## 📸 Screenshots

### Dashboard
![Emotion Meter Dashboard](./image/emotion-meter.png)

### Mobile App Notification
<img src="./image/omi phone ss.png" alt="Mobile Notification" width="300"/>

## ✨ Features

- 🎤 **Real-time Audio Streaming** from Omi device or any compatible device
- 🧠 **Emotion Analysis** using Hume EVI API's Speech Prosody & Language models
- 📱 **Automatic Notifications** when emotions are detected
- 📊 **Live Dashboard** with emotion statistics and percentages
- ⚙️ **Configurable Thresholds** for emotion detection
- 📈 **Emotion Tracking** with cumulative counts and visualizations
- 🔄 **Auto-chunking** for audio files longer than 5 seconds
- 🗑️ **Statistics Reset** button on dashboard
- 💾 **Optional GCS Storage** for audio archives
- 🐳 **Docker Support** for easy deployment

## 🚀 Quick Start

### 1. Get Your API Keys

#### Hume EVI API (Required)
1. Sign up at [Hume AI](https://www.hume.ai/)
2. Create an API key from your dashboard
3. Copy your key

#### Notification Integration (Optional)
1. Configure your notification service integration
2. Set up your **App ID** and **API Key**
3. Notifications will be sent when emotions are detected

### 2. Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

**Set these environment variables in Render:**

```bash
# Required
HUME_API_KEY=your_hume_api_key
OMI_APP_ID=your_omi_app_id
OMI_API_KEY=your_omi_api_key

# Optional (for GCS storage)
GCS_BUCKET_NAME=your_bucket_name
GOOGLE_APPLICATION_CREDENTIALS_JSON=base64_encoded_credentials
```

### 3. Configure Your Omi Device

#### For Omi Device Users:
1. Open the **Omi App**
2. Go to **Settings → Developer Mode**
3. Set **"Realtime audio bytes"** to:
```
https://your-app-name.onrender.com/audio
```
4. Set **"Every x seconds"** to `10`

#### For Other Devices:
Configure your audio streaming device to send real-time audio to the endpoint above.

That's it! The service will automatically analyze emotions and send notifications! 🎉

## 🎯 How It Works

```
User speaks → Omi Device/Audio Device → Sends to your server
                                              ↓
                                   Analyze with Hume EVI API
                                              ↓
                                   Detect emotions in top 3
                                              ↓
                                   Match against configured list
                                              ↓
                             Send notification automatically!
                                              ↓
                             📱 User receives emotion alert
```

## 📱 Notification System

### Automatic Notifications

By default, notifications are sent for **ALL emotions** detected in the top 3. The system is configured in `emotion_config.json`:

```json
{
  "notification_enabled": true,
  "emotion_thresholds": {},
  "notification_message_template": "🎭 Emotion Alert: Detected {emotions}"
}
```

**Empty thresholds = notify for ALL top 3 emotions!**

### Customize Which Emotions Trigger Notifications

Edit `emotion_config.json` to notify only for specific emotions:

```json
{
  "notification_enabled": true,
  "emotion_thresholds": {
    "Joy": 0.5,
    "Anger": 0.6,
    "Sadness": 0.5
  }
}
```

### Configuration Methods

**Method 1: File (Recommended)**
- Edit `emotion_config.json`
- Commit and redeploy

**Method 2: API**
```bash
# View config
curl https://your-app.onrender.com/emotion-config

# Update config
curl -X POST https://your-app.onrender.com/emotion-config \
  -H "Content-Type: application/json" \
  -d '{"notification_enabled": true, "emotion_thresholds": {"Joy": 0.5}}'
```

**Method 3: Environment Variable**
```bash
EMOTION_NOTIFICATION_CONFIG={"notification_enabled":true,"emotion_thresholds":{"Anger":0.7}}
```

## 📊 Dashboard Features

Access at: `https://your-app.onrender.com/`

### What You'll See:

- ✅ **Configuration Status** - Hume AI & GCS setup
- 📈 **Request Statistics** - Total, successful, failed analyses
- 🕒 **Last Activity** - Most recent request with emotions
- 🎭 **Emotion Statistics** - Cumulative counts and percentages with visual bars
- 🗑️ **Reset Button** - Clear all statistics
- 🔄 **Auto-refresh** - Updates every 10 seconds

### Example Dashboard View:

```
🎭 Emotion Meter - Real-time Voice Analysis ONLINE

⚙️ Configuration Status
✓ Hume AI API Key: Configured
✗ Google Cloud Storage: Not configured (optional)

16 Total Requests | 12 Successful | 4 Failed

📊 Last Activity
Time: 2025-11-02 18:52:54 UTC
User ID: XqBK****
[Joy (0.23)] [Calmness (0.18)] [Interest (0.15)]

🎭 Emotion Statistics
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Joy            Count: 15 | 25.0% ████████████████
Calmness       Count: 12 | 20.0% ██████████████
Interest       Count: 10 | 16.7% ████████████
Excitement     Count: 8  | 13.3% █████████
Satisfaction   Count: 7  | 11.7% ████████
```

## 🔧 API Endpoints

### POST /audio
Receives and analyzes audio from streaming device.

**Query Parameters:**
- `sample_rate` (required): 8000 or 16000 Hz
- `uid` (required): User ID
- `analyze_emotion` (optional, default: true)
- `save_to_gcs` (optional, default: true)
- `send_notification` (optional, uses config default)
- `emotion_filters` (optional, JSON): Override config filters

**Example:**
```bash
curl -X POST "https://your-app.onrender.com/audio?sample_rate=16000&uid=user123" \
  -H "Content-Type: application/octet-stream" \
  --data-binary "@audio.wav"
```

### POST /analyze-text
Analyzes emotion from text content.

**Body:**
```json
{
  "text": "I am so excited about this project!"
}
```

**Response:**
```json
{
  "success": true,
  "emotions": [
    {"name": "Excitement", "score": 0.85},
    {"name": "Joy", "score": 0.72},
    {"name": "Interest", "score": 0.65}
  ]
}
```

### GET /emotion-config
View current notification configuration.

### POST /emotion-config
Update notification configuration.

### POST /reset-stats
Reset all statistics (confirmation required).

### GET /status
Get server status and statistics (JSON).

### GET /health
Health check endpoint.

## 🎭 Available Emotions

Hume AI detects 48+ emotions including:

**Positive:** Joy, Amusement, Satisfaction, Excitement, Pride, Triumph, Relief, Romance, Desire, Admiration, Adoration

**Negative:** Anger, Sadness, Fear, Disgust, Anxiety, Distress, Shame, Guilt, Embarrassment, Contempt

**Neutral:** Calmness, Concentration, Contemplation, Determination, Interest, Surprise, Confusion, Realization

## 📋 Configuration Examples

### Example 1: Safety Monitoring
```json
{
  "emotion_thresholds": {
    "Anger": 0.8,
    "Fear": 0.85,
    "Distress": 0.8
  }
}
```
→ Only high-intensity negative emotions

### Example 2: Mental Health Support
```json
{
  "emotion_thresholds": {
    "Sadness": 0.5,
    "Anxiety": 0.55,
    "Distress": 0.5
  }
}
```
→ Early detection of emotional distress

### Example 3: Positive Reinforcement
```json
{
  "emotion_thresholds": {
    "Joy": 0.7,
    "Pride": 0.75,
    "Triumph": 0.8
  }
}
```
→ Celebrate achievements!

### Example 4: All Emotions (Default)
```json
{
  "emotion_thresholds": {}
}
```
→ Notify for ALL top 3 emotions

## 🐳 Local Development

### Prerequisites
- Python 3.11+
- ffmpeg (for audio processing)

### Setup

```bash
# Clone repo
git clone <your-repo-url>
cd audio-sentiment-profiling

# Install dependencies
pip install -r requirements.txt

# Install ffmpeg
brew install ffmpeg  # macOS
# or
sudo apt-get install ffmpeg  # Linux

# Create .env file
cp .env.example .env

# Edit .env with your keys
nano .env
```

### Run Locally

```bash
python main.py
```

Server runs at `http://localhost:8080`

### Test with ngrok

```bash
# In one terminal
python main.py

# In another terminal
ngrok http 8080

# Use ngrok URL in Omi app
```

## 🔍 Troubleshooting

### No Notifications Received?

**Check 1: Render Environment Variables**
```bash
# Verify these are set in Render Dashboard → Environment:
OMI_APP_ID=...
OMI_API_KEY=...
```

**Check 2: App Enabled**
- Open your notification app
- Make sure the integration is **ENABLED**

**Check 3: Check Logs**
Look for in Render logs:
```
🔔 Notification check: should_notify=True, has_predictions=True
Using config emotion filters: {}
📊 Trigger check result: triggered=True, count=3
✓ Sent Omi notification to user
```

**Check 4: Verify URL**
```
✅ https://your-app.onrender.com/audio
❌ https://your-app.onrender.com/audio?send_notification=true?sample_rate=16000
```
(No extra parameters needed!)

### "No speech detected" Warnings

- Speak clearly during recording
- Check microphone permissions
- Test in quiet environment
- Ensure device is working properly

### "Audio too long" Errors

Already fixed! The service automatically chunks audio >5 seconds into 4.5s segments.

### Dashboard Not Showing Emotions

- Hard refresh browser: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)
- Wait for auto-refresh (10 seconds)
- Check `/status` endpoint for current stats

## 📚 Documentation

Detailed guides available in the `docs/` folder:

- `AUTOMATIC_NOTIFICATIONS_SETUP.md` - Quick notification setup
- `NOTIFICATIONS_GUIDE.md` - Complete notification guide
- `DEVICE_CONFIGURATION.md` - Device configuration details
- `HUME_API_LIMITS.md` - API limits and best practices
- `TEXT_EMOTION_EXAMPLES.md` - Text analysis examples
- `TROUBLESHOOTING.md` - Common issues and solutions

## 🚀 Deployment

### Render (Recommended)

1. Fork this repo
2. Connect to Render
3. Add environment variables
4. Deploy!

See `RENDER_DEPLOYMENT.md` for detailed steps.

### Docker

```bash
docker build -t omi-emotion-ai .
docker run -p 8080:8080 \
  -e HUME_API_KEY=... \
  -e OMI_APP_ID=... \
  -e OMI_API_KEY=... \
  omi-emotion-ai
```

## 🎯 Use Cases

- 💙 **Mental Health Monitoring** - Track emotional patterns
- 📞 **Customer Service** - Alert when customers are frustrated
- 🎙️ **Voice Journaling** - Analyze emotional trends
- 🗣️ **Communication Coaching** - Improve emotional delivery
- 🔬 **Research** - Study emotional responses

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- [Hume AI](https://www.hume.ai/) - Powerful Hume EVI API for emotion analysis
- [Omi AI Voice](https://www.omi.me/) - Wearable AI device used for demo and real-time audio streaming
- [Render](https://render.com/) - Easy cloud deployment
- FastAPI - Modern web framework for Python

---

**Made with ❤️ for better emotional awareness**

For questions or issues, please open an issue on GitHub!
