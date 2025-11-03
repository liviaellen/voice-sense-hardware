# Omi Emotion Notifications Guide

## Overview

Your server now supports sending **automatic notifications to Omi** when specific emotions are detected in audio! This allows you to get real-time alerts when certain emotional states are identified.

## Setup

### 1. Create an Omi App

1. Open the **Omi mobile app**
2. Go to **Apps** section
3. Select **"Create App"**
4. Fill in app information:
   - Name: "Emotion AI Notifier"
   - Description: "Sends notifications based on detected emotions"
5. Under **"App Capabilities"**, select **"External Integration"**
6. Select capabilities:
   - ✅ **Notifications** (to send alerts)
   - ✅ **Create Memories** (optional, to save emotion records)

### 2. Generate API Keys

1. Go to your app's management page
2. Scroll to **"API Keys"** section
3. Click **"Create Key"**
4. **Copy and save** the generated key securely

### 3. Configure Your Server

Add to your `.env` file:

```bash
# Omi Integration Configuration
OMI_APP_ID=your_app_id_here
OMI_API_KEY=sk_your_api_key_here
```

### 4. Enable Your App for Users

Each user must:
1. Open Omi app
2. Go to **Apps** → Find your app
3. Click **"Enable"** or **"Connect"**

---

## How It Works

```
┌─────────────┐
│ Omi Device  │ Records audio
└──────┬──────┘
       │
       ↓
┌─────────────────┐
│  Your Server    │ Analyzes with Hume AI
└──────┬──────────┘
       │
       ↓
  ┌────────────┐
  │ Emotions?  │
  └────┬───────┘
       │
  ┌────┴────┐
  │ Filter? │ Check threshold
  └────┬────┘
       │
       ↓ (if matched)
┌─────────────────┐
│ Send Omi        │
│ Notification 📱 │
└─────────────────┘
```

---

## Usage Examples

### Example 1: Notify for ANY Emotion

Send notification for all detected emotions:

```bash
curl -X POST "https://your-url/audio?sample_rate=16000&uid=user123&send_notification=true" \
  -H "Content-Type: application/octet-stream" \
  --data-binary "@audio.wav"
```

**Result:** User receives notification like:
> 🎭 Emotion Alert: Detected Joy, Interest, Calmness

---

### Example 2: Notify Only for High Anger

Only send notification if Anger score >= 0.7:

```bash
curl -X POST "https://your-url/audio?sample_rate=16000&uid=user123&send_notification=true&emotion_filters=%7B%22Anger%22:0.7%7D" \
  -H "Content-Type: application/octet-stream" \
  --data-binary "@audio.wav"
```

**Note:** `%7B%22Anger%22:0.7%7D` is URL-encoded `{"Anger":0.7}`

**Result:** Only notifies if Anger >= 0.7

---

### Example 3: Multiple Emotion Filters

Notify if ANY of these conditions match:
- Anger >= 0.7 **OR**
- Sadness >= 0.6 **OR**
- Distress >= 0.65

```bash
# URL-encoded: {"Anger":0.7,"Sadness":0.6,"Distress":0.65}
curl -X POST "https://your-url/audio?sample_rate=16000&uid=user123&send_notification=true&emotion_filters=%7B%22Anger%22:0.7,%22Sadness%22:0.6,%22Distress%22:0.65%7D" \
  -H "Content-Type: application/octet-stream" \
  --data-binary "@audio.wav"
```

---

### Example 4: Configure in Omi App Settings

Set your Omi device to automatically include notification parameters:

**In Omi App → Settings → Developer Mode:**

**For anger alerts:**
```
https://your-url/audio?send_notification=true&emotion_filters={"Anger":0.7}
```

**For mental health monitoring:**
```
https://your-url/audio?send_notification=true&emotion_filters={"Sadness":0.6,"Distress":0.65,"Anxiety":0.7}
```

---

## API Parameters

### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `sample_rate` | int | Audio sample rate (8000 or 16000) |
| `uid` | string | Omi user ID |

### Optional Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `analyze_emotion` | bool | `true` | Whether to analyze emotions |
| `send_notification` | bool | `false` | Whether to send Omi notification |
| `emotion_filters` | JSON string | `null` | Emotion:threshold filters |
| `save_to_gcs` | bool | `true` | Whether to save to Google Cloud |

---

## Emotion Filters Format

### JSON Structure

```json
{
  "EmotionName1": threshold_value1,
  "EmotionName2": threshold_value2,
  ...
}
```

- **EmotionName**: Exact emotion name from Hume AI (case-sensitive)
- **threshold_value**: Float between 0.0 and 1.0

### Available Emotions

**Negative Emotions:**
- Anger, Anxiety, Contempt, Disgust, Distress
- Embarrassment, Fear, Guilt, Sadness, Shame

**Positive Emotions:**
- Admiration, Adoration, Amusement, Joy, Pride
- Relief, Romance, Satisfaction, Triumph

**Neutral/Complex:**
- Calmness, Concentration, Contemplation, Determination
- Interest, Surprise, Confusion

