import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pipeline import analyze_image, generate_lesson, user_error, ResponseFormatError
from prompts import Analysis, GeneratedLesson
from pydantic import ValidationError

ANALYSIS = {'problem': 'Find slope for f(x)=x² at x=2.', 'category': 'derivative_tangent',
            'assumptions': [], 'learning_question': 'Why slope 4?', 'needs_clarification': False}
LESSON = {'problem_title': 'Slope of x²', 'visual_intuition': 'Watch the points come together.',
          'solution_steps': [dict(step_number=i, action_title='Calculate', formula_used='m = 2x',
                                  why_this_formula='It gives the slope at x.', detailed_walkthrough='x = 2\nm = 2(2) = 4') for i in range(1, 4)],
          'final_answer': 'm = 4', 'manim_code': 'scene'}


class ResponseRepairTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {'AI_PROVIDER': 'groq', 'GROQ_API_KEY': 'private-test-key'})
        environment.start()
        self.addCleanup(environment.stop)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        # Keep reference lookup working while diagnostics go to the temporary root.
        (self.root / 'templates').mkdir()
        (self.root / 'templates' / 'derivative_tangent.py').write_text('reference')
        root_patch = patch('pipeline.ROOT', self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)

    def test_missing_solution_field_corrected_once_with_original_problem(self):
        bad = dict(LESSON)
        del bad['final_answer']
        updates = []
        with patch('pipeline.groq_completion', side_effect=[json.dumps(bad), json.dumps(LESSON)]) as call:
            result = generate_lesson('original equation and values', 'derivative_tangent', [],
                                     lambda *args: updates.append(args))
        self.assertEqual(result, {**LESSON, 'learning_question': '', 'assumptions': []})
        self.assertEqual(call.call_count, 2)
        self.assertIn('original equation and values', call.call_args.args[1])
        self.assertNotIn('reference_template', call.call_args.args[1])
        self.assertIn('final_answer', call.call_args.args[0])
        self.assertEqual(len(updates), 1)

    def test_photo_retry_keeps_image_and_distinguishes_stage(self):
        with patch('pipeline.groq_completion', side_effect=['{}', json.dumps(ANALYSIS)]) as call:
            self.assertEqual(analyze_image(b'photo'), ANALYSIS)
        self.assertEqual(call.call_args_list[0].args[1], call.call_args_list[1].args[1])
        self.assertTrue(call.call_args.kwargs['vision'])

    def test_exhaustion_saved_without_key_or_input_values(self):
        with patch('pipeline.groq_completion', return_value='{"secret":"private-test-key"}') as call:
            with self.assertRaises(ResponseFormatError) as failure:
                generate_lesson('problem', 'derivative_tangent', [])
        self.assertEqual(call.call_count, 2)
        self.assertIn('solution generation', str(failure.exception))
        self.assertIn('unchanged', str(failure.exception))
        folder = next((self.root / 'media' / 'response-errors').iterdir())
        self.assertNotIn('private-test-key', (folder / 'response-0.txt').read_text())
        self.assertNotIn('"input"', (folder / 'errors-0.json').read_text())

    def test_valid_fenced_json_needs_no_second_call(self):
        with patch('pipeline.groq_completion', return_value='```json\n' + json.dumps(ANALYSIS) + '\n```') as call:
            self.assertEqual(analyze_image(b'photo'), ANALYSIS)
        self.assertEqual(call.call_count, 1)

    def test_schema_errors_name_correct_stage(self):
        for schema, expected in [(Analysis, 'photo-transcription'), (GeneratedLesson, 'solution format')]:
            try:
                schema.model_validate({})
            except ValidationError as exc:
                self.assertIn(expected, user_error(exc))
