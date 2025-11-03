# Hume AI WebSocket API - Limits & Important Notes

## API Limits (from official docs)

### 1. WebSocket Duration Limit
- **1 minute of inactivity** → connection automatically closes
- You must implement reconnection logic
- Keep socket open for multiple files (don't open/close for each file)

### 2. WebSocket Message Payload Size Limits

⚠️ **CRITICAL**: These are maximum sizes per message:

- **Audio**: 5,000 milliseconds (5 seconds) MAX
- **Video**: 5,000 milliseconds (5 seconds) MAX
- **Image**: 3,000 × 3,000 pixels MAX
- **Text**: 10,000 characters MAX

### 3. Request Rate Limit
- **50 requests per second** for HTTP requests (WebSocket handshakes)

## Your Current Setup

### Omi Device Audio
Your Omi device sends audio every X seconds (configurable in app).

**Problem**: If you set "Every x seconds" to 10 seconds, the audio will be **10 seconds long**, which **exceeds the 5-second WebSocket API limit**!

### Solutions

#### Option 1: Reduce Omi Interval (Easiest)
Set "Every x seconds" to **5** or less in the Omi app:
- ✅ No code changes needed
- ✅ Works with current WebSocket implementation
- ❌ More frequent network requests

#### Option 2: Use Hume Batch API (Better for long audio)
Switch from WebSocket streaming to Batch API for files > 5 seconds:
- ✅ Handles audio up to 3 hours
- ✅ Processes files asynchronously
- ✅ Better for recorded audio
- ❌ Requires code refactoring
- ❌ Not real-time (job-based processing)

#### Option 3: Chunk Audio Client-Side
Split long audio into 5-second chunks before sending:
- ✅ Works with WebSocket API
- ✅ Can process long recordings
- ❌ Complex implementation
- ❌ Requires audio processing library

## Current Implementation Status

### ✅ What Works Now
- Receives audio from Omi device
- Saves audio files locally in `audio_files/` directory
- Detects audio duration and warns if > 5 seconds
- Uses Hume Prosody model for speech emotion analysis
- Returns top 3 emotions with confidence scores

### ⚠️ Current Limitation
**Your audio is likely > 5 seconds**, which causes:
```json
{
  "success": false,
  "error": "No prosody predictions returned (audio is ~10.2s, limit is 5s)"
}
```

### 🎯 Recommended Action
**Configure your Omi device to send audio every 5 seconds or less:**

1. Open Omi App
2. Settings → Developer Mode
3. Set "Every x seconds" to: **5** (or 3-4 for safety margin)
4. Save settings

This will immediately fix the "No prosody predictions" issue!

## Models Available

### Speech Prosody Model (What We Use)
- ✅ Analyzes speech emotion from audio tone/pitch
- ✅ Works with audio or video files
- ❌ **Does NOT provide transcription**
- ❌ **Does NOT do text emotion analysis**

### Language Model (Text Emotion)
- ✅ Analyzes emotion from text content
- ✅ Returns word-by-word emotion scores
- ❌ Requires actual text input (not audio)
- ❌ Cannot be used with prosody for transcription

### Important Note
**Hume's WebSocket API does NOT automatically transcribe audio**. The language model analyzes text you provide, not transcribed speech. For speech-to-text + emotion analysis, you would need:
1. Separate speech-to-text service (e.g., Whisper, Google Speech-to-Text)
2. Then send transcribed text to Hume's language model

## Response Format

### Success Response (Prosody)
```json
{
  "success": true,
  "predictions": [
    {
      "time": {"begin": 0.0, "end": 4.8},
      "emotions": [
        {"name": "Joy", "score": 0.82},
        {"name": "Interest", "score": 0.65},
        {"name": "Calmness", "score": 0.54},
        ...48 total emotions...
      ],
      "top_3_emotions": [
        {"name": "Joy", "score": 0.82},
        {"name": "Interest", "score": 0.65},
        {"name": "Calmness", "score": 0.54}
      ]
    }
  ],
  "total_predictions": 1
}
```

### Error Response
```json
{
  "success": false,
  "error": "No prosody predictions returned (audio is ~10.2s, limit is 5s)",
  "predictions": [],
  "debug_info": {
    "estimated_duration_seconds": 10.24,
    "likely_cause": "Audio file exceeds 5-second WebSocket API limit"
  }
}
```

## Best Practices

### ✅ DO
- Keep WebSocket connections open for multiple files
- Use `reset_stream` parameter to avoid context leakage between unrelated files
- Implement reconnection logic for 1-minute timeout
- Check audio duration before sending
- Handle errors gracefully

### ❌ DON'T
- Send audio files longer than 5 seconds
- Open new connection for each audio file
- Assume language model will transcribe audio
- Exceed 50 requests/second rate limit

## Monitoring

Check server logs for warnings:
```bash
tail -f server.log
```

Look for:
```
⚠️  WARNING: Audio is ~10.2s, but WebSocket API limit is 5s
```

## References

- [Hume WebSocket API Docs](https://dev.hume.ai/docs/expression-measurement/websocket)
- [Hume Python SDK](https://github.com/HumeAI/hume-python-sdk)
- [API Rate Limits](https://dev.hume.ai/docs/expression-measurement/websocket#api-limits)
