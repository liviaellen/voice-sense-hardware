# Automatic Emotion Notifications - Quick Setup

## ✅ Perfect! Notifications Are Now AUTOMATIC!

You no longer need to add `?send_notification=true` to every URL. The system automatically sends notifications when emotions hit your thresholds!

---

## 🎯 Simple Setup

### Step 1: Configure Omi Device

**In Omi App → Settings → Developer Mode → "Realtime audio bytes":**

```
https://audio-sentiment-profiling.onrender.com/audio
```

**That's it!** No parameters needed. Notifications happen automatically when thresholds are met.

---

### Step 2: Configure Emotion Thresholds (Optional)

The server comes with smart defaults:

```json
{
  "Anger": 0.7,      // Notify when Anger >= 70%
  "Sadness": 0.6,    // Notify when Sadness >= 60%
  "Distress": 0.65,  // Notify when Distress >= 65%
  "Anxiety": 0.7,    // Notify when Anxiety >= 70%
  "Fear": 0.75       // Notify when Fear >= 75%
}
```

**Want to change them?** Three ways:

---

## 🔧 Configure Emotion Thresholds

### Method 1: Edit emotion_config.json (Recommended)

Edit the file `emotion_config.json`:

```json
{
  "notification_enabled": true,
  "emotion_thresholds": {
    "Anger": 0.8,
    "Sadness": 0.7,
    "Fear": 0.75
  }
}
```

Commit to git and redeploy.

---

### Method 2: Use API (Dynamic Changes)

**View current config:**
```bash
curl https://audio-sentiment-profiling.onrender.com/emotion-config
```

**Update config:**
```bash
curl -X POST https://audio-sentiment-profiling.onrender.com/emotion-config \
  -H "Content-Type: application/json" \
  -d '{
    "notification_enabled": true,
    "emotion_thresholds": {
      "Anger": 0.8,
      "Sadness": 0.7
    }
  }'
```

Changes apply immediately!

---

### Method 3: Environment Variable (For Render)

**In Render Dashboard → Environment:**

Add:
```
EMOTION_NOTIFICATION_CONFIG={"notification_enabled":true,"emotion_thresholds":{"Anger":0.7,"Sadness":0.6}}
```

This overrides the file config.

---

## 📱 How It Works

```
User speaks → Omi records → Sends to your server
                               ↓
                    Analyze with Hume AI
                               ↓
                    Check: Anger >= 0.7?
                               ↓
                          ✅ YES!
                               ↓
              Send notification automatically!
                               ↓
              📱 User receives: "🎭 Emotion Alert: Detected Anger"
```

---

## 🎯 Configuration Examples

### Example 1: Safety Monitoring (High Threshold)
```json
{
  "notification_enabled": true,
  "emotion_thresholds": {
    "Anger": 0.8,
    "Fear": 0.85,
    "Distress": 0.8
  }
}
```
→ Only notifies for very strong negative emotions

---

### Example 2: Mental Health Support (Lower Threshold)
```json
{
  "notification_enabled": true,
  "emotion_thresholds": {
    "Sadness": 0.5,
    "Anxiety": 0.55,
    "Distress": 0.5
  }
}
```
→ Catches earlier signs of emotional distress

---

### Example 3: Customer Service
```json
{
  "notification_enabled": true,
  "emotion_thresholds": {
    "Anger": 0.65,
    "Frustration": 0.6,
    "Contempt": 0.7
  }
}
```
→ Alert supervisors when customers are upset

---

### Example 4: Positive Reinforcement
```json
{
  "notification_enabled": true,
  "emotion_thresholds": {
    "Joy": 0.8,
    "Pride": 0.75,
    "Triumph": 0.8
  }
}
```
→ Celebrate positive moments!

---

## 🔄 Override for Specific Users (Optional)

Want different settings for a specific request? Add parameters:

**Disable for one request:**
```
https://audio-sentiment-profiling.onrender.com/audio?send_notification=false
```

**Custom thresholds for one request:**
```
https://audio-sentiment-profiling.onrender.com/audio?emotion_filters={"Anger":0.9}
```

