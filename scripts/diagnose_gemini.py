"""Minimal model-access check. Never prints API keys or uploaded problem content."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / '.env')
from pipeline import model
from google import genai
from google.genai import types

key = os.getenv('GEMINI_API_KEY', '')
try:
    with genai.Client(api_key=key, http_options=types.HttpOptions(
            timeout=10000, retry_options=types.HttpRetryOptions(attempts=1))) as api:
        response = api.models.generate_content(model=model(), contents='Reply with OK only.')
    print(json.dumps({'success': True, 'model': model(), 'has_text': bool(response.text)}))
except Exception as exc:
    message = str(exc).replace(key, '[REDACTED]') if key else str(exc)
    print(json.dumps({'success': False, 'type': type(exc).__name__,
                      'code': getattr(exc, 'code', None), 'message': message[:1800]}))
    sys.exit(1)
