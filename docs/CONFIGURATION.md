# Configuration Guide

This document explains all configuration options for the Omi + Hume AI streaming service.

## Environment Variables

### Required Variables

#### `HUME_API_KEY`
- **Required**: Yes (for emotion analysis)
- **Description**: Your Hume AI API key for emotion analysis
- **How to get**: Sign up at [hume.ai](https://www.hume.ai/) and create an API key
- **Example**: `HUME_API_KEY=hu_abc123def456...`

### Optional Variables

#### `GCS_BUCKET_NAME`
- **Required**: No (only if using Google Cloud Storage)
- **Description**: Name of your Google Cloud Storage bucket
- **Example**: `GCS_BUCKET_NAME=my-omi-audio-bucket`
- **Note**: If not set, GCS upload will be skipped (even if `save_to_gcs=true`)

#### `GOOGLE_APPLICATION_CREDENTIALS_JSON`
- **Required**: No (only if using Google Cloud Storage)
- **Description**: Base64-encoded Google Cloud service account credentials
- **How to get**:
  1. Create service account in GCP
  2. Download JSON key file
  3. Encode to base64: `base64 -i credentials.json`
- **Example**: `GOOGLE_APPLICATION_CREDENTIALS_JSON=ewogICJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIsC...`

## API Query Parameters

### Required Parameters

#### `sample_rate`
- **Required**: Yes
- **Type**: Integer
- **Description**: Audio sample rate in Hz
- **Valid values**:
  - `8000` - DevKit1 v1.0.2
  - `16000` - DevKit1 v1.0.4+ and DevKit2
- **Example**: `?sample_rate=16000`

#### `uid`
- **Required**: Yes
- **Type**: String
- **Description**: Unique user identifier
- **Example**: `?uid=user123`

### Optional Parameters

#### `analyze_emotion`
- **Required**: No
- **Type**: Boolean
- **Default**: `true`
- **Description**: Whether to analyze audio with Hume AI
- **Use cases**:
  - `true` - Analyze emotions (requires `HUME_API_KEY`)
  - `false` - Skip emotion analysis (just storage)
- **Example**: `?analyze_emotion=true`

#### `save_to_gcs`
- **Required**: No
- **Type**: Boolean
- **Default**: `true`
- **Description**: Whether to save audio to Google Cloud Storage
- **Use cases**:
  - `true` - Save to GCS (requires GCS credentials)
  - `false` - Skip storage (just analyze)
- **Example**: `?save_to_gcs=false`

## Common Configuration Scenarios

### 1. Emotion Analysis Only (No Storage)

**Best for**: Real-time emotion detection without archiving

**Environment Variables:**
```bash
HUME_API_KEY=your_hume_api_key
# GCS variables not needed
```

**Omi Endpoint:**
```
https://your-url/audio?sample_rate=16000&uid=user123&save_to_gcs=false
```

**What happens:**
- ✅ Audio analyzed with Hume AI
- ❌ Audio NOT saved to cloud
- 📊 Returns emotion predictions only

---

### 2. Storage Only (No Analysis)

**Best for**: Audio archiving without emotion processing

**Environment Variables:**
```bash
GOOGLE_APPLICATION_CREDENTIALS_JSON=your_base64_credentials
GCS_BUCKET_NAME=your-bucket-name
# HUME_API_KEY not needed
```

**Omi Endpoint:**
```
https://your-url/audio?sample_rate=16000&uid=user123&analyze_emotion=false
```

**What happens:**
- ❌ Audio NOT analyzed
- ✅ Audio saved to GCS
- 📦 Returns storage location only

---

### 3. Full Pipeline (Analysis + Storage)

**Best for**: Complete emotion tracking with archival

**Environment Variables:**
```bash
HUME_API_KEY=your_hume_api_key
GOOGLE_APPLICATION_CREDENTIALS_JSON=your_base64_credentials
GCS_BUCKET_NAME=your-bucket-name
```

**Omi Endpoint:**
```
https://your-url/audio?sample_rate=16000&uid=user123
```

**What happens:**
- ✅ Audio analyzed with Hume AI
- ✅ Audio saved to GCS
- 📊 Returns both emotions and storage location

---

### 4. Testing/Development

**Best for**: Local development without cloud dependencies

**Environment Variables:**
```bash
HUME_API_KEY=your_hume_api_key
# No GCS needed
```

**Omi Endpoint (via ngrok):**
```
https://abc123.ngrok.io/audio?sample_rate=16000&uid=dev-user&save_to_gcs=false
```

**What happens:**
- ✅ Tests emotion analysis
- ❌ No cloud costs
- 🚀 Quick iteration

## Deployment Configurations

### Minimal Docker (Hume Only)

```bash
docker run -p 8080:8080 \
  -e HUME_API_KEY="your_hume_api_key" \
  omi-audio-streaming
```

### Full Docker (Hume + GCS)

```bash
docker run -p 8080:8080 \
  -e HUME_API_KEY="your_hume_api_key" \
  -e GOOGLE_APPLICATION_CREDENTIALS_JSON="your_base64_creds" \
  -e GCS_BUCKET_NAME="your-bucket" \
  omi-audio-streaming
```

### Google Cloud Run (Minimal)

```bash
gcloud run deploy omi-audio-streaming \
  --image gcr.io/PROJECT_ID/omi-audio-streaming \
  --set-env-vars HUME_API_KEY=your_key
```

### Google Cloud Run (Full)

```bash
gcloud run deploy omi-audio-streaming \
  --image gcr.io/PROJECT_ID/omi-audio-streaming \
  --set-env-vars HUME_API_KEY=your_key \
  --set-env-vars GCS_BUCKET_NAME=bucket-name \
  --set-env-vars GOOGLE_APPLICATION_CREDENTIALS_JSON=base64_creds
```

## Response Examples

### With Both Analysis and Storage

```json
{
  "message": "Audio processed successfully",
  "filename": "user123_20250102_143022_123456.wav",
  "uid": "user123",
  "sample_rate": 16000,
  "data_size_bytes": 160000,
  "timestamp": "20250102_143022_123456",
  "gcs_path": "gs://bucket/user123_20250102_143022_123456.wav",
  "hume_analysis": {
    "success": true,
    "total_predictions": 2,
    "predictions": [...]
  }
}
```

### Analysis Only (No GCS)

```json
{
  "message": "Audio processed successfully",
  "filename": "user123_20250102_143022_123456.wav",
  "uid": "user123",
  "sample_rate": 16000,
  "data_size_bytes": 160000,
  "timestamp": "20250102_143022_123456",
  "hume_analysis": {
    "success": true,
    "total_predictions": 2,
    "predictions": [...]
  }
}
```

Note: No `gcs_path` field when storage is disabled.

### Storage Only (No Analysis)

```json
{
  "message": "Audio processed successfully",
  "filename": "user123_20250102_143022_123456.wav",
  "gcs_path": "gs://bucket/user123_20250102_143022_123456.wav",
  "uid": "user123",
  "sample_rate": 16000,
  "data_size_bytes": 160000,
  "timestamp": "20250102_143022_123456"
}
```

Note: No `hume_analysis` field when analysis is disabled.

## Troubleshooting

### "HUME_API_KEY environment variable not set"

**Cause**: Trying to analyze emotions without API key

**Solutions**:
- Set `HUME_API_KEY` environment variable
- Or disable analysis: `?analyze_emotion=false`

### "GCS_BUCKET_NAME not set, skipping GCS upload"

**Cause**: Trying to save to GCS without configuration (warning only)

**Solutions**:
- Set GCS environment variables (see above)
- Or disable storage: `?save_to_gcs=false`
- Or ignore (audio will still be analyzed)

### "Failed to upload to GCS"

**Cause**: GCS credentials invalid or permissions missing

**Solutions**:
- Verify base64 encoding of credentials
- Check service account has Storage Object Creator role
- Check bucket name is correct
- Or disable storage: `?save_to_gcs=false`

## Best Practices

1. **Start Simple**: Begin with Hume-only setup, add GCS later if needed
2. **Security**: Never commit `.env` files or credentials to git
3. **Cost Optimization**: Disable storage if you only need real-time analysis
4. **Testing**: Use `save_to_gcs=false` during development to avoid storage costs
5. **Monitoring**: Check server logs to verify which features are active