**See full list:** [Hume AI Emotion Categories](https://hume.docs)

---

## Response Format

### With Notification Sent

```json
{
  "message": "Audio processed successfully",
  "filename": "user123_20251102_143322.wav",
  "uid": "user123",
  "hume_analysis": {
    "success": true,
    "predictions": [
      {
        "time": {"begin": 0.0, "end": 4.5},
        "top_3_emotions": [
          {"name": "Anger", "score": 0.85},
          {"name": "Frustration", "score": 0.72},
          {"name": "Contempt", "score": 0.58}
        ]
      }
    ],
    "notification_sent": true,
    "triggered_emotions": [
      {
        "name": "Anger",
        "score": 0.85,
        "threshold": 0.7,
        "time": {"begin": 0.0, "end": 4.5}
      }
    ]
  }
}
```

### No Emotions Matched Threshold

```json
{
  "hume_analysis": {
    "success": true,
    "predictions": [...],
    "notification_sent": false,
    "trigger_check": "No emotions matched threshold"
  }
}
```

---

## Use Cases

### 1. Mental Health Monitoring

**Setup:**
```json
{"Sadness": 0.65, "Distress": 0.7, "Anxiety": 0.7}
```

**Use Case:** Alert caregivers or therapists when patient shows signs of distress

---

### 2. Customer Service Quality

**Setup:**
```json
{"Anger": 0.7, "Contempt": 0.65, "Frustration": 0.7}
```

**Use Case:** Alert supervisors when customer is frustrated

---

### 3. Safety Monitoring

**Setup:**
```json
{"Fear": 0.75, "Distress": 0.8}
```

**Use Case:** Emergency alerts in dangerous situations

---

### 4. Positive Reinforcement

**Setup:**
```json
{"Joy": 0.8, "Pride": 0.75, "Triumph": 0.7}
```

**Use Case:** Celebrate achievements and positive moments

---

## Testing

### Test Script

```python
import requests
import json

# Configuration
API_URL = "https://your-ngrok-url.ngrok-free.app/audio"
USER_ID = "test_user_123"

# Test 1: Notify for all emotions
response = requests.post(
    f"{API_URL}?sample_rate=16000&uid={USER_ID}&send_notification=true",
    data=open("test_audio.wav", "rb"),
    headers={"Content-Type": "application/octet-stream"}
)
print("Test 1:", response.json())

# Test 2: Notify only for anger
filters = json.dumps({"Anger": 0.7})
response = requests.post(
    f"{API_URL}?sample_rate=16000&uid={USER_ID}&send_notification=true&emotion_filters={filters}",
    data=open("angry_audio.wav", "rb"),
    headers={"Content-Type": "application/octet-stream"}
)
print("Test 2:", response.json())
```

---

## Troubleshooting

### Notification Not Received

**Check 1: Omi App Configuration**
```bash
# Verify env vars are set
echo $OMI_APP_ID
echo $OMI_API_KEY
```

**Check 2: User Has Enabled App**
- User must enable your app in Omi mobile app

**Check 3: Check Server Logs**
```bash
tail -f server.log
```

Look for:
- `✓ Sent Omi notification to user {uid}`
- `❌ Omi API error: ...`

**Check 4: Verify Emotion Threshold**
- Emotion score must be >= threshold
- Check actual scores in response

---

### Common Issues

| Issue | Solution |
|-------|----------|
| `OMI_APP_ID not configured` | Add to `.env` file |
| `401 Unauthorized` | Check `OMI_API_KEY` is correct |
| `403 Forbidden` | User hasn't enabled your app |
| No emotions detected | Audio may be silent (see TROUBLESHOOTING.md) |
| Notification not triggering | Lower threshold or check emotion names |

---

## Advanced: Custom Notification Messages

Want to customize notification text? Modify the code in `main.py`:

```python
# Current (line ~704):
notification_msg = f"🎭 Emotion Alert: Detected {emotion_str}"

# Custom examples:
# For safety:
notification_msg = f"⚠️ Safety Alert: {emotion_str} detected. Are you okay?"

# For customer service:
notification_msg = f"📞 Customer Alert: High {emotion_str}. Agent assistance recommended."

# For mental health:
notification_msg = f"💙 Wellness Check: We noticed {emotion_str}. How can we support you?"
```

---

## Rate Limits

**Omi API Limits:**
- Check with Omi documentation for current limits
- Implement exponential backoff if needed

**Recommendations:**
- Don't send notifications for every audio chunk
- Use meaningful thresholds (>= 0.6)
- Group notifications (e.g., max 1 per minute)

---

## Security Best Practices

1. **Secure API Keys**
   - Never commit `.env` to git
   - Use environment variables
   - Rotate keys regularly

2. **User Privacy**
   - Get user consent for notifications
   - Allow users to opt-out
   - Don't log sensitive audio content

3. **Validate Inputs**
   - Server validates all parameters
   - Sanitizes user IDs
   - Checks thresholds are valid

---

## Next Steps

1. ✅ Configure your Omi app and get API keys
2. ✅ Update `.env` with credentials
3. ✅ Test with sample audio
4. ✅ Configure emotion filters for your use case
5. ✅ Deploy and monitor

---

## Support

- **Server Logs:** `tail -f server.log`
- **Omi Documentation:** https://docs.omi.me/
- **Hume AI Emotions:** https://dev.hume.ai/docs

Happy emotion monitoring! 🎭
