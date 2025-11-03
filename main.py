import os
import base64
import json
import tempfile
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from google.cloud import storage
from google.oauth2 import service_account
from hume import AsyncHumeClient
from hume.expression_measurement.stream.stream.types import Config
import uvicorn

app = FastAPI(title="Real-time Voice Emotion Analysis - Powered by Hume EVI API")


# Startup event to launch background tasks
@app.on_event("startup")
async def startup_event():
    """Initialize background tasks on server startup"""
    import asyncio

    print("🚀 Starting emotion memory background task (runs every 1 hour)...")
    asyncio.create_task(emotion_memory_background_task())

    print("🗑️  Starting audio file cleanup task (runs every 1 minute)...")
    asyncio.create_task(cleanup_old_audio_files())


# Store recent audio processing stats
audio_stats = {
    "total_requests": 0,
    "successful_analyses": 0,
    "failed_analyses": 0,
    "last_request_time": None,
    "last_uid": None,
    "recent_emotions": [],
    "emotion_counts": {},  # Track count of each emotion detected
    "recent_notifications": []  # Track last 10 notifications sent
}

# Emotion categories for classification
POSITIVE_EMOTIONS = {
    "Joy", "Amusement", "Satisfaction", "Excitement", "Pride", "Triumph",
    "Relief", "Romance", "Desire", "Admiration", "Adoration", "Love",
    "Interest", "Realization", "Surprise"
}

NEGATIVE_EMOTIONS = {
    "Anger", "Sadness", "Fear", "Disgust", "Anxiety", "Distress",
    "Shame", "Guilt", "Embarrassment", "Contempt", "Disappointment",
    "Pain", "Awkwardness", "Boredom", "Confusion", "Doubt", "Tiredness"
}

NEUTRAL_EMOTIONS = {
    "Calmness", "Concentration", "Contemplation", "Determination"
}


# Load emotion notification configuration
def load_emotion_config():
    """Load emotion notification configuration from file or environment"""
    config_file = Path("emotion_config.json")

    # Default configuration - empty thresholds = notify for ALL emotions
    default_config = {
        "notification_enabled": True,
        "emotion_thresholds": {}
    }

    # Try to load from file
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                print(f"✓ Loaded emotion config: {config.get('emotion_thresholds')}")
                return config
        except Exception as e:
            print(f"Warning: Could not load emotion_config.json: {e}")
            return default_config

    # Try to load from environment variable
    env_config = os.getenv('EMOTION_NOTIFICATION_CONFIG')
    if env_config:
        try:
            config = json.loads(env_config)
            print(f"✓ Loaded emotion config from env: {config.get('emotion_thresholds')}")
            return config
        except Exception as e:
            print(f"Warning: Could not parse EMOTION_NOTIFICATION_CONFIG: {e}")

    print(f"ℹ️  Using default emotion config: {default_config['emotion_thresholds']}")
    return default_config

# Load configuration at startup
EMOTION_CONFIG = load_emotion_config()


def create_wav_header(sample_rate: int, data_size: int) -> bytes:
    """
    Create a WAV file header for the audio data.

    Args:
        sample_rate: Audio sample rate in Hz (typically 8000 or 16000)
        data_size: Size of the audio data in bytes

    Returns:
        44-byte WAV header
    """
    num_channels = 1  # Mono
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8

    # RIFF header
    header = bytearray()
    header.extend(b'RIFF')
    header.extend((36 + data_size).to_bytes(4, 'little'))
    header.extend(b'WAVE')

    # fmt subchunk
    header.extend(b'fmt ')
    header.extend((16).to_bytes(4, 'little'))  # Subchunk size
    header.extend((1).to_bytes(2, 'little'))   # Audio format (PCM)
    header.extend(num_channels.to_bytes(2, 'little'))
    header.extend(sample_rate.to_bytes(4, 'little'))
    header.extend(byte_rate.to_bytes(4, 'little'))
    header.extend(block_align.to_bytes(2, 'little'))
    header.extend(bits_per_sample.to_bytes(2, 'little'))

    # data subchunk
    header.extend(b'data')
    header.extend(data_size.to_bytes(4, 'little'))

    return bytes(header)


def upload_to_gcs(file_path: str, bucket_name: str, destination_blob_name: str) -> str:
    """
    Upload a file to Google Cloud Storage.

    Args:
        file_path: Path to the local file
        bucket_name: GCS bucket name
        destination_blob_name: Name for the blob in GCS

    Returns:
        Public URL of the uploaded file
    """
    # Get credentials from environment variable
    credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if not credentials_json:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable not set")

    # Decode base64 credentials
    try:
        credentials_dict = json.loads(base64.b64decode(credentials_json))
        credentials = service_account.Credentials.from_service_account_info(credentials_dict)
    except Exception as e:
        raise ValueError(f"Failed to decode credentials: {e}")

    # Create GCS client
    client = storage.Client(credentials=credentials, project=credentials_dict.get('project_id'))
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    # Upload file
    blob.upload_from_filename(file_path, content_type='audio/wav')

    return f"gs://{bucket_name}/{destination_blob_name}"


