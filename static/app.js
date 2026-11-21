'use strict';
const $ = id => document.getElementById(id);
let selectedFile = null;
let previewUrl = null;
let busy = false;
let health = {};
let typedMode = false;
const sampleProblems = {};

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'The request could not be completed.');
  return body;
}
function error(message) { $('error').textContent = message; $('error').hidden = !message; }
function status(message) { $('status-text').textContent = message; $('status').hidden = !message; }
function syncControls() {
  $('generate-button').disabled = busy || $('problem-text').value.trim().length < 5;
  $('analyze-button').disabled = busy || !selectedFile;
  document.querySelectorAll('[data-sample], .tab, #remove-image, #file-input').forEach(el => { el.disabled = busy; });
  $('problem-text').disabled = busy; $('category').disabled = busy; $('assumptions').disabled = busy;
}
function setBusy(value) { busy = value; syncControls(); }
function setMode(typed) {
  typedMode = typed;
  $('upload-tab').classList.toggle('active', !typed);
  $('type-tab').classList.toggle('active', typed);
  $('upload-section').hidden = typed;
  $('review-section').hidden = !typed && !$('problem-text').value;
}
function clearResult() {
  $('video').pause(); $('video').removeAttribute('src'); $('video').load();
  $('video').hidden = true; $('illustration').hidden = false;
  $('lesson').hidden = true; $('empty-result').hidden = false;
  $('result-badge').textContent = 'A DIFFERENT WAY TO SEE IT';
}
function selectFile(file) {
  if (busy || !file) return;
  error('');
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) return error('Choose a JPG, PNG, or WebP image.');
  if (file.size > 10 * 1024 * 1024) return error('Choose an image smaller than 10 MB.');
  selectedFile = file;
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = URL.createObjectURL(file);
  $('problem-image').src = previewUrl;
  $('image-preview').hidden = false; $('dropzone').hidden = true; $('analyze-button').hidden = false;
  $('problem-text').value = ''; $('assumptions').value = ''; $('review-section').hidden = true;
  $('clarification').hidden = true; clearResult(); syncControls();
}
$('upload-tab').addEventListener('click', () => setMode(false));
$('type-tab').addEventListener('click', () => { setMode(true); $('problem-text').focus(); });
$('file-input').addEventListener('change', event => selectFile(event.target.files[0]));
$('problem-text').addEventListener('input', syncControls);
$('remove-image').addEventListener('click', () => {
  selectedFile = null; if (previewUrl) URL.revokeObjectURL(previewUrl); previewUrl = null;
  $('file-input').value = ''; $('problem-image').removeAttribute('src');
  $('image-preview').hidden = true; $('dropzone').hidden = false; $('analyze-button').hidden = true;
  $('problem-text').value = ''; $('assumptions').value = ''; $('review-section').hidden = !typedMode; clearResult(); syncControls();
});
['dragenter', 'dragover'].forEach(name => $('dropzone').addEventListener(name, event => { event.preventDefault(); $('dropzone').classList.add('drag'); }));
['dragleave', 'drop'].forEach(name => $('dropzone').addEventListener(name, event => { event.preventDefault(); $('dropzone').classList.remove('drag'); }));
$('dropzone').addEventListener('drop', event => selectFile(event.dataTransfer.files[0]));
$('analyze-button').addEventListener('click', async () => {
  if (!selectedFile || busy) return;
  setBusy(true); error(''); status('Reading the equation, values, and units…');
  try {
    const form = new FormData(); form.append('file', selectedFile);
    const result = await api('/api/analyze', { method: 'POST', body: form });
    $('problem-text').value = result.problem; $('category').value = result.category;
    $('assumptions').value = result.assumptions.join('\n');
    $('clarification').hidden = !result.needs_clarification;
    $('review-section').hidden = false; status('Review the recognized problem, then choose “Make it click”.');
  } catch (exc) { error(exc.message); status(''); }
  finally { setBusy(false); }
});

