# Text Emotion Analysis with Hume AI Language Model

## What is Text Emotion Analysis?

The Language model analyzes **emotional content in text** based on:
- Word choice (e.g., "happy" vs "sad")
- Phrasing and sentence structure
- Linguistic patterns
- Context and meaning

**Different from Prosody (Audio):**
- 🎤 **Prosody**: Analyzes HOW you say something (tone, pitch, intonation)
- 💬 **Language**: Analyzes WHAT you say (word choice, meaning)

## Example: Same Words, Different Emotions

### Audio (Prosody) Analysis
- "I'm fine" (said with angry tone) → Detects: Anger, Frustration
- "I'm fine" (said with happy tone) → Detects: Joy, Contentment

### Text (Language) Analysis
- "I'm fine" → Detects: Calmness, Neutrality (based on word choice)
- "I'm absolutely terrible!" → Detects: Distress, Sadness

## API Endpoint

### POST /analyze-text

**URL:** `https://your-ngrok-url.ngrok-free.app/analyze-text`

**Query Parameters:**
- `uid` (optional): User ID

**Request Body (JSON):**
```json
{
  "text": "Your text to analyze",
  "metadata": {
    "source": "transcription",
    "timestamp": "2024-11-02T13:33:22Z"
  }
}
```

**Limits:**
- Max text length: 10,000 characters
- Rate limit: 50 requests/second

## Usage Examples

### Example 1: Basic Text Analysis

**Request:**
```bash
curl -X POST "https://your-url/analyze-text?uid=user123" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I am feeling really happy and excited today! This is the best day ever!"
  }'
```

**Response:**
```json
{
  "message": "Text emotion analysis complete",
  "text_length": 72,
  "uid": "user123",
  "hume_analysis": {
    "success": true,
    "analyzed_text": "I am feeling really happy and excited today! This is the best day ever!",
    "predictions": [
      {
        "text": "I",
        "position": {"begin": 0, "end": 1},
        "top_3_emotions": [
          {"name": "Calmness", "score": 0.45},
          {"name": "Contentment", "score": 0.38},
          {"name": "Interest", "score": 0.32}
        ]
      },
      {
        "text": "am",
        "position": {"begin": 2, "end": 4},
        "top_3_emotions": [...]
      },
      {
        "text": "feeling",
        "position": {"begin": 5, "end": 12},
        "top_3_emotions": [...]
      },
      {
        "text": "really",
        "position": {"begin": 13, "end": 19},
        "top_3_emotions": [...]
      },
      {
        "text": "happy",
        "position": {"begin": 20, "end": 25},
        "top_3_emotions": [
          {"name": "Joy", "score": 0.89},
          {"name": "Amusement", "score": 0.72},
          {"name": "Excitement", "score": 0.68}
        ]
      },
      {
        "text": "excited",
        "position": {"begin": 30, "end": 37},
        "top_3_emotions": [
          {"name": "Excitement", "score": 0.91},
          {"name": "Interest", "score": 0.75},
          {"name": "Admiration", "score": 0.58}
        ]
      }
    ],
    "total_predictions": 14
  }
}
```

### Example 2: Analyze Transcription from Speech-to-Text

**Workflow:**
1. Get audio from Omi device → `/audio` endpoint
2. Transcribe audio with your STT service (Whisper, Google STT, etc.)
3. Send transcription to `/analyze-text` endpoint

**Python Example:**
```python
import requests

# Step 1: Already have transcription from your STT service
transcription = "I'm really worried about the meeting tomorrow. I don't think I'm prepared enough."

# Step 2: Send to text emotion analysis
response = requests.post(
    "https://your-url/analyze-text?uid=user123",
    json={
        "text": transcription,
        "metadata": {
            "source": "whisper_stt",
            "audio_file": "user123_20241102_133322.wav"
        }
    }
)

results = response.json()

# Step 3: Extract dominant emotions
for prediction in results["hume_analysis"]["predictions"]:
    word = prediction["text"]
    top_emotion = prediction["top_3_emotions"][0]
    print(f"{word}: {top_emotion['name']} ({top_emotion['score']:.2f})")
```

**Output:**
```
I'm: Calmness (0.45)
really: Emphasis (0.62)
worried: Anxiety (0.88)
about: Contemplation (0.51)
meeting: Determination (0.43)
tomorrow: Anticipation (0.55)
...
```

### Example 3: JavaScript/TypeScript Integration

```typescript
async function analyzeTextEmotion(text: string, userId: string) {
  const response = await fetch(
    `https://your-url/analyze-text?uid=${userId}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text: text,
        metadata: {
          timestamp: new Date().toISOString(),
          source: 'user_input'
        }
      })
    }
  );

  const data = await response.json();

  // Get overall emotional tone (aggregate top emotions)
  const emotionCounts = {};
  data.hume_analysis.predictions.forEach(pred => {
    const topEmotion = pred.top_3_emotions[0].name;
    emotionCounts[topEmotion] = (emotionCounts[topEmotion] || 0) + 1;
  });

  // Find most common emotion
  const dominantEmotion = Object.entries(emotionCounts)
    .sort((a, b) => b[1] - a[1])[0][0];

  return {
    dominantEmotion,
    wordByWordAnalysis: data.hume_analysis.predictions,
    rawResponse: data
  };
}

