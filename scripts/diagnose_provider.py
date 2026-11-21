"""Credential-safe access check for the selected provider."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / '.env')
from providers import provider, key_variable, active_model, groq_completion
from pipeline import user_error

try:
    if provider() != 'groq':
        raise RuntimeError('For Gemini use scripts/diagnose_gemini.py.')
    if not os.getenv(key_variable(), '').strip():
        raise RuntimeError('Add GROQ_API_KEY to .env first.')
    text = groq_completion('Reply briefly.', 'Reply with OK.', max_output_tokens=64)
    print(json.dumps({'success': True, 'provider': provider(), 'model': active_model(), 'has_text': bool(text)}))
except Exception as exc:
    print(json.dumps({'success': False, 'type': type(exc).__name__, 'code': getattr(exc, 'code', None),
                      'message': user_error(exc)}))
    sys.exit(1)