function addList(target, values) {
  target.replaceChildren();
  for (const value of values) { const li = document.createElement('li'); li.textContent = value; target.append(li); }
}
function displayLesson(job) {
  const lesson = job.result;
  $('illustration').hidden = true; $('video').hidden = false;
  $('video').src = lesson.video_url; $('video').load();
  $('lesson').hidden = false; $('empty-result').hidden = true;
  $('result-badge').textContent = `${lesson.duration.toFixed(1)} SEC · ${lesson.height}P`;
  $('lesson-mode').textContent = job.mode === 'sample' ? 'VERIFIED SAMPLE · NO AI CALLS' : 'YOUR CUSTOM VISUAL EXPLANATION';
  $('lesson-title').textContent = lesson.problem_title || lesson.title;
  $('learning-question').textContent = lesson.learning_question || '';
  $('learning-question').hidden = !lesson.learning_question;
  $('lesson-problem').textContent = job.problem;
  $('visual-intuition').textContent = lesson.visual_intuition || '';
  $('steps').replaceChildren();
  const solutionSteps = lesson.solution_steps || (lesson.steps || []).map((text, i) => ({step_number: i + 1, explanation: text}));
  for (const step of solutionSteps) {
    const card = $('solution-step-template').content.cloneNode(true);
    card.querySelector('.step-badge').textContent = `Step ${step.step_number}`;
    card.querySelector('.step-title').textContent = step.action_title || 'Work through the calculation';
    card.querySelector('.step-formula').textContent = step.formula_used || 'Formula not recorded for this older lesson.';
    card.querySelector('.step-why').textContent = step.why_this_formula || step.explanation || '';
    card.querySelector('.step-walkthrough').textContent = step.detailed_walkthrough || step.math_work || '';
    card.querySelector('.detailed-work').hidden = !(step.detailed_walkthrough || step.math_work);
    $('steps').append(card);
  }
  $('final-answer').textContent = lesson.final_answer || '';
  $('final-answer-banner').hidden = !lesson.final_answer;
  const assumptionTitle = document.createElement('strong'); assumptionTitle.textContent = 'Assumptions: ';
  $('assumptions-result').replaceChildren(assumptionTitle, document.createTextNode(lesson.assumptions.join(' ') || 'No additional assumptions supplied.'));
  $('verification').textContent = lesson.verification || 'AI-generated lesson: review the mathematics and assumptions.';
  $('code').textContent = lesson.manim_code || lesson.code;
  $('checks-details').hidden = !lesson.checks?.length;
  addList($('checks'), lesson.checks || []);
  addList($('activity'), job.events.map(event => event.message));
  $('download').href = lesson.video_url;
}
async function poll(jobId) {
  const started = Date.now();
  while (Date.now() - started < 15 * 60 * 1000) {
    const job = await api(`/api/jobs/${jobId}`);
    status(job.message);
    if (job.status === 'error') throw new Error(job.message);
    if (job.status === 'complete') { displayLesson(job); status(''); return; }
    await new Promise(resolve => setTimeout(resolve, 1200));
  }
  throw new Error('The browser stopped waiting after 15 minutes. The server may still be processing the job; check the terminal.');
}
async function startJob(path, body) {
  if (busy) return;
  setBusy(true); error(''); clearResult(); status('Preparing your animation…');
  try {
    const options = { method: 'POST' };
    if (body) { options.headers = { 'Content-Type': 'application/json' }; options.body = JSON.stringify(body); }
    const result = await api(path, options);
    await poll(result.job_id);
  } catch (exc) { error(exc.message); status(''); }
  finally { setBusy(false); }
}
$('generate-button').addEventListener('click', () => startJob('/api/generate', {
  problem: $('problem-text').value.trim(), category: $('category').value,
  assumptions: $('assumptions').value.split('\n').map(s => s.trim()).filter(Boolean).slice(0, 8)
}));
document.querySelectorAll('[data-sample]').forEach(button => button.addEventListener('click', () => {
  if (busy) return;
  const sample = button.dataset.sample;
  if (sampleProblems[sample]) {
    setMode(true); $('problem-text').value = sampleProblems[sample].problem;
    $('category').value = sample; $('assumptions').value = ''; $('clarification').hidden = true;
  }
  startJob(`/api/samples/${sample}`);
}));
Promise.all([api('/api/health'), api('/api/samples')]).then(([state, samples]) => {
  health = state;
  samples.forEach(sample => { sampleProblems[sample.id] = sample; });
  const providerName = state.provider_label || 'AI provider';
  $('health').textContent = state.api_key_configured ? `Local renderer · ${providerName} key configured` : `Sample mode ready · Add a ${providerName} key for your own problems`;
  $('privacy').textContent = state.provider === 'groq'
    ? 'Photos are sent to Groq for analysis. Avoid personal information and review Groq’s data policy.'
    : 'Photos are sent to Google Gemini for analysis. Free-tier content may be used to improve Google’s products.';
  if (!state.manim || !state.ffmpeg || !state.ffprobe) $('health').textContent = 'Rendering setup incomplete · Check /api/health';
}).catch(() => { $('health').textContent = 'Server unavailable · Start the local app'; });
