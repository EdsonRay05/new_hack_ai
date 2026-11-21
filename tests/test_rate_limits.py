import json
import os
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

import httpx

import providers
from providers import GroqError, groq_completion, reset_seconds, token_budget
from pipeline import user_error


class RateLimitTests(unittest.TestCase):
    def test_reference_request_keeps_room_for_full_worked_lesson(self):
        from prompts import GENERATE, GeneratedLesson
        root = Path(__file__).resolve().parents[1]
        system = GENERATE + '\nReturn only a JSON object matching this schema:\n' + json.dumps(GeneratedLesson.model_json_schema())
        content = json.dumps({'reviewed_problem': 'Find slope of V(t)=t³-6t²+35 at t=5.',
                              'reference_template': (root / 'templates' / 'derivative_tangent.py').read_text(encoding='utf-8')}, ensure_ascii=False)
        estimated, output = token_budget(system, content, 'openai/gpt-oss-20b')
        self.assertLessEqual(estimated + output, 7400)
        self.assertGreaterEqual(output, 3000)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        patches = [patch.dict(os.environ, {'AI_PROVIDER': 'groq', 'GROQ_API_KEY': 'private-key',
                    'GROQ_MODEL': 'openai/gpt-oss-20b', 'GROQ_REQUEST_TOKEN_BUDGET': '7400'}),
                   patch('providers.ROOT', Path(temporary.name)),
                   patch.dict(providers._cooldowns, {}, clear=True),
                   patch.dict(providers._token_limits, {}, clear=True)]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def test_budget_caps_large_prompt_and_counts_images_without_base64(self):
        estimated, output = token_budget('s' * 8000, 'p' * 3000, 'openai/gpt-oss-20b')
        self.assertLessEqual(estimated + output, 7400)
        self.assertLess(output, 4000)
        estimated, output = token_budget('short', [{'type': 'text', 'text': 'read photo'},
            {'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,' + 'a' * 500000}}], 'vision', True)
        self.assertLess(estimated, 3000)
        self.assertEqual(output, 1400)

    def test_oversized_request_is_rejected_before_network(self):
        with patch('providers.httpx.Client') as client:
            with self.assertRaises(GroqError) as error:
                groq_completion('x' * 25000, 'problem')
        client.assert_not_called()
        self.assertEqual(error.exception.reason, 'request_too_large')
        self.assertIn('Waiting will not fix', user_error(error.exception))

    def test_reset_header_units(self):
        self.assertAlmostEqual(reset_seconds('2m59.56s'), 179.56)
        self.assertEqual(reset_seconds('1h2m3s'), 3723)
        self.assertEqual(reset_seconds('120ms'), 0.12)
        self.assertIsNone(reset_seconds('NaN'))
        self.assertIsNone(reset_seconds('private-provider-body'))

    def test_quota_cooldown_prevents_repeated_api_calls(self):
        reply = httpx.Response(429, headers={'retry-after': '12', 'x-ratelimit-limit-tokens': '8000'},
            json={'error': {'message': 'Rate limit reached on tokens per minute (TPM). private-key'}})
        with patch('providers.httpx.Client') as factory, patch('providers.time.monotonic', return_value=100):
            client = factory.return_value.__enter__.return_value
            client.post.return_value = reply
            with self.assertRaises(GroqError) as first:
                groq_completion('system', 'problem')
            with self.assertRaises(GroqError) as second:
                groq_completion('system', 'problem')
        self.assertEqual(client.post.call_count, 1)
        self.assertEqual(first.exception.reason, 'minute_tokens')
        self.assertEqual(second.exception.retry_after, 12)
        self.assertIn('12 seconds', user_error(second.exception))
        self.assertNotIn('private-key', user_error(second.exception))

    def test_daily_and_request_size_are_not_confused(self):
        for message, reason in [('tokens per day (TPD)', 'daily_tokens'),
                                ('requests per day (RPD)', 'daily_requests'),
                                ('Request too large for tokens per minute', 'request_too_large')]:
            with self.subTest(message=message), patch('providers.httpx.Client') as factory:
                factory.return_value.__enter__.return_value.post.return_value = httpx.Response(429,
                    json={'error': {'message': message}})
                with self.assertRaises(GroqError) as error:
                    groq_completion('system', 'problem')
                self.assertEqual(error.exception.reason, reason)
                if reason.startswith('daily'):
                    self.assertIn('daily usage limit', user_error(error.exception))