But **by default**, you don't need any parameters! 🎉

---

## 📊 Check Your Settings

**View in browser:**
```
https://audio-sentiment-profiling.onrender.com/emotion-config
```

**Response:**
```json
{
  "current_config": {
    "notification_enabled": true,
    "emotion_thresholds": {
      "Anger": 0.7,
      "Sadness": 0.6,
      "Distress": 0.65,
      "Anxiety": 0.7,
      "Fear": 0.75
    }
  }
}
```

---

## 🧪 Test It

### Step 1: Speak into Omi
Say something emotional (angry, sad, excited)

### Step 2: Check Dashboard
Visit: https://audio-sentiment-profiling.onrender.com/

Look for:
- Recent emotions detected
- Whether notification was sent

### Step 3: Check Omi App
You should receive notification if emotion exceeded threshold!

---

## 🎭 Available Emotions

**You can set thresholds for any of these:**

### Negative
- Anger, Anxiety, Contempt, Disgust, Distress
- Embarrassment, Fear, Guilt, Sadness, Shame

### Positive
- Admiration, Adoration, Amusement, Joy, Pride
- Relief, Romance, Satisfaction, Triumph

### Neutral/Complex
- Calmness, Concentration, Contemplation
- Determination, Interest, Surprise, Confusion

---

## ⚙️ Advanced: Per-User Settings

Want different thresholds for different users? Store in database:

```python
# In your code (advanced)
user_configs = {
    "user_abc": {"Anger": 0.6, "Sadness": 0.5},
    "user_xyz": {"Anger": 0.8, "Sadness": 0.7}
}

# Use user-specific config
filters = user_configs.get(uid, EMOTION_CONFIG['emotion_thresholds'])
```

---

## 🚀 Deploy to Render

### Option 1: Commit emotion_config.json
```bash
git add emotion_config.json
git commit -m "Configure emotion thresholds"
git push
```

Render auto-deploys with your settings!

---

### Option 2: Use Environment Variable
**In Render Dashboard:**
1. Go to Environment tab
2. Add variable:
   ```
   EMOTION_NOTIFICATION_CONFIG={"notification_enabled":true,"emotion_thresholds":{"Anger":0.7}}
   ```
3. Save Changes

---

## 📝 Summary

### What Changed:

**Before:**
```
https://audio-sentiment-profiling.onrender.com/audio?send_notification=true&emotion_filters={"Anger":0.7}
```
👎 Had to include parameters every time

**After:**
```
https://audio-sentiment-profiling.onrender.com/audio
```
👍 Clean URL! Everything configured in `emotion_config.json`

### Benefits:

✅ **Simpler Omi configuration** - Just one URL
✅ **Centralized settings** - Change thresholds in one place
✅ **Consistent behavior** - All users get same thresholds
✅ **Easy updates** - Change config without reconfiguring devices
✅ **Optional overrides** - Can still customize per-request if needed

---

## 🔍 Troubleshooting

### Notifications not sending?

**Check 1: Config loaded?**
```bash
curl https://audio-sentiment-profiling.onrender.com/emotion-config
```

**Check 2: Omi credentials set?**
```bash
# In Render environment:
OMI_APP_ID=...
OMI_API_KEY=...
```

**Check 3: Emotions meeting threshold?**
Check logs - look for:
```
Using config emotion filters: {'Anger': 0.7, 'Sadness': 0.6}
🔔 Emotion trigger detected!
✓ Sent Omi notification to user
```

**Check 4: Emotion scores too low?**
Lower your thresholds if emotions aren't triggering:
```json
{
  "emotion_thresholds": {
    "Anger": 0.5,  // Lower = more sensitive
    "Sadness": 0.4
  }
}
```

---

## 🎉 You're Done!

Your setup:
1. ✅ Omi device sends audio to: `https://audio-sentiment-profiling.onrender.com/audio`
2. ✅ Server automatically checks emotion thresholds from `emotion_config.json`
3. ✅ Sends notification when thresholds exceeded
4. ✅ User receives: "🎭 Emotion Alert: Detected Anger"

No URL parameters needed! 🚀
