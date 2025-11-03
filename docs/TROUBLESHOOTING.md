# Troubleshooting Guide

## Issue: "No speech detected" from Hume AI

### Symptoms
```json
{
  "success": false,
  "error": "No speech detected in audio (Hume: No speech detected.)",
  "warning": "No speech detected."
}
```

### Root Cause
The audio file is **silent, very quiet, or contains no actual speech**.

### Diagnostic Steps

#### 1. Check if audio file has sound
```bash
# Play the audio file (macOS)
afplay audio_files/your_file.wav

# Check audio properties
ffmpeg -i audio_files/your_file.wav 2>&1 | grep -E "Duration|Stream"

# Analyze audio levels
ffmpeg -i audio_files/your_file.wav -af "volumedetect" -f null /dev/null 2>&1 | grep "mean_volume"
```

#### 2. Test with known good audio
Try with a file that has clear speech to verify the API works:
```bash
# Record test audio (macOS)
sox -d -r 16000 -c 1 -b 16 test_speech.wav trim 0 5

# Or download sample
curl -o test_sample.wav "https://www2.cs.uic.edu/~i101/SoundFiles/taunt.wav"
```

#### 3. Check Omi Device Settings

**Common Issues with Omi:**
- ✅ Microphone permissions not granted
- ✅ Device microphone is muted
- ✅ Recording level is too low
- ✅ Device is too far from speaker
- ✅ Background noise is masking speech

**Solutions:**
1. Open Omi app → Settings → Permissions → Microphone → Allow
2. Check device volume/recording levels
3. Speak closer to the device (within 1-2 feet)
4. Test in a quiet environment
5. Check device hardware (clean microphone hole)

### Solution 1: Increase Audio Recording Level

If audio is too quiet:

```python
from pydub import AudioSegment
from pydub.effects import normalize

# Load audio
audio = AudioSegment.from_wav("quiet_audio.wav")

# Normalize audio (increase volume)
normalized = normalize(audio)

# Save
normalized.export("louder_audio.wav", format="wav")
```

### Solution 2: Check Omi Device Configuration

**In Omi App:**
1. Settings → Developer Mode
2. Check "Audio Quality" settings
3. Try different sample rates (8000 vs 16000)
4. Enable "Audio Enhancement" if available

### Solution 3: Use Different Recording Method

If Omi device audio consistently has issues:

**Option A: Test with phone recording**
- Record voice memo on phone
- Transfer to server
- Test with `/audio` endpoint

**Option B: Use different hardware**
- External microphone
- Different recording device
- Phone as microphone

### Automated Audio Chunking Status

✅ **Audio chunking is now implemented!**

The server now automatically:
- Detects audio duration
- Splits files >5 seconds into 4.5-second chunks
- Analyzes each chunk separately
- Combines results with adjusted timestamps
- Cleans up temporary chunk files

**However, chunking won't help if audio is silent!**

### Testing Your Setup

#### Test 1: Verify API Key Works
```bash
curl -X POST "http://localhost:8080/analyze-text" \
  -H "Content-Type: application/json" \
  -d '{"text": "I am happy"}'
```

Expected: Success with emotion predictions

#### Test 2: Test with Sample Audio
```bash
# Create test audio with speech
say "Hello, this is a test" -o test_speech.aiff
ffmpeg -i test_speech.aiff -ar 16000 -ac 1 -sample_fmt s16 test_speech.wav

# Send to server
curl -X POST "http://localhost:8080/audio?sample_rate=16000&uid=test" \
  --data-binary "@test_speech.wav" \
  -H "Content-Type: application/octet-stream"
```

Expected: Success with prosody predictions

#### Test 3: Test with Your Omi Audio
```bash
# Send actual Omi recording
curl -X POST "http://localhost:8080/audio?sample_rate=16000&uid=test" \
  --data-binary "@audio_files/your_omi_file.wav" \
  -H "Content-Type: application/octet-stream"
```

Expected:
- If silent → "No speech detected"
- If has speech → Prosody predictions

### Next Steps

#### If Audio is Silent:
1. **Check Omi device hardware**
   - Test microphone with another app
   - Clean microphone port
   - Check for hardware damage

2. **Check Omi app permissions**
   - iOS: Settings → Omi → Microphone → On
   - Android: Settings → Apps → Omi → Permissions → Microphone → Allow

3. **Test recording manually**
   - Use Omi's built-in voice memo feature
   - Check if you can hear the recording

4. **Contact Omi support**
   - If hardware issue persists
   - Check for firmware updates

#### If Audio Has Speech but Still Fails:
1. **Check audio quality**
   ```bash
   ffmpeg -i audio_files/file.wav -af "volumedetect" -f null /dev/null 2>&1
   ```
   - Look for `mean_volume` (should be > -50dB)
   - Look for `max_volume` (should be close to 0dB)

2. **Try audio normalization** (see Solution 1 above)

3. **Check for codec issues**
   - Hume expects: 16kHz, 16-bit, mono PCM
   - Your Omi uses: 16kHz ✅
   - Check if format matches

### Current File Status

**Your audio file:**
- ✅ File exists: `XqBKRatqZ5MS4tsX84VfBEne16W2_20251102_134454_244061.wav`
- ✅ Format: RIFF WAV, PCM 16-bit, mono, 16kHz ✅
- ✅ Duration: 10.07 seconds
- ✅ Size: 315KB
- ❌ **Contains no detectable speech** (Hume API result)

**This means:**
- The Omi device is recording
- The audio file format is correct
- **BUT the audio is silent or doesn't contain speech**

### Recommended Actions

1. **Immediate:** Check your Omi device
   - Is microphone working?
   - Are you speaking into it during recording?
   - Is recording level adequate?

2. **Test:** Create a manual recording
   - Use phone/computer to record yourself speaking
   - Convert to 16kHz WAV
   - Test with server to verify API works

3. **Debug:** Check Omi device
   - Test with Omi's own playback feature
   - Verify you can hear your voice in recordings
   - Check device isn't in airplane mode

## Additional Resources

- [Hume AI WebSocket Docs](https://dev.hume.ai/docs/expression-measurement/websocket)
- [Omi Device Documentation](https://docs.omi.me/)
- [FFmpeg Audio Processing](https://ffmpeg.org/ffmpeg-filters.html#Audio-Filters)
- [PyDub Documentation](https://github.com/jiaaro/pydub)

## Support

If issues persist:
1. Check server logs: `tail -f server.log`
2. Check Omi device logs in Omi app
3. Test with different audio source
4. Contact Omi support for hardware issues
