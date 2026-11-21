"""Explicit provider selection; no automatic provider/account fallback."""
import json
import os
import time
import math
import re
from pathlib import Path
import httpx

_cooldowns = {}
_token_limits = {}
ROOT = Path(__file__).resolve().parent


def reset_seconds(value):
    """Parse Groq reset headers such as 7.66s, 2m59.56s, or numeric seconds."""
    if not value:
        return None
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        parts = re.findall(r'(\d+(?:\.\d+)?)(ms|s|m|h|d)', str(value))
        if not parts or ''.join(a+b for a, b in parts) != str(value):
            return None
        units = {'ms': 0.001, 's': 1, 'm': 60, 'h': 3600, 'd': 86400}
        seconds = sum(float(number)*units[unit] for number, unit in parts)
    return min(seconds, 7*86400) if math.isfinite(seconds) and seconds >= 0 else None


def token_budget(system, content, model_name, vision=False, maximum=None):
    # Conservative estimate, not the provider's tokenizer. Exclude image base64:
    # image tokens are counted separately, not as millions of text characters.
    if isinstance(content, list):
        strings = [part.get('text', '') for part in content if isinstance(part, dict) and part.get('type') == 'text']
        images = sum(part.get('type') == 'image_url' for part in content if isinstance(part, dict))
        text = system + '\n' + '\n'.join(strings)
    else:
        text, images = system + '\n' + str(content), 0
    estimated_input = math.ceil(len(text.encode('utf-8')) / 3) + 100 + images*2048
    cap = min(int(os.getenv('GROQ_REQUEST_TOKEN_BUDGET', '7400')), _token_limits.get(model_name, 8000) - 600)
    desired = maximum if maximum is not None else (1400 if vision else 4000)
    output = min(desired, cap - estimated_input)
    if output < (min(512, desired) if vision else min(1000, desired)):
        raise GroqError(429, 'request_too_large')
    return estimated_input, output


def provider():
    value = os.getenv('AI_PROVIDER', 'gemini').strip().lower()
    if value not in {'gemini', 'groq'}:
        raise RuntimeError('AI_PROVIDER must be groq or gemini in .env.')
    return value


def provider_label():
    return 'Groq' if provider() == 'groq' else 'Google Gemini'


def key_variable():
    return 'GROQ_API_KEY' if provider() == 'groq' else 'GEMINI_API_KEY'


def active_model(vision=False):
    if provider() == 'groq':
        return os.getenv('GROQ_VISION_MODEL', 'qwen/qwen3.8-27b') if vision else os.getenv('GROQ_MODEL', 'openai/gpt-oss-20b')
    return os.getenv('GEMINI_MODEL', 'gemini-3.8-flash')


class GroqError(Exception):
    def __init__(self, code, reason='', retry_after=None):
        self.code = code
        self.reason = reason
        self.retry_after = retry_after
        super().__init__(f'Groq request failed (HTTP {code}).')


def groq_completion(system: str, content, schema=None, vision=False, max_output_tokens=None) -> str:
    key = os.getenv('GROQ_API_KEY', '').strip()
    if not key:
        raise RuntimeError('Add GROQ_API_KEY to .env and restart. Sample mode works without a key.')
    selected_model = active_model(vision)
    cooldown = _cooldowns.get(selected_model)
    if cooldown and cooldown[0] > time.monotonic():
        raise GroqError(429, cooldown[1], math.ceil(cooldown[0] - time.monotonic()))
    if schema:
        system += '\nReturn only a JSON object matching this schema:\n' + json.dumps(schema.model_json_schema())
    estimated_input, output_limit = token_budget(system, content, selected_model, vision, max_output_tokens)
    body = {'model': selected_model, 'messages': [
        {'role': 'system', 'content': system}, {'role': 'user', 'content': content}],
        'temperature': 0.1, 'max_completion_tokens': output_limit}
    if schema:
        body['response_format'] = {'type': 'json_object'}
    if selected_model.startswith('openai/gpt-oss-'):
        body['reasoning_effort'] = 'low'
    with httpx.Client(timeout=httpx.Timeout(60, connect=15)) as api:
        for attempt in range(2):
            response = api.post('https://api.groq.com/openai/v1/chat/completions',
                                headers={'Authorization': f'Bearer {key}'}, json=body)
            limit = response.headers.get('x-ratelimit-limit-tokens', '')
            if limit.isdigit():
                _token_limits[selected_model] = int(limit)
            if response.status_code >= 500 and attempt == 0:
                time.sleep(1)
                continue
            if response.is_error:
                reason = ''
                message = ''
                try:
                    code = response.json().get('error', {}).get('code', '')
                    if code in {'model_decommissioned', 'model_not_found', 'invalid_api_key'}:
                        reason = code
                    message = str(response.json().get('error', {}).get('message', '')).lower()
                except (ValueError, AttributeError):
                    pass
                retry_after = None
                if response.status_code == 429:
                    if 'request too large' in message or 'request_too_large' in message:
                        reason = 'request_too_large'
                    elif 'tokens per day' in message or 'tpd' in message:
                        reason = 'daily_tokens'
                    elif 'requests per day' in message or 'rpd' in message:
                        reason = 'daily_requests'
                    elif 'tokens per minute' in message or 'tpm' in message:
                        reason = 'minute_tokens'
                    elif 'requests per minute' in message or 'rpm' in message:
                        reason = 'minute_requests'
                    elif response.headers.get('x-ratelimit-remaining-requests') == '0':
                        reason = 'daily_requests'
                    elif response.headers.get('x-ratelimit-remaining-tokens') == '0':
                        reason = 'minute_tokens'
                    retry_after = reset_seconds(response.headers.get('retry-after'))
                    if retry_after is None:
                        header = 'x-ratelimit-reset-requests' if reason == 'daily_requests' else 'x-ratelimit-reset-tokens' if reason == 'minute_tokens' else None
                        retry_after = reset_seconds(response.headers.get(header)) if header else None
                    if retry_after and reason != 'request_too_large':
                        _cooldowns[selected_model] = (time.monotonic() + retry_after, reason)
                    directory = ROOT / 'media'
                    directory.mkdir(parents=True, exist_ok=True)
                    safe_details = {'model': selected_model, 'reason': reason or 'rate_limit',
                                    'retry_after_seconds': retry_after, 'estimated_input_tokens': estimated_input,
                                    'reserved_output_tokens': output_limit,
                                    'limits': {name: value for name, value in response.headers.items()
                                               if name.startswith('x-ratelimit-') and re.fullmatch(r'[0-9.hmsd]+', value)}}
                    (directory / 'groq-rate-limit.json').write_text(json.dumps(safe_details, indent=2), encoding='utf-8')
                raise GroqError(response.status_code, reason, retry_after)
            data = response.json()
            try:
                choice = data['choices'][0]
                if choice.get('finish_reason') == 'length':
                    raise RuntimeError('Groq reached the response length limit. Try a simpler problem.')
                text = choice['message']['content']
            except (KeyError, IndexError, TypeError) as exc:
                raise RuntimeError('Groq returned an empty or invalid response. Please retry.') from exc
            if not isinstance(text, str) or not text.strip():
                raise RuntimeError('Groq returned no lesson text. Please retry.')
            return text
    raise RuntimeError('Groq request did not complete.')
