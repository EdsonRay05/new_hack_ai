"""Optional real-browser QA with the machine's existing Chrome, no browser download."""
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'media' / 'qa'
ARTIFACTS.mkdir(parents=True, exist_ok=True)
BASE = 'http://127.0.0.1:8011'
custom_lesson = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')) if len(sys.argv) > 1 else None
server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8011'],
                          cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(60):
        if server.poll() is not None:
            raise RuntimeError('QA server exited before startup.')
        try:
            with urlopen(BASE + '/api/health', timeout=1) as response:
                health = json.load(response)
                break
        except OSError:
            time.sleep(0.25)
    else:
        raise RuntimeError('QA server did not start.')
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='chrome', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1100}, device_scale_factor=1)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(BASE)
        page.locator('#health').filter(has_text='Sample mode').wait_for() if not health['api_key_configured'] else None
        page.screenshot(path=str(ARTIFACTS / 'desktop.png'), full_page=True)
        page.locator('[data-sample="derivative_tangent"]').click()
        page.locator('#lesson').wait_for(state='visible', timeout=180000)
        page.locator('#video').evaluate('(video) => video.play()')
        page.wait_for_function('document.getElementById("video").currentTime > 0.2')
        assert page.locator('#lesson-mode').inner_text() == 'VERIFIED SAMPLE · NO AI CALLS'
        assert page.locator('#steps .solution-step-card').count() == 4
        assert page.locator('#steps li').count() == 0
        assert page.locator('#steps .step-badge').all_text_contents() == ['Step 1', 'Step 2', 'Step 3', 'Step 4']
        assert page.locator('#visual-intuition').inner_text()
        assert page.locator('#steps h5').count() == 4
        assert page.locator('#steps .math-work').count() == 4
        assert page.locator('#steps .formula-callout').count() == 4
        for card in page.locator('#steps .solution-step-card').all():
            assert card.locator('h5').count() == 1
            assert card.locator('p').count() == 1
            assert card.locator('.step-formula').count() == 1
            assert card.locator('.step-why').count() == 1
            assert card.locator('.step-walkthrough').count() == 1
            assert len(card.locator('.step-walkthrough').inner_text().splitlines()) >= 2
            assert card.locator('.step-walkthrough').evaluate('(el) => getComputedStyle(el).whiteSpace') == 'pre-line'
        assert 'm = 4' in page.locator('#final-answer').inner_text()
        page.get_by_text('View Generated Manim Python Code', exact=False).click()
        assert 'GeneratedScene' in page.locator('#code').inner_text()
        with page.expect_download() as download:
            page.locator('#download').click()
        download.value.save_as(str(ARTIFACTS / 'download.mp4'))
        assert (ARTIFACTS / 'download.mp4').stat().st_size > 1000
        page.locator('#video').evaluate('(video) => { video.pause(); video.currentTime = 7; }')
        page.wait_for_function('!document.getElementById("video").seeking')
        page.screenshot(path=str(ARTIFACTS / 'lesson.png'), full_page=True)
        for sample in ['integral_riemann', 'projectile_motion']:
            page.locator(f'[data-sample="{sample}"]').click()
            page.locator('#lesson').wait_for(state='visible', timeout=180000)
            page.wait_for_function('document.getElementById("video").readyState >= 1')
            assert page.locator('#error').is_hidden()
        if custom_lesson:
            # Replay a real saved provider response through the UI without
            # spending another model request. The MP4 is served by the real server.
            page.route('**/api/generate', lambda route: route.fulfill(status=202, json={'job_id': 'qa-custom'}))
            page.route('**/api/jobs/qa-custom', lambda route: route.fulfill(json={
                'status': 'complete', 'message': 'Ready', 'mode': 'custom', 'events': [],
                'problem': 'Find the tangent to f(x) = 15 - 2x² at x = 1.', 'result': custom_lesson}))
            page.locator('#type-tab').click()
            page.locator('#problem-text').fill('Find the tangent to f(x) = 15 - 2x² at x = 1.')
            page.locator('#generate-button').click()
            page.locator('#lesson').wait_for(state='visible')
            assert page.locator('#steps h5').count() == len(custom_lesson['solution_steps'])
            assert '+ 17' in page.locator('#final-answer').inner_text()
            page.wait_for_function('document.getElementById("video").readyState >= 1')
            page.locator('#video').evaluate('(video) => { video.pause(); video.currentTime = 11; }')
            page.wait_for_function('!document.getElementById("video").seeking')
            page.screenshot(path=str(ARTIFACTS / 'custom-lesson.png'), full_page=True)
            page.unroute('**/api/generate')
            page.unroute('**/api/jobs/qa-custom')
        page.set_viewport_size({'width': 390, 'height': 844})
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        page.screenshot(path=str(ARTIFACTS / 'mobile-lesson.png'), full_page=True)
        page.locator('#upload-tab').click()
        page.locator('#file-input').set_input_files(str(ROOT / 'static' / 'samples' / 'derivative_tangent.png'))
        assert page.locator('#image-preview').is_visible()
        if not health['api_key_configured']:
            page.locator('#analyze-button').click()
            page.locator('#error').wait_for(state='visible')
            assert '.env' in page.locator('#error').inner_text()
        page.locator('#type-tab').click()
        page.locator('#problem-text').fill('For f(x)=3x^2, visualize the slope at x=1.')
        assert page.locator('#generate-button').is_enabled()
        if not health['api_key_configured']:
            page.locator('#generate-button').click()
            page.wait_for_function('document.getElementById("error").textContent.includes(".env")')
        page.set_viewport_size({'width': 390, 'height': 844})
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        page.screenshot(path=str(ARTIFACTS / 'mobile.png'), full_page=True)
        assert not errors, errors
        browser.close()
        print(json.dumps({'browser': 'Chrome', 'sample_videos': 3, 'download': 'passed',
                          'custom_lesson_replay': bool(custom_lesson),
                          'image_upload': 'passed', 'mobile_overflow': False, 'page_errors': errors,
                          'screenshots': str(ARTIFACTS)}, indent=2))
finally:
    server.terminate()
    server.wait(timeout=15)
