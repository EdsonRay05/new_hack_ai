import json
import os
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

import httpx

from pipeline import analyze_image, generate_lesson, repair_code, user_error
from providers import GroqError, active_model, groq_completion, key_variable
from prompts import Analysis
from fastapi.testclient import TestClient
import main


class GroqTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root_patch = patch('providers.ROOT', Path(temporary.name))
        root_patch.start()
        self.addCleanup(root_patch.stop)
        env = patch.dict(os.environ, {'AI_PROVIDER': 'groq', 'GROQ_API_KEY': 'test-key',
                         'GROQ_MODEL': 'openai/gpt-oss-20b', 'GROQ_VISION_MODEL': 'qwen/qwen3.8-27b'})
        env.start()
        self.addCleanup(env.stop)

    def test_separate_models_and_key(self):
        self.assertEqual(active_model(), 'openai/gpt-oss-20b')
        self.assertEqual(active_model(True), 'qwen/qwen3.8-27b')
        self.assertEqual(key_variable(), 'GROQ_API_KEY')
        state = TestClient(main.app).get('/api/health').json()
        self.assertEqual(state['provider'], 'groq')
        self.assertNotIn('test-key', json.dumps(state))

    def test_missing_groq_key_does_not_use_gemini_key(self):
        with patch.dict(os.environ, {'GROQ_API_KEY': '', 'GEMINI_API_KEY': 'other-key'}):
            response = TestClient(main.app).post('/api/generate', json={'problem': 'slope at x=2'})
            self.assertEqual(response.status_code, 503)
            self.assertIn('GROQ_API_KEY', response.json()['detail'])

    def test_image_encoded_and_validated(self):
        result = {'problem': 'x^2 at x=2', 'category': 'derivative_tangent', 'assumptions': [],
                  'learning_question': 'Why slope 4?', 'needs_clarification': False}
        with patch('pipeline.groq_completion', return_value=json.dumps(result)) as request:
            self.assertEqual(analyze_image(b'image'), result)
        self.assertTrue(request.call_args.kwargs['vision'])
        content = request.call_args.args[1]
        self.assertTrue(content[1]['image_url']['url'].startswith('data:image/jpeg;base64,'))

    def test_lesson_and_repair_use_groq(self):
        lesson = {'problem_title': 'Slope', 'visual_intuition': 'Watch the secant become a tangent.',
                  'solution_steps': [dict(step_number=i, action_title='Calculate', formula_used='m = 2x',
                                          why_this_formula='It gives the slope at x.', detailed_walkthrough='x = 2\nm = 2(2) = 4') for i in range(1, 4)],
                  'final_answer': 'm = 4', 'assumptions': [], 'manim_code': 'scene'}
        with patch('pipeline.groq_completion', return_value=json.dumps(lesson)) as request:
            self.assertEqual(generate_lesson('x^2 at x=2', 'derivative_tangent', [])['problem_title'], 'Slope')
            self.assertIn('reference_template', request.call_args.args[1])
        with patch('pipeline.groq_completion', return_value='```python\nfixed\n```'):
            self.assertEqual(repair_code('broken', 'exact trace', 'problem'), 'fixed')

    def test_http_payload_and_response(self):
        reply = httpx.Response(200, json={'choices': [{'message': {'content': '{}'}, 'finish_reason': 'stop'}]})
        with patch('providers.httpx.Client') as factory:
            client = factory.return_value.__enter__.return_value
            client.post.return_value = reply
            self.assertEqual(groq_completion('return json', 'problem', schema=Analysis), '{}')
        payload = client.post.call_args.kwargs['json']
        self.assertEqual(payload['response_format'], {'type': 'json_object'})
        self.assertEqual(payload['reasoning_effort'], 'low')
        self.assertIn('"properties"', payload['messages'][0]['content'])

    def test_retries_only_transient_errors(self):
        ok = httpx.Response(200, json={'choices': [{'message': {'content': 'done'}}]})
        with patch('providers.httpx.Client') as factory, patch('providers.time.sleep'):
            client = factory.return_value.__enter__.return_value
            client.post.side_effect = [httpx.Response(503), ok]
            self.assertEqual(groq_completion('system', 'problem'), 'done')
            self.assertEqual(client.post.call_count, 2)
        with patch('providers.httpx.Client') as factory:
            client = factory.return_value.__enter__.return_value
            client.post.return_value = httpx.Response(429, json={'error': {'message': 'test-key private data'}})
            with self.assertRaises(GroqError) as error:
                groq_completion('system', 'problem')
            self.assertEqual(client.post.call_count, 1)
            self.assertNotIn('test-key', str(error.exception))
            self.assertIn('Groq', user_error(error.exception))

    def test_unavailable_vision_is_actionable(self):
        self.assertIn('type your problem', user_error(GroqError(400, 'model_decommissioned')))


if __name__ == '__main__':
    unittest.main()
