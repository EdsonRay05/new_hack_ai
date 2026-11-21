import io
import os
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

import main
from pipeline import render_with_repair, user_error
import httpx
from google.genai.errors import ClientError, ServerError
from renderer import RenderError
from samples import verify_sample_math
from validation import validate_code

ROOT = Path(__file__).resolve().parents[1]
GOOD = (ROOT / 'templates' / 'derivative_tangent.py').read_text(encoding='utf-8')


class SceneValidationTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {'AI_PROVIDER': 'gemini'})
        env.start()
        self.addCleanup(env.stop)

    def test_network_errors_are_actionable_and_do_not_leak_details(self):
        for exc in [httpx.ConnectError('secret-provider-url'), httpx.ConnectTimeout('secret-provider-url')]:
            message = user_error(exc)
            self.assertNotIn('secret-provider-url', message)
            self.assertIn('connection', message)

    def test_invalid_key_and_model_errors(self):
        exc = ClientError(400, {'error': {'message': 'API key not valid. secret', 'status': 'INVALID_ARGUMENT'}})
        self.assertIn('API key', user_error(exc))
        self.assertNotIn('secret', user_error(exc))
        self.assertIn('GEMINI_MODEL', user_error(ClientError(404, {'error': {'message': 'not found'}})))

    def test_high_demand_is_reported_without_provider_body(self):
        error = ServerError(503, {'error': {'message': 'High demand. secret'}})
        message = user_error(error)
        self.assertIn('temporarily unavailable', message)
        self.assertNotIn('secret', message)

    def test_all_reference_templates_are_allowed(self):
        for path in (ROOT / 'templates').glob('*.py'):
            with self.subTest(template=path.name):
                validate_code(path.read_text(encoding='utf-8'))

    def test_rejects_execution_and_implicit_tex(self):
        for line in ['import os', 'eval("1")', 'self.__class__', 'MathTex("x")',
                     'axes.add_coordinates()', 'open("secret")', 'self.camera = Text("x")']:
            code = 'from manim import *\nclass GeneratedScene(Scene):\n    def construct(self):\n        ' + line
            with self.subTest(line=line), self.assertRaises((ValueError, SyntaxError)):
                validate_code(code)

    def test_plot_lambda_is_allowed_but_body_is_inspected(self):
        prefix = 'from manim import *\nclass GeneratedScene(Scene):\n    def construct(self):\n        '
        validate_code(prefix + 'axes = Axes()\n        curve = axes.plot(lambda x: 3 * x**2)')
        with self.assertRaises(ValueError):
            validate_code(prefix + 'curve = axes.plot(lambda x: open("secret"))')

    def test_repair_uses_exact_error_and_preserves_problem(self):
        updates = []
        with patch('pipeline.render_scene', side_effect=[RenderError('EXACT TRACEBACK'), {'video_url': '/test.mp4'}]) as render, patch('pipeline.repair_code', return_value=GOOD) as repair:
            result = render_with_repair({'code': GOOD}, 'slope at x=2', 'job', lambda *args: updates.append(args))
        repair.assert_called_once_with(GOOD, 'EXACT TRACEBACK', 'slope at x=2')
        self.assertEqual(result['repairs'], 1)
        self.assertEqual(render.call_count, 2)
        self.assertIn('repairing', [u[0] for u in updates])

    def test_maximum_two_repairs(self):
        with patch('pipeline.render_scene', side_effect=RenderError('trace')) as render, patch('pipeline.repair_code', return_value=GOOD) as repair:
            with self.assertRaises(RuntimeError):
                render_with_repair({'code': GOOD}, 'problem', 'job', lambda *args: None)
        self.assertEqual(render.call_count, 3)
        self.assertEqual(repair.call_count, 2)

    def test_validation_failure_saves_diagnostics_before_render(self):
        with tempfile.TemporaryDirectory() as directory, patch('pipeline.ROOT', Path(directory)):
            with self.assertRaisesRegex(RuntimeError, 'failure.txt'):
                render_with_repair({'code': 'not valid python'}, 'problem', 'invalid-scene',
                                   lambda *args: None, allow_repair=False)
            folder = Path(directory) / 'media' / 'invalid-scene'
            self.assertTrue((folder / 'lesson.json').exists())
            self.assertEqual((folder / '0' / 'scene.py').read_text(), 'not valid python')
            self.assertIn('SyntaxError', (folder / '0' / 'failure.txt').read_text())

    def test_no_repairs_for_timeout(self):
        with patch('pipeline.render_scene', side_effect=TimeoutError('timeout')), patch('pipeline.repair_code') as repair:
            with self.assertRaises(TimeoutError):
                render_with_repair({'code': GOOD}, 'problem', 'job', lambda *args: None)
        repair.assert_not_called()

    def test_sample_math(self):
        verify_sample_math()


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def test_home_and_health(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        state = self.client.get('/api/health').json()
        self.assertIn('api_key_configured', state)
        self.assertNotIn('api_key', state)
        self.assertEqual(len(self.client.get('/api/samples').json()), 5)

    def test_normalization_strips_metadata_and_resizes(self):
        output = io.BytesIO()
        Image.new('RGB', (2000, 1200), 'white').save(output, format='PNG')
        result = main.normalize_image(output.getvalue())
        with Image.open(io.BytesIO(result)) as image:
            self.assertEqual(image.format, 'JPEG')
            self.assertEqual(image.size, (1024, 614))
            self.assertEqual(len(image.getexif()), 0)

    def test_invalid_image_rejected_before_api(self):
        response = self.client.post('/api/analyze', files={'file': ('bad.png', b'not an image', 'image/png')})
        self.assertEqual(response.status_code, 400)

    def test_oversized_image(self):
        response = self.client.post('/api/analyze', files={'file': ('big.png', b'x' * (main.MAX_IMAGE + 1), 'image/png')})
        self.assertEqual(response.status_code, 413)

    def test_missing_key_is_actionable(self):
        with patch.dict(os.environ, {'AI_PROVIDER': 'gemini', 'GEMINI_API_KEY': ''}):
            response = self.client.post('/api/generate', json={'problem': 'Find slope at x = 2'})
        self.assertEqual(response.status_code, 503)
        self.assertIn('.env', response.json()['detail'])

    def test_malicious_category_rejected(self):
        response = self.client.post('/api/generate', json={'problem': 'slope at x = 2', 'category': '../../secret'})
        self.assertEqual(response.status_code, 422)

    def test_cross_origin_and_remote_host_denied(self):
        response = self.client.post('/api/generate', json={}, headers={'Origin': 'https://example.com'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.get('/api/health', headers={'Host': 'example.com'}).status_code, 403)

    def test_unknown_job(self):
        self.assertEqual(self.client.get('/api/jobs/unknown').status_code, 404)


if __name__ == '__main__':
    unittest.main()