// Usage
const result = await analyzeTextEmotion(
  "I'm so grateful for your help! Thank you!",
  "user123"
);
console.log(`Dominant emotion: ${result.dominantEmotion}`);
```

## Emotion Categories

Hume's Language model detects 48+ emotions including:

**Positive:**
- Joy, Amusement, Admiration, Adoration
- Excitement, Aesthetic Appreciation, Romance
- Relief, Pride, Triumph, Satisfaction

**Negative:**
- Sadness, Anger, Fear, Disgust
- Anxiety, Distress, Disappointment
- Shame, Guilt, Contempt, Envy

**Neutral/Complex:**
- Interest, Surprise, Confusion, Contemplation
- Determination, Concentration, Calmness
- Sympathy, Empathy, Nostalgia

## Use Cases

### 1. **Customer Support Analysis**
```json
{
  "text": "I've been trying to cancel my subscription for three days and nobody is helping me. This is ridiculous!"
}
```
→ Detects: Frustration, Anger → Route to senior support

### 2. **Mental Health Monitoring**
```json
{
  "text": "I don't see the point anymore. Everything feels hopeless."
}
```
→ Detects: Despair, Sadness → Trigger wellness check-in

### 3. **Content Moderation**
```json
{
  "text": "You're all idiots and I hate this platform!"
}
```
→ Detects: Anger, Contempt → Flag for moderation

### 4. **Learning & Education**
```json
{
  "text": "I'm confused about how this concept works. Can someone explain?"
}
```
→ Detects: Confusion, Interest → Provide additional resources

## Combined Audio + Text Analysis

For the most complete emotional understanding, use BOTH:

```python
import requests

# Step 1: Analyze audio (prosody) - HOW they said it
audio_response = requests.post(
    "https://your-url/audio?sample_rate=16000&uid=user123",
    data=audio_bytes,
    headers={"Content-Type": "application/octet-stream"}
)
prosody_emotions = audio_response.json()["hume_analysis"]["predictions"]

# Step 2: Transcribe audio
transcription = transcribe_audio(audio_bytes)  # Your STT service

# Step 3: Analyze text (language) - WHAT they said
text_response = requests.post(
    "https://your-url/analyze-text?uid=user123",
    json={"text": transcription}
)
language_emotions = text_response.json()["hume_analysis"]["predictions"]

# Step 4: Compare results
print("Speech emotion (HOW):", prosody_emotions[0]["top_3_emotions"])
print("Text emotion (WHAT):", language_emotions[0]["top_3_emotions"])

# Example output:
# Speech emotion: [Sarcasm (0.82), Contempt (0.65), Amusement (0.54)]
# Text emotion: [Calmness (0.55), Interest (0.42), Contentment (0.38)]
# → Person said "I'm fine" sarcastically!
```

## Testing the Endpoint

### Test 1: Happy Text
```bash
curl -X POST "http://localhost:8080/analyze-text" \
  -H "Content-Type: application/json" \
  -d '{"text": "I love this amazing product!"}'
```

### Test 2: Sad Text
```bash
curl -X POST "http://localhost:8080/analyze-text" \
  -H "Content-Type: application/json" \
  -d '{"text": "I feel so lonely and miserable."}'
```

### Test 3: Mixed Emotions
```bash
curl -X POST "http://localhost:8080/analyze-text" \
  -H "Content-Type: application/json" \
  -d '{"text": "I am excited but also nervous about the interview."}'
```

## Error Handling

### Text Too Long
```json
{
  "detail": "Text too long (12,543 characters). Maximum is 10,000 characters."
}
```

**Solution:** Split text into chunks ≤10,000 characters

### Missing Text Field
```json
{
  "detail": "Missing 'text' field in request body"
}
```

**Solution:** Include `"text"` in JSON body

## Best Practices

1. ✅ **Pre-process text**: Remove excessive whitespace, normalize encoding
2. ✅ **Handle punctuation**: Hume analyzes punctuation for emotional cues
3. ✅ **Keep context**: Don't split sentences mid-word
4. ✅ **Aggregate results**: Average emotions across words for overall sentiment
5. ✅ **Combine with prosody**: Use both audio and text for complete picture

## Next Steps

1. Integrate your speech-to-text service (Whisper, Google STT, etc.)
2. Send transcriptions to `/analyze-text` endpoint
3. Combine prosody + language results for comprehensive emotion AI
4. Build your emotion-aware application!