async def send_notification(
    uid: str,
    message: str
) -> Dict[str, Any]:
    """
    Send a notification to user.

    Args:
        uid: User ID
        message: The notification message

    Returns:
        Dict with success status and response
    """
    omi_app_id = os.getenv('OMI_APP_ID')
    omi_api_key = os.getenv('OMI_API_KEY')

    if not omi_app_id or not omi_api_key:
        return {
            "success": False,
            "error": "OMI_APP_ID or OMI_API_KEY not configured"
        }

    try:
        import httpx
        from urllib.parse import quote

        # Make API request to notification endpoint
        url = f"https://api.omi.me/v2/integrations/{omi_app_id}/notification?uid={quote(uid)}&message={quote(message)}"
        headers = {
            "Authorization": f"Bearer {omi_api_key}",
            "Content-Type": "application/json",
            "Content-Length": "0"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, timeout=30.0)

        if response.status_code >= 200 and response.status_code < 300:
            print(f"✓ Sent notification to user {uid}")

            # Track notification in stats
            from datetime import datetime, timezone
            notification_data = {
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "uid": uid,
                "message": message
            }
            audio_stats["recent_notifications"].insert(0, notification_data)
            # Keep only last 10 notifications
            audio_stats["recent_notifications"] = audio_stats["recent_notifications"][:10]

            return {
                "success": True,
                "message": "Notification sent successfully"
            }
        else:
            error_msg = f"API error: {response.status_code} - {response.text}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }

    except Exception as e:
        print(f"Error sending notification: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


async def create_memory(
    uid: str,
    text: str,
    emotions: list,
    timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a memory based on detected emotions.

    Args:
        uid: User ID
        text: The emotion summary text to save
        emotions: List of detected emotions
        timestamp: Optional timestamp

    Returns:
        Dict with success status and response
    """
    omi_app_id = os.getenv('OMI_APP_ID')
    omi_api_key = os.getenv('OMI_API_KEY')

    if not omi_app_id or not omi_api_key:
        return {
            "success": False,
            "error": "OMI_APP_ID or OMI_API_KEY not configured"
        }

    try:
        import httpx
        from datetime import datetime, timezone

        # Format emotions into a readable string
        emotion_list = ", ".join([f"{e['name']} ({e['score']:.2f})" for e in emotions[:3]])

        # Create memory data
        memory_data = {
            "memories": [
                {
                    "content": f"Emotion detected: {emotion_list}",
                    "tags": ["emotion", "audio_analysis", emotions[0]['name'].lower()]
                }
            ],
            "text": text,
            "text_source": "other",
            "text_source_spec": "emotion_ai_analysis"
        }

        # Make API request
        url = f"https://api.omi.me/v2/integrations/{omi_app_id}/user/memories?uid={uid}"
        headers = {
            "Authorization": f"Bearer {omi_api_key}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=memory_data, headers=headers, timeout=30.0)

        if response.status_code == 200:
            print(f"✓ Created memory for user {uid}")
            return {
                "success": True,
                "message": "Memory created successfully"
            }
        else:
            error_msg = f"API error: {response.status_code} - {response.text}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }

    except Exception as e:
        print(f"Error creating memory: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


def generate_emotion_summary() -> Dict[str, Any]:
    """
    Generate a summary of top 5 emotions from statistics.

    Returns:
        Dict with summary text and top emotions
    """
    if not audio_stats["emotion_counts"]:
        return {
            "success": False,
            "error": "No emotion data available"
        }

    # Get top 5 emotions
    sorted_emotions = sorted(
        audio_stats["emotion_counts"].items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]

    total_count = sum(audio_stats["emotion_counts"].values())

    # Build summary text
    emotion_list = []
    emotions_data = []

    for emotion, count in sorted_emotions:
        percentage = (count / total_count * 100)
        emotion_list.append(f"{emotion} ({percentage:.1f}%)")
        emotions_data.append({
            "name": emotion,
            "score": percentage / 100,  # Convert to 0-1 scale
            "count": count
        })

    summary_text = f"📊 Emotion Summary - Top 5 emotions detected: {', '.join(emotion_list)}"

    return {
        "success": True,
        "summary": summary_text,
        "emotions": emotions_data,
        "total_detections": total_count
    }


async def save_emotion_memory(uid: Optional[str] = None):
    """
    Save current emotion statistics to Omi memories.

    Args:
        uid: User ID to save memory for. If None, uses last active user.
    """
    # Use last active user if no uid provided
    target_uid = uid or audio_stats.get("last_uid")

    if not target_uid:
        print("⚠️ No user ID available for emotion memory")
        return {
            "success": False,
            "error": "No user ID available"
        }

    # Generate emotion summary
    summary = generate_emotion_summary()

    if not summary["success"]:
        print(f"⚠️ Cannot create memory: {summary['error']}")
        return summary

    # Create memory
    result = await create_memory(
        uid=target_uid,
        text=summary["summary"],
        emotions=summary["emotions"]
    )

    return result


async def emotion_memory_background_task():
    """Background task that saves emotion summaries every hour"""
    import asyncio

    while True:
        try:
            # Wait 1 hour (3600 seconds)
            await asyncio.sleep(3600)

            print("⏰ Running hourly emotion memory save...")
            result = await save_emotion_memory()

            if result.get("success"):
                print("✓ Hourly emotion memory saved successfully")
            else:
                print(f"⚠️ Hourly emotion memory save failed: {result.get('error')}")

        except Exception as e:
            print(f"Error in emotion memory background task: {e}")
            import traceback
            traceback.print_exc()


async def cleanup_old_audio_files():
    """Background task that deletes audio files older than 5 minutes"""
    import asyncio
    import time

    while True:
        try:
            # Run cleanup every 1 minute
            await asyncio.sleep(60)

            audio_dir = Path("audio_files")
            if not audio_dir.exists():
                continue

            current_time = time.time()
            deleted_count = 0

            # Check all wav files in audio_files directory
            for audio_file in audio_dir.glob("*.wav"):
                try:
                    # Get file age in seconds
                    file_age = current_time - audio_file.stat().st_mtime

                    # Delete if older than 5 minutes (300 seconds)
                    if file_age > 300:
                        audio_file.unlink()
                        deleted_count += 1
                        print(f"🗑️  Deleted old audio file: {audio_file.name} (age: {file_age/60:.1f} minutes)")

                except Exception as e:
                    print(f"Warning: Could not delete audio file {audio_file}: {e}")

            if deleted_count > 0:
                print(f"✓ Cleanup complete: Deleted {deleted_count} audio file(s)")

        except Exception as e:
            print(f"Error in audio cleanup background task: {e}")
            import traceback
            traceback.print_exc()


def check_emotion_triggers(
    predictions: list,
    emotion_filters: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Check if any emotions meet the threshold criteria.

    Args:
        predictions: List of emotion predictions from Hume
        emotion_filters: Dict of {emotion_name: threshold} to filter by
                        Example: {"Anger": 0.7, "Sadness": 0.6}
                        If None, returns all emotions

    Returns:
        Dict with triggered emotions and details
    """
    triggered_emotions = []

    for prediction in predictions:
        emotions = prediction.get('emotions', [])

        for emotion in emotions:
            emotion_name = emotion['name']
            emotion_score = emotion['score']

            # If no filters, include all
            if not emotion_filters:
                triggered_emotions.append({
                    "name": emotion_name,
                    "score": emotion_score,
                    "time": prediction.get('time')
                })
                continue

            # Check if this emotion is in our filter list (no threshold checking!)
            if emotion_name in emotion_filters:
                triggered_emotions.append({
                    "name": emotion_name,
                    "score": emotion_score,
                    "time": prediction.get('time')
                })

    return {
        "triggered": len(triggered_emotions) > 0,
        "emotions": triggered_emotions,
        "total_triggers": len(triggered_emotions)
    }


async def analyze_text_with_hume(text: str) -> Dict[str, Any]:
    """
    Analyze text with Hume AI Language model for emotional content.

    This analyzes emotion from the text content itself (word choice, phrasing, etc.)
    Different from prosody which analyzes speech tone/pitch.

    Args:
        text: The text to analyze (e.g., transcription from speech-to-text)

    Returns:
        Dict containing emotion predictions for the text
    """
    hume_api_key = os.getenv('HUME_API_KEY')
    if not hume_api_key:
        raise ValueError("HUME_API_KEY environment variable not set")

    try:
        from hume.expression_measurement.stream.stream.types import StreamLanguage

        client = AsyncHumeClient(api_key=hume_api_key)
        # Config with language model for text emotion
        model_config = Config(language=StreamLanguage())

        async with client.expression_measurement.stream.connect() as socket:
            result = await socket.send_text(text, config=model_config)

            # Debug output
            print(f"Text analysis result type: {type(result)}")

            # Check for errors
            if hasattr(result, 'error'):
                return {
                    "success": False,
                    "error": f"Hume API error: {result.error}",
                    "predictions": []
                }

            # Extract language predictions
            if result and hasattr(result, 'language') and result.language:
                lang_preds = result.language.predictions
                print(f"✓ Got {len(lang_preds)} text emotion predictions")

                predictions = []
                for prediction in lang_preds:
                    # Sort emotions by score (highest first)
                    sorted_emotions = sorted(
                        prediction.emotions,
                        key=lambda e: e.score,
                        reverse=True
                    )

                    pred_data = {
                        "text": prediction.text if hasattr(prediction, 'text') else None,
                        "position": {
                            "begin": prediction.position.begin if hasattr(prediction, 'position') else None,
                            "end": prediction.position.end if hasattr(prediction, 'position') else None
                        },
                        "emotions": [
                            {"name": emotion.name, "score": emotion.score}
                            for emotion in sorted_emotions
                        ],
                        "top_3_emotions": [
                            {"name": emotion.name, "score": emotion.score}
                            for emotion in sorted_emotions[:3]
                        ]
                    }
                    predictions.append(pred_data)

                return {
                    "success": True,
                    "predictions": predictions,
                    "total_predictions": len(predictions),
                    "analyzed_text": text
                }
            else:
                error_msg = "No language predictions returned from Hume API"
                print(f"❌ {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "predictions": []
                }

    except Exception as e:
        print(f"Error analyzing text with Hume: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "predictions": []
        }


async def analyze_audio_with_hume(wav_file_path: str) -> Dict[str, Any]:
    """
    Analyze audio file with Hume AI Speech Prosody model.

    Automatically chunks audio >5 seconds into smaller segments.

    Args:
        wav_file_path: Path to the WAV audio file

    Returns:
        Dict containing emotion predictions from Hume AI
    """
    hume_api_key = os.getenv('HUME_API_KEY')
    if not hume_api_key:
        raise ValueError("HUME_API_KEY environment variable not set")

    try:
        from pydub import AudioSegment

        # Load audio to get actual duration
        audio = AudioSegment.from_wav(wav_file_path)
        duration_ms = len(audio)
        duration_seconds = duration_ms / 1000.0

        print(f"Audio duration: {duration_ms}ms ({duration_seconds:.2f} seconds)")

        # Hume WebSocket API limit: 5000ms (5 seconds)
        MAX_CHUNK_MS = 4500  # Use 4.5s to leave safety margin

        # If audio is within limit, send as-is
        if duration_ms <= 5000:
            print(f"✓ Audio is within 5s limit, analyzing directly")
            return await _analyze_single_audio(wav_file_path, hume_api_key)

        # Audio is too long, need to chunk
        print(f"⚠️  Audio is {duration_seconds:.1f}s, chunking into 4.5s segments...")

        chunks_data = []
        chunk_files = []

        try:
            # Split audio into chunks
            num_chunks = (duration_ms + MAX_CHUNK_MS - 1) // MAX_CHUNK_MS  # Ceiling division
            print(f"   Splitting into {num_chunks} chunks")

            for i in range(0, duration_ms, MAX_CHUNK_MS):
                start_ms = i
                end_ms = min(i + MAX_CHUNK_MS, duration_ms)

                chunk = audio[start_ms:end_ms]
                chunk_duration = len(chunk)

                # Save chunk to temporary file
                chunk_path = f"{wav_file_path}.chunk{i // MAX_CHUNK_MS}.wav"
                chunk.export(chunk_path, format="wav")
                chunk_files.append(chunk_path)

                print(f"   Chunk {i // MAX_CHUNK_MS + 1}/{num_chunks}: {start_ms}ms-{end_ms}ms ({chunk_duration}ms)")

                # Analyze chunk
                chunk_result = await _analyze_single_audio(chunk_path, hume_api_key)

                if chunk_result.get('success'):
                    # Adjust time offsets for each prediction
                    for pred in chunk_result['predictions']:
                        pred['time']['begin'] = pred['time']['begin'] + (start_ms / 1000.0) if pred['time']['begin'] else None
                        pred['time']['end'] = pred['time']['end'] + (start_ms / 1000.0) if pred['time']['end'] else None
                        pred['chunk_index'] = i // MAX_CHUNK_MS

                    chunks_data.extend(chunk_result['predictions'])
                else:
                    print(f"   ⚠️  Chunk {i // MAX_CHUNK_MS + 1} analysis failed: {chunk_result.get('error')}")

            # Combine results from all chunks
            if chunks_data:
                return {
                    "success": True,
                    "predictions": chunks_data,
                    "total_predictions": len(chunks_data),
                    "total_duration_seconds": duration_seconds,
                    "num_chunks": num_chunks,
                    "chunked": True
                }
            else:
                return {
                    "success": False,
                    "error": "All chunks failed to analyze",
                    "predictions": [],
                    "debug_info": {
                        "num_chunks": num_chunks,
                        "total_duration_seconds": duration_seconds
                    }
                }

        finally:
            # Clean up chunk files
            for chunk_file in chunk_files:
                try:
                    if Path(chunk_file).exists():
                        Path(chunk_file).unlink()
                except Exception as e:
                    print(f"Warning: Could not delete chunk file {chunk_file}: {e}")

    except Exception as e:
        print(f"Error analyzing audio with Hume: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "predictions": []
        }


async def _analyze_single_audio(wav_file_path: str, hume_api_key: str) -> Dict[str, Any]:
    """
    Analyze a single audio file (must be ≤5 seconds).

    Internal function used by analyze_audio_with_hume.
    """
    try:
        client = AsyncHumeClient(api_key=hume_api_key)
        # Config with only prosody model
        model_config = Config(prosody={})

        async with client.expression_measurement.stream.connect() as socket:
            result = await socket.send_file(wav_file_path, config=model_config)

            # Check if result is an error
            if hasattr(result, 'error'):
                return {
                    "success": False,
                    "error": f"Hume API error: {result.error}",
                    "predictions": []
                }

            # Check for warnings (like "No speech detected")
            warning_msg = None
            if result and hasattr(result, 'prosody') and result.prosody:
                if hasattr(result.prosody, 'warning') and result.prosody.warning:
                    warning_msg = result.prosody.warning
                    print(f"  ⚠️  Hume API warning: {warning_msg}")

            # Extract prosody (speech emotion) predictions
            if result and hasattr(result, 'prosody') and result.prosody:
                prosody_preds = result.prosody.predictions

                # Check if predictions exist and is not None
                if not prosody_preds:
                    error_msg = "No speech detected in audio"
                    if warning_msg:
                        error_msg = f"{error_msg} (Hume: {warning_msg})"
                    return {
                        "success": False,
                        "error": error_msg,
                        "predictions": [],
                        "warning": warning_msg
                    }

                predictions = []
                for prediction in prosody_preds:
                    # Sort emotions by score (highest first)
                    sorted_emotions = sorted(
                        prediction.emotions,
                        key=lambda e: e.score,
                        reverse=True
                    )

                    pred_data = {
                        "time": {
                            "begin": prediction.time.begin if hasattr(prediction.time, 'begin') else None,
                            "end": prediction.time.end if hasattr(prediction.time, 'end') else None
                        },
                        "emotions": [
                            {"name": emotion.name, "score": emotion.score}
                            for emotion in sorted_emotions
                        ],
                        "top_3_emotions": [
                            {"name": emotion.name, "score": emotion.score}
                            for emotion in sorted_emotions[:3]
                        ]
                    }
                    predictions.append(pred_data)

                return {
                    "success": True,
                    "predictions": predictions,
                    "total_predictions": len(predictions)
                }
            else:
                return {
                    "success": False,
                    "error": "No prosody predictions returned from Hume API",
                    "predictions": []
                }

    except Exception as e:
        print(f"Error in _analyze_single_audio: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "predictions": []
        }


@app.post("/audio")
async def handle_audio_stream(
    request: Request,
    sample_rate: int = Query(..., description="Audio sample rate in Hz"),
    uid: str = Query(..., description="User ID"),
    analyze_emotion: bool = Query(True, description="Whether to analyze emotions with Hume AI"),
    save_to_gcs: bool = Query(True, description="Whether to save audio to Google Cloud Storage"),
    enable_notification: Optional[bool] = Query(None, description="Override notification setting (uses config default if not specified)"),
    emotion_filters: Optional[str] = Query(None, description="Override emotion filters (uses config default if not specified)")
):
    """
    Endpoint to receive audio bytes from device, optionally analyze with Hume AI and/or save to GCS.

    Query Parameters:
        - sample_rate: Audio sample rate (e.g., 8000 or 16000)
        - uid: User unique ID
        - analyze_emotion: Whether to analyze emotions with Hume AI (default: True)
        - save_to_gcs: Whether to save audio to GCS (default: True)
        - enable_notification: Whether to send Omi notification (default: False)
        - emotion_filters: JSON string of emotion:threshold pairs
                          Examples:
                          - '{"Anger":0.7}' - notify only if Anger >= 0.7
                          - '{"Anger":0.7,"Sadness":0.6}' - notify if Anger >= 0.7 OR Sadness >= 0.6
                          - null - notify for all detected emotions

    Body:
        - Binary audio data (application/octet-stream)

    Examples:
        # Basic emotion analysis
        POST /audio?sample_rate=16000&uid=user123

        # With notification for any emotion
        POST /audio?sample_rate=16000&uid=user123&enable_notification=true

        # With notification only for high anger or sadness
        POST /audio?sample_rate=16000&uid=user123&enable_notification=true&emotion_filters={"Anger":0.7,"Sadness":0.6}
    """
    try:
        # Update stats
        audio_stats["total_requests"] += 1
        audio_stats["last_request_time"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        audio_stats["last_uid"] = uid

        # Read audio bytes from request body
        audio_data = await request.body()

        if not audio_data:
            raise HTTPException(status_code=400, detail="No audio data received")

        # Generate filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{uid}_{timestamp}.wav"

        # Create WAV header
        wav_header = create_wav_header(sample_rate, len(audio_data))

        # Combine header and audio data
        wav_data = wav_header + audio_data

        # Save to local audio_files directory
        audio_dir = Path("audio_files")
        audio_dir.mkdir(exist_ok=True)
        local_file_path = audio_dir / filename

        with open(local_file_path, 'wb') as f:
            f.write(wav_data)

        try:
            # Analyze with Hume AI if requested
            hume_results = None
            if analyze_emotion:
                print(f"Analyzing audio with Hume AI for user {uid}")
                hume_results = await analyze_audio_with_hume(str(local_file_path))
                print(f"Hume analysis complete: {hume_results.get('total_predictions', 0)} predictions")

                # Update stats
                if hume_results.get('success'):
                    audio_stats["successful_analyses"] += 1
                    # Extract top emotions from prosody predictions
                    recent_emotions = []
                    if hume_results.get('predictions'):
                        for pred in hume_results['predictions']:
                            if pred.get('top_3_emotions'):
                                recent_emotions = [
                                    f"{e['name']} ({e['score']:.2f})"
                                    for e in pred['top_3_emotions']
                                ]
                                # Track emotion counts for statistics
                                for emotion in pred['top_3_emotions']:
                                    emotion_name = emotion['name']
                                    if emotion_name not in audio_stats["emotion_counts"]:
                                        audio_stats["emotion_counts"][emotion_name] = 0
                                    audio_stats["emotion_counts"][emotion_name] += 1

                                break
                    if recent_emotions:
                        audio_stats["recent_emotions"] = recent_emotions

                    # Check emotion triggers and send notification
                    # Use config default if enable_notification not explicitly provided
                    should_notify = enable_notification if enable_notification is not None else EMOTION_CONFIG.get('notification_enabled', False)
                    print(f"🔔 Notification check: should_notify={should_notify}, has_predictions={bool(hume_results.get('predictions'))}")

                    if should_notify and hume_results.get('predictions'):
                        # Use emotion filters from parameter, or fall back to config
                        filters_dict = None
                        if emotion_filters:
                            try:
                                filters_dict = json.loads(emotion_filters)
                                print(f"Using custom emotion filters: {filters_dict}")
                            except json.JSONDecodeError as e:
                                print(f"Warning: Invalid emotion_filters JSON: {e}")
                                filters_dict = EMOTION_CONFIG.get('emotion_thresholds')
                        else:
                            # Use config defaults
                            filters_dict = EMOTION_CONFIG.get('emotion_thresholds')
                            print(f"Using config emotion filters: {filters_dict}")

                        # Check triggers
                        trigger_result = check_emotion_triggers(
                            hume_results['predictions'],
                            filters_dict
                        )
                        print(f"📊 Trigger check result: triggered={trigger_result['triggered']}, count={trigger_result['total_triggers']}")

                        if trigger_result['triggered']:
                            print(f"🔔 Emotion trigger detected! {trigger_result['total_triggers']} emotions matched")

                            # Format notification message with detected emotions
                            emotion_names = [e['name'] for e in trigger_result['emotions'][:3]]
                            emotion_str = ", ".join(emotion_names)
                            notification_msg = f"🎭 Emotion Alert: {emotion_str}"

                            # Send notification
                            notification_result = await send_notification(uid, notification_msg)

                            # Add to response
                            hume_results['notification_sent'] = notification_result.get('success', False)
                            hume_results['triggered_emotions'] = trigger_result['emotions']

                            if notification_result.get('success'):
                                print(f"✓ Notification sent successfully")
                            else:
                                print(f"✗ Notification failed: {notification_result.get('error')}")
                        else:
                            print(f"ℹ️  No emotion triggers matched (filters: {filters_dict})")
                            hume_results['notification_sent'] = False
                            hume_results['trigger_check'] = "No emotions matched threshold"

                else:
                    audio_stats["failed_analyses"] += 1

            # Upload to GCS if requested
            gcs_path = None
            if save_to_gcs:
                bucket_name = os.getenv('GCS_BUCKET_NAME')
                if not bucket_name:
                    print("Warning: GCS_BUCKET_NAME not set, skipping GCS upload")
                else:
                    try:
                        gcs_path = upload_to_gcs(str(local_file_path), bucket_name, filename)
                        print(f"Audio file uploaded successfully: {gcs_path}")
                    except Exception as e:
                        print(f"Warning: Failed to upload to GCS: {e}")
                        # Continue processing even if GCS upload fails

            response_data = {
                "message": "Audio processed successfully",
                "filename": filename,
                "uid": uid,
                "sample_rate": sample_rate,
                "data_size_bytes": len(audio_data),
                "timestamp": timestamp,
                "local_file_path": str(local_file_path.absolute())
            }

            # Add GCS path if available
            if gcs_path:
                response_data["gcs_path"] = gcs_path

            # Add Hume results if available
            if hume_results:
                response_data["hume_analysis"] = hume_results

            return JSONResponse(
                status_code=200,
                content=response_data
            )
        except Exception as e:
            # If there's an error, clean up the file
            if local_file_path.exists():
                local_file_path.unlink()
            raise

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing audio: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with web interface"""
    hume_configured = bool(os.getenv('HUME_API_KEY'))
    gcs_configured = bool(os.getenv('GCS_BUCKET_NAME'))

    # Build emotion statistics HTML
    emotion_stats_html = ''
    if audio_stats['emotion_counts']:
        total_emotion_count = sum(audio_stats['emotion_counts'].values())
        max_emotion_count = max(audio_stats['emotion_counts'].values())
        sorted_emotions = sorted(audio_stats['emotion_counts'].items(), key=lambda x: x[1], reverse=True)[:12]

        emotion_items = []
        for emotion, count in sorted_emotions:
            percentage = (count / total_emotion_count * 100)
            bar_width = (count / max_emotion_count * 100)
            emotion_items.append(f'''
                <div class="emotion-stat-item">
                    <div class="emotion-stat-name">{emotion}</div>
                    <div class="emotion-stat-count">Count: {count} | {percentage:.1f}%</div>
                    <div class="emotion-stat-bar">
                        <div class="emotion-stat-fill" style="width: {bar_width:.1f}%"></div>
                    </div>
                </div>
            ''')

        emotion_stats_html = f'''
            <div style="margin: 20px 0;">
                <h3>🎭 Emotion Statistics</h3>
                <p style="color: #666; font-size: 14px;">Cumulative counts and percentages of all detected emotions</p>
                <div class="emotion-stats">
                    {''.join(emotion_items)}
                </div>
            </div>
        '''


    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🎭 Emotion Meter - Real-time Voice Analysis</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                max-width: 900px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }}
            .container {{
                background: white;
                border-radius: 10px;
                padding: 30px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #333;
                margin-top: 0;
            }}
            .status {{
                display: inline-block;
                padding: 5px 12px;
                border-radius: 5px;
                font-weight: 600;
                margin-left: 10px;
            }}
            .status.online {{
                background: #d4edda;
                color: #155724;
            }}
            .status.offline {{
                background: #f8d7da;
                color: #721c24;
            }}
            .config-section {{
                background: #f8f9fa;
                border-left: 4px solid #007bff;
                padding: 15px;
                margin: 20px 0;
            }}
            .stats {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }}
            .stat-card {{
                background: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
                border-left: 4px solid #28a745;
            }}
            .stat-value {{
                font-size: 28px;
                font-weight: bold;
                color: #333;
            }}
            .stat-label {{
                color: #666;
                font-size: 14px;
                margin-top: 5px;
            }}
            .endpoint {{
                background: #e9ecef;
                padding: 10px;
                border-radius: 5px;
                font-family: monospace;
                margin: 10px 0;
            }}
            .emotions {{
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                margin: 15px 0;
            }}
            .emotion-tag {{
                background: #007bff;
                color: white;
                padding: 5px 12px;
                border-radius: 20px;
                font-size: 12px;
            }}
            .emotion-stats {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: 10px;
                margin: 15px 0;
            }}
            .emotion-stat-item {{
                background: #f8f9fa;
                padding: 10px;
                border-radius: 5px;
                border-left: 3px solid #007bff;
            }}
            .emotion-stat-name {{
                font-weight: bold;
                color: #333;
                font-size: 14px;
            }}
            .emotion-stat-count {{
                color: #666;
                font-size: 12px;
                margin-top: 5px;
            }}
            .emotion-stat-bar {{
                background: #e9ecef;
                height: 8px;
                border-radius: 4px;
                margin-top: 8px;
                overflow: hidden;
            }}
            .emotion-stat-fill {{
                background: linear-gradient(90deg, #007bff, #0056b3);
                height: 100%;
                transition: width 0.3s ease;
            }}
            .refresh-btn {{
                background: #007bff;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                margin-top: 20px;
            }}
            .refresh-btn:hover {{
                background: #0056b3;
            }}
            .check {{
                color: #28a745;
                font-weight: bold;
            }}
            .cross {{
                color: #dc3545;
                font-weight: bold;
            }}
        </style>
        <script>
            function refreshPage() {{
                location.reload();
            }}

            async function resetStats() {{
                if (confirm('Are you sure you want to reset all statistics? This cannot be undone.')) {{
                    try {{
                        const response = await fetch('/reset-stats', {{
                            method: 'POST'
                        }});
                        const data = await response.json();
                        alert('Statistics reset successfully!');
                        location.reload();
                    }} catch (error) {{
                        alert('Error resetting statistics: ' + error.message);
                    }}
                }}
            }}

            // Load current config and pre-check boxes
            async function loadCurrentConfig() {{
                try {{
                    const response = await fetch('/emotion-config');
                    const data = await response.json();
                    const thresholds = data.current_config.emotion_thresholds;

                    document.querySelectorAll('.emotion-checkbox').forEach(checkbox => {{
                        checkbox.checked = checkbox.value in thresholds;
                    }});
                }} catch (error) {{
                    console.error('Error loading config:', error);
                }}
            }}

            // Select all emotions
            function selectAllEmotions() {{
                document.querySelectorAll('.emotion-checkbox').forEach(cb => cb.checked = true);
            }}

            // Clear all emotions
            function clearAllEmotions() {{
                document.querySelectorAll('.emotion-checkbox').forEach(cb => cb.checked = false);
            }}

            // Save emotion configuration
            async function saveEmotionConfig() {{
                const checkboxes = document.querySelectorAll('.emotion-checkbox:checked');
                const thresholds = {{}};

                checkboxes.forEach(cb => {{
                    thresholds[cb.value] = 0;
                }});

                const config = {{
                    notification_enabled: true,
                    emotion_thresholds: thresholds
                }};

                const statusEl = document.getElementById('saveStatus');
                statusEl.textContent = 'Saving...';
                statusEl.style.color = '#666';

                try {{
                    const response = await fetch('/emotion-config', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify(config)
                    }});

                    if (response.ok) {{
                        statusEl.textContent = '✅ Configuration saved successfully!';
                        statusEl.style.color = '#28a745';
                        setTimeout(() => {{ statusEl.textContent = ''; }}, 3000);
                    }} else {{
                        throw new Error('Save failed');
                    }}
                }} catch (error) {{
                    statusEl.textContent = '❌ Error saving configuration';
                    statusEl.style.color = '#dc3545';
                }}
            }}

            // Save emotion memory to Omi
            async function saveEmotionMemory() {{
                const statusEl = document.getElementById('memoryStatus');
                statusEl.textContent = '💾 Saving emotion summary to memories...';
                statusEl.style.color = '#666';

                try {{
                    const response = await fetch('/save-emotion-memory', {{
                        method: 'POST'
                    }});

                    const data = await response.json();

                    if (response.ok) {{
                        statusEl.textContent = '✅ Emotion summary saved to memories!';
                        statusEl.style.color = '#28a745';
                        setTimeout(() => {{ statusEl.textContent = ''; }}, 3000);
                    }} else {{
                        statusEl.textContent = `❌ Error: ${{data.error || 'Failed to save'}}`;
                        statusEl.style.color = '#dc3545';
                    }}
                }} catch (error) {{
                    statusEl.textContent = '❌ Error saving to memories';
                    statusEl.style.color = '#dc3545';
                }}
            }}

            // Load config on page load
            window.addEventListener('DOMContentLoaded', loadCurrentConfig);

            // Auto-refresh every 10 seconds
            setTimeout(refreshPage, 10000);
        </script>
    </head>
    <body>
        <div class="container">
            <h1>🎭 Emotion Meter <span style="font-size: 0.5em; color: #666;">Real-time Voice Analysis</span> <span class="status online">ONLINE</span></h1>
            <p style="text-align: center; color: #666; font-size: 16px; margin: -10px 0 5px 0; font-style: italic;">
                AI-powered emotion detection from voice tone and speech prosody
            </p>
            <p style="text-align: center; color: #999; font-size: 13px; margin: 0 0 10px 0;">
                Developer: Livia Ellen
            </p>
            <p style="text-align: center; color: #999; font-size: 12px; margin: 0 0 30px 0;">
                Powered by <a href="https://www.hume.ai/" target="_blank" style="color: #007bff; text-decoration: none;">Hume EVI API</a> |
                Demo performed with <a href="https://www.omi.me/" target="_blank" style="color: #007bff; text-decoration: none;">Omi AI Voice</a>
            </p>

            <div class="config-section">
                <h3>⚙️ Configuration Status</h3>
                <p><span class="{'check' if hume_configured else 'cross'}">{'✓' if hume_configured else '✗'}</span> Hume AI API Key: {'Configured' if hume_configured else 'Not configured'}</p>
                <p><span class="{'check' if gcs_configured else 'cross'}">{'✓' if gcs_configured else '✗'}</span> Google Cloud Storage: {'Configured' if gcs_configured else 'Not configured (optional)'}</p>
            </div>

            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value">{audio_stats['total_requests']}</div>
                    <div class="stat-label">Total Requests</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{audio_stats['successful_analyses']}</div>
                    <div class="stat-label">Successful Analyses</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{audio_stats['failed_analyses']}</div>
                    <div class="stat-label">Failed Analyses</div>
                </div>
            </div>

            {f'''
            <div style="margin: 20px 0;">
                <h3>📊 Last Activity</h3>
                <p><strong>Time:</strong> {audio_stats['last_request_time']}</p>
                <p><strong>User ID:</strong> {audio_stats['last_uid'][:4] + '****' if audio_stats['last_uid'] and len(audio_stats['last_uid']) > 4 else audio_stats['last_uid']}</p>
                {f'<div class="emotions">' + ''.join([f'<span class="emotion-tag">{e}</span>' for e in audio_stats['recent_emotions'][:5]]) + '</div>' if audio_stats['recent_emotions'] else ''}
            </div>
            ''' if audio_stats['last_request_time'] else '<p style="color: #666; margin: 20px 0;">No audio received yet. Waiting for device to send data...</p>'}

            {emotion_stats_html}

            <div class="config-section">
                <h3>⚙️ Emotion Tracking Configuration</h3>
                <p style="color: #666; font-size: 14px; margin-bottom: 15px;">
                    Select which emotions trigger notifications. Leave all unchecked for ALL emotions.
                </p>

                <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                    <button onclick="selectAllEmotions()" style="padding: 8px 16px; background: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer;">
                        ✓ Select All
                    </button>
                    <button onclick="clearAllEmotions()" style="padding: 8px 16px; background: #6c757d; color: white; border: none; border-radius: 5px; cursor: pointer;">
                        ✗ Clear All
                    </button>
                </div>

                <div id="emotionSelector" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; margin-bottom: 20px;">
                    <!-- Positive Emotions -->
                    <label style="display: flex; align-items: center; gap: 8px; padding: 8px; background: #f8f9fa; border-radius: 5px; cursor: pointer;">
                        <input type="checkbox" name="emotion" value="Joy" class="emotion-checkbox">
                        <span>😊 Joy</span>
                    </label>
                    <label style="display: flex; align-items: center; gap: 8px; padding: 8px; background: #f8f9fa; border-radius: 5px; cursor: pointer;">
                        <input type="checkbox" name="emotion" value="Amusement" class="emotion-checkbox">
                        <span>😄 Amusement</span>
                    </label>
                    <label style="display: flex; align-items: center; gap: 8px; padding: 8px; background: #f8f9fa; border-radius: 5px; cursor: pointer;">
                        <input type="checkbox" name="emotion" value="Satisfaction" class="emotion-checkbox">
                        <span>😌 Satisfaction</span>
                    </label>
                    <label style="display: flex; align-items: center; gap: 8px; padding: 8px; background: #f8f9fa; border-radius: 5px; cursor: pointer;">
                        <input type="checkbox" name="emotion" value="Excitement" class="emotion-checkbox">
                        <span>🤩 Excitement</span>
                    </label>
                    <label style="display: flex; align-items: center; gap: 8px; padding: 8px; background: #f8f9fa; border-radius: 5px; cursor: pointer;">
                        <input type="checkbox" name="emotion" value="Desire" class="emotion-checkbox">
                        <span>😍 Desire</span>
                    </label>

                    <!-- Negative Emotions -->
                    <label style="display: flex; align-items: center; gap: 8px; padding: 8px; background: #f8f9fa; border-radius: 5px; cursor: pointer;">
                        <input type="checkbox" name="emotion" value="Anger" class="emotion-checkbox">
                        <span>😠 Anger</span>
                    </label>
                    <label style="display: flex; align-items: center; gap: 8px; padding: 8px; background: #f8f9fa; border-radius: 5px; cursor: pointer;">
                        <input type="checkbox" name="emotion" value="Sadness" class="emotion-checkbox">
                        <span>😢 Sadness</span>
                    </label>
                    <label style="display: flex; align-items: center; gap: 8px; padding: 8px; background: #f8f9fa; border-radius: 5px; cursor: pointer;">
                        <input type="checkbox" name="emotion" value="Anxiety" class="emotion-checkbox">
                        <span>😰 Anxiety</span>
                    </label>
                    <label style="display: flex; align-items: center; gap: 8px; padding: 8px; background: #f8f9fa; border-radius: 5px; cursor: pointer;">
                        <input type="checkbox" name="emotion" value="Fear" class="emotion-checkbox">
                        <span>😨 Fear</span>
                    </label>
                    <label style="display: flex; align-items: center; gap: 8px; padding: 8px; background: #f8f9fa; border-radius: 5px; cursor: pointer;">
                        <input type="checkbox" name="emotion" value="Distress" class="emotion-checkbox">
                        <span>😖 Distress</span>
                    </label>

                    <!-- Neutral Emotions -->
                    <label style="display: flex; align-items: center; gap: 8px; padding: 8px; background: #f8f9fa; border-radius: 5px; cursor: pointer;">
                        <input type="checkbox" name="emotion" value="Calmness" class="emotion-checkbox">
                        <span>😌 Calmness</span>
                    </label>
                    <label style="display: flex; align-items: center; gap: 8px; padding: 8px; background: #f8f9fa; border-radius: 5px; cursor: pointer;">
                        <input type="checkbox" name="emotion" value="Interest" class="emotion-checkbox">
                        <span>🤔 Interest</span>
                    </label>
                    <label style="display: flex; align-items: center; gap: 8px; padding: 8px; background: #f8f9fa; border-radius: 5px; cursor: pointer;">
                        <input type="checkbox" name="emotion" value="Surprise" class="emotion-checkbox">
                        <span>😲 Surprise</span>
                    </label>
                    <label style="display: flex; align-items: center; gap: 8px; padding: 8px; background: #f8f9fa; border-radius: 5px; cursor: pointer;">
                        <input type="checkbox" name="emotion" value="Contemplation" class="emotion-checkbox">
                        <span>🤨 Contemplation</span>
                    </label>
                    <label style="display: flex; align-items: center; gap: 8px; padding: 8px; background: #f8f9fa; border-radius: 5px; cursor: pointer;">
                        <input type="checkbox" name="emotion" value="Determination" class="emotion-checkbox">
                        <span>😤 Determination</span>
                    </label>
                </div>

                <button onclick="saveEmotionConfig()" class="refresh-btn" style="background: #007bff;">
                    💾 Save Emotion Configuration
                </button>
                <p id="saveStatus" style="color: #666; font-size: 14px; margin-top: 10px;"></p>
            </div>

            <div class="config-section">
                <h3>🔌 API Endpoints</h3>
                <p><strong>Audio Upload (Prosody):</strong></p>
                <div class="endpoint">POST /audio?sample_rate=16000&uid=your_user_id</div>
                <p style="font-size: 12px; color: #666; margin: 5px 0;">Analyzes speech emotion from audio tone/pitch (≤5 seconds)</p>

                <p><strong>Text Emotion Analysis:</strong></p>
                <div class="endpoint">POST /analyze-text?uid=your_user_id</div>
                <p style="font-size: 12px; color: #666; margin: 5px 0;">Analyzes emotion from text content (≤10,000 chars)</p>

                <p><strong>Health Check:</strong></p>
                <div class="endpoint">GET /health</div>

                <p><strong>Status Dashboard:</strong></p>
                <div class="endpoint">GET /status</div>
            </div>

            <div class="config-section">
                <h3>📱 Device Configuration</h3>
                <p>Configure your audio streaming device to send real-time audio to:</p>
                <div class="endpoint" id="audioUrl">{os.getenv('NGROK_URL', 'https://your-server-url.app')}/audio</div>
                <p style="font-size: 12px; color: #666; margin-top: 10px;">
                    Send audio every 10 seconds with sample rate 16000 Hz
                </p>
            </div>

            <div style="display: flex; gap: 10px; margin-top: 20px;">
                <button class="refresh-btn" onclick="refreshPage()">🔄 Refresh Status</button>
                <button class="refresh-btn" onclick="saveEmotionMemory()" style="background: #28a745;">💾 Save to Memories</button>
                <button class="refresh-btn" onclick="resetStats()" style="background: #dc3545;">🗑️ Reset Statistics</button>
            </div>
            <p id="memoryStatus" style="color: #666; font-size: 14px; margin-top: 10px;"></p>
            <p style="color: #666; font-size: 12px; margin-top: 10px;">Page auto-refreshes every 10 seconds</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/status")
async def get_status():
    """Get current server status and stats"""
    hume_configured = bool(os.getenv('HUME_API_KEY'))
    gcs_configured = bool(os.getenv('GCS_BUCKET_NAME'))

    return JSONResponse({
        "status": "online",
        "service": "voice-emotion-analysis",
        "configuration": {
            "hume_ai": hume_configured,
            "google_cloud_storage": gcs_configured
        },
        "stats": audio_stats
    })


@app.post("/analyze-text")
async def analyze_text_emotion(
    request: Request,
    uid: Optional[str] = Query(None, description="User ID (optional)")
):
    """
    Endpoint to analyze emotion from text using Hume AI Language model.

    This analyzes emotional content based on word choice, phrasing, and linguistic patterns.
    Use this endpoint with transcribed text from speech-to-text services.

    Query Parameters:
        - uid: User unique ID (optional)

    Body (JSON):
        {
            "text": "Your text to analyze here",
            "metadata": {...}  // optional metadata
        }

    Example curl:
        curl -X POST "https://your-url/analyze-text?uid=user123" \
             -H "Content-Type: application/json" \
             -d '{"text": "I am feeling really happy and excited today!"}'
    """
    try:
        # Parse JSON body
        body = await request.json()
        text = body.get('text')
        metadata = body.get('metadata', {})

        if not text:
            raise HTTPException(status_code=400, detail="Missing 'text' field in request body")

        # Check text length (API limit is 10,000 characters)
        if len(text) > 10000:
            raise HTTPException(
                status_code=400,
                detail=f"Text too long ({len(text)} characters). Maximum is 10,000 characters."
            )

        print(f"Analyzing text emotion for user: {uid or 'anonymous'}")
        print(f"Text length: {len(text)} characters")
        print(f"Text preview: {text[:100]}...")

        # Analyze text with Hume AI
        hume_results = await analyze_text_with_hume(text)

        response_data = {
            "message": "Text emotion analysis complete",
            "text_length": len(text),
            "uid": uid,
            "hume_analysis": hume_results,
            "metadata": metadata
        }

        return JSONResponse(
            status_code=200,
            content=response_data
        )

    except HTTPException:
        raise
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in request body")
    except Exception as e:
        print(f"Error analyzing text: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/emotion-config")
async def get_emotion_config():
    """Get current emotion notification configuration"""
    return {
        "current_config": EMOTION_CONFIG,
        "description": "Automatic notification settings for detected emotions"
    }


@app.post("/emotion-config")
async def update_emotion_config(request: Request):
    """
    Update emotion notification configuration

    Body (JSON):
    {
        "notification_enabled": true,
        "emotion_thresholds": {
            "Anger": 0.7,
            "Sadness": 0.6
        }
    }
    """
    global EMOTION_CONFIG

    try:
        new_config = await request.json()

        # Validate config
        if "notification_enabled" in new_config:
            if not isinstance(new_config["notification_enabled"], bool):
                raise HTTPException(status_code=400, detail="notification_enabled must be boolean")

        if "emotion_thresholds" in new_config:
            if not isinstance(new_config["emotion_thresholds"], dict):
                raise HTTPException(status_code=400, detail="emotion_thresholds must be a dict")

            # Validate thresholds are numbers between 0 and 1
            for emotion, threshold in new_config["emotion_thresholds"].items():
                if not isinstance(threshold, (int, float)) or threshold < 0 or threshold > 1:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Threshold for {emotion} must be between 0 and 1"
                    )

        # Update configuration
        EMOTION_CONFIG.update(new_config)

        # Save to file
        config_file = Path("emotion_config.json")
        with open(config_file, 'w') as f:
            json.dump(EMOTION_CONFIG, f, indent=2)

        print(f"✓ Updated emotion config: {EMOTION_CONFIG}")

        return {
            "message": "Configuration updated successfully",
            "new_config": EMOTION_CONFIG
        }

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in request body")
    except Exception as e:
        print(f"Error updating config: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/reset-stats")
async def reset_stats():
    """Reset all statistics"""
    global audio_stats
    audio_stats = {
        "total_requests": 0,
        "successful_analyses": 0,
        "failed_analyses": 0,
        "last_request_time": None,
        "last_uid": None,
        "recent_emotions": [],
        "emotion_counts": {},
        "recent_notifications": []
    }
    return {"message": "Statistics reset successfully", "stats": audio_stats}


@app.post("/save-emotion-memory")
async def manual_save_emotion_memory(uid: Optional[str] = Query(None, description="User ID (optional)")):
    """
    Manually save current emotion statistics to Omi memories.

    Query Parameters:
        - uid: User ID (optional, uses last active user if not provided)
    """
    result = await save_emotion_memory(uid)

    if result.get("success"):
        return JSONResponse(
            status_code=200,
            content={
                "message": "Emotion memory saved successfully",
                "result": result
            }
        )
    else:
        return JSONResponse(
            status_code=400,
            content={
                "message": "Failed to save emotion memory",
                "error": result.get("error")
            }
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "voice-emotion-analysis"}


if __name__ == "__main__":
    # Run the server
    uvicorn.run(app, host="0.0.0.0", port=8080)
