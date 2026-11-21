# IntuitionLens

See the idea behind the equation. A local FastAPI app that turns a reviewed STEM problem into a short Manim animation and a plain-English explanation.

## Groq setup (selected provider)

Lessons return `problem_title`, `visual_intuition`, 3–5 numbered `solution_steps`, `final_answer`, and `manim_code`, plus optional learning question and assumptions. Each step has five fields: `step_number`, `action_title`, `formula_used`, `why_this_formula`, and `detailed_walkthrough`. The general rule is stated before substitution, a short rationale connects it to the problem, and a multiline walkthrough shows intermediate work. Both AI providers share this schema. The interface groups each step into a card with a numbered pill and goal, a highlighted monospace formula callout, its rationale, and a separate calculation block that preserves line breaks. All five sample lessons use the same format; the derivative example has four worked steps. Older saved lessons remain displayable without inventing missing formulas. A final-answer banner follows the cards, with actual final Python source in the last disclosure.

Evaluated numbers share one Python source: define pure numeric functions, compute point values/slopes/intercepts/areas and other results before labels, then reuse those variables in both geometry and f-string Text. Given formulas may be literal; evaluated readouts may not be independently hardcoded. Validation rejects hardcoded numeric point, slope, result, and tangent labels and inspects permitted pure arithmetic functions. The prompt requires a term-by-term Math Verification Pass with a final substitution check before writing the worked solution or scene. This improves consistency; it is not a general mathematical proof system. `scripts/verify_math_labels.py` reproduces the reported V(t)=t³-6t²+35 at t=5 case locally, checks the actual dot and Text agree at (5,10), verifies slope 15/intercept -65, and renders its MP4 without AI calls. Duplicate prompt instructions were condensed so the sample request still reserves at least 3,000 output tokens under the estimated free-tier request budget.

Visible math uses Unicode rather than raw LaTeX/caret exponents. All five references use explicit `Text` axis labels. A module-level `add_plain_axis_numbers(axes, x_vals, y_vals)` helper adds selected nonzero numeric ticks with 16-point gray `Text`; built-in numbers, `add_coordinates`, `DecimalNumber`, and `Integer` are prohibited. The title uses font size 30 and `to_edge(UP, buff=0.35)`. Axes use `x_length=6.2, y_length=4.5`. Formulas, readouts, and answers belong to `info_panel`, arranged down with left alignment and 0.35 row spacing. Its border and content form `info_box`, positioned with `next_to(axes, RIGHT, buff=0.65)`. `VGroup(axes_group, info_box)` is centered at the origin, then shifted down 0.25. Axes labels and tick numbers belong to axes_group before centering; curves, points, and guides use the moved axes afterward. Subtle dashed coordinate guides connect points of interest to their axis values. Readout replacements retain their row position and line count. The validator inspects the numeric helper, rejects built-in coordinate numbers and long/formula Text attached via `next_to`, and permits small coordinate annotations. Reference tangent/secant segments extend 1.5 data units on each side of the fixed point. Numerically resolvable named tangent/secant `Line` constructions also receive local centering correction, preserving their supplied slope. This is a geometry correction, not derivative verification. Inspected local math lambdas remain callable.

Sample video caches are invalidated when their reference source changes. `scripts/check_template_layout.py` checks actual reference text bounds, title/panel separation, the exact 0.65 graph/box gap, centering at (0,-0.25), pure Text nonzero tick labels, guide endpoints, and changing readout containment without producing movies. The unit-circle reference stacks the circle and wave traces within the graph zone.

Groq support is included for image analysis, lesson generation, and traceback repair. Create a key at https://console.groq.com/keys using the Free plan, then set these values in the existing `.env` file (preserve your Gemini key if you want to switch back later):

```dotenv
AI_PROVIDER=groq
GROQ_API_KEY=your_key_here
GROQ_MODEL=openai/gpt-oss-20b
GROQ_VISION_MODEL=qwen/qwen3.8-27b
```

Restart Uvicorn after saving. No Groq SDK installation is needed; the adapter uses `httpx`. The text model handles custom scenes and repairs; the vision model reads images. Model access is account-dependent; if Qwen vision is unavailable, choose **Type it out** and use the text pipeline. Check the current model list and your account limits rather than relying on older Llama vision model names. Free-plan quota exhaustion is surfaced as an error; there is no provider or paid-plan fallback. Keep the account on the Free plan to preserve the budget.

The Groq adapter requests JSON mode and validates responses locally with Pydantic. It does not claim provider-guaranteed schema compliance. It retries HTTP 5xx once and does not retry quota/authentication errors. The health endpoint reports the selected provider, generation model, image model, and key presence without exposing credentials.

Groq token budgeting defaults to a conservative estimated 7,400 input-plus-output tokens per request (`GROQ_REQUEST_TOKEN_BUDGET`), below the documented 8K TPM allowance for the default free-tier models. Output reservations are adaptive: up to 4,000 text tokens / 1,400 vision tokens, reduced when the input is large. Image base64 bytes are excluded from the text estimate and image tokens are counted separately. This is an estimate, not Groq's exact tokenizer or a guarantee of quota availability. Format correction omits the duplicate reference script. Daily usage, earlier calls, and other apps sharing the organization can still exhaust the account quota.

429 errors distinguish oversized requests, minute limits, and daily limits when Groq identifies them. Server `retry-after`/reset headers supply the displayed wait; known cooldowns prevent repeated API calls for that model within the running process. No paid plan, alternate-account rotation, or rate-limit retry is used. A credential-free quota diagnostic is saved to `media/groq-rate-limit.json` on actual 429 responses. Restarting the application does not reset Groq's account quota.

Photo transcription and solution generation have separate response-format errors. On invalid Groq JSON/schema output, the app makes at most one extra format-correction request, preserving the original photo or reviewed problem. This is separate from Manim code repair. Markdown-fenced valid JSON is accepted locally. Invalid provider responses and field errors are stored under `media/response-errors/` for diagnosis, with configured API keys redacted; these files may contain generated problem/solution text, but never the uploaded image bytes or request headers. A failed correction reports the stage and diagnostic location instead of suggesting the photo itself must be wrong.

Successful renders outside the 8–15 second limit receive one local pacing adjustment toward 12 seconds and are rendered again. This changes playback timing in the scene code, preserves equations and geometry, and preserves a literal final `wait(1.5)`. It does not consume an AI repair attempt. If the adjusted scene still fails, the normal bounded repair loop applies. The code viewer shows the final adjusted source. Both renders and their metadata are retained for diagnosis.

Every attempted scene is saved before validation, including failures that occur before Manim starts. Look in `media/<job-id>/<attempt>/failure.txt` for the failure and `media/<job-id>/lesson.json` for the original lesson. You can retry a saved lesson locally without AI requests:

```powershell
.\.venv\Scripts\python.exe scripts/recover_lesson.py media/<job-id>/lesson.json
```

To check the configured Groq key after saving it:

```powershell
.\.venv\Scripts\python.exe scripts/diagnose_provider.py
```

This makes a real short text request. It does not verify image-model permissions or full scene rendering. Set `AI_PROVIDER=gemini` to use the Gemini setup below. Samples work with either provider and no key.

## Start on Windows

Python 3.11+ is the target. This checkout was installed and tested with Python 3.14.4 and Manim Community 0.22.1 on Windows. Install the FFmpeg tools (`ffmpeg` and `ffprobe`) and put both on PATH. No LaTeX, Node build, hosting account, or paid API is required.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Choose one of the three sample cards to render a verified example without an API key. All five samples are also available through `/api/samples` and the API. The first sample render takes time; successful sample videos are cached for later use.

To pre-render every example for an internet-independent demonstration:

```powershell
.\.venv\Scripts\python.exe scripts/verify_renders.py
```

For your own uploaded or typed problem:

```powershell
Copy-Item .env.example .env
```

Edit `.env` locally to set `GEMINI_API_KEY`, then restart the server. Do not put the key in the browser or commit it. `GEMINI_MODEL` defaults to `gemini-3.8-flash`; availability and quotas depend on your project. Use an eligible free-tier project with billing disabled to preserve the $0 service budget. The application does not enable billing or silently choose a paid model. It cannot enforce the billing configuration of an externally supplied key.

## Use

1. Upload a JPEG, PNG, or WebP image (at most 10 MB), then choose **Read this problem**. Or choose **Type it out**.
2. Review and correct the transcription, concept, and assumptions. Ambiguous images are flagged.
3. Choose **Make it click**. Follow the real job status through scene generation, rendering, and any repairs.
4. Play/download the MP4, read the intuition steps, and inspect the final code and activity log.

Sample mode is explicitly labeled and never substitutes for failed custom generation. Known sample calculations have independent scalar checks. AI-generated mathematics is not automatically proven correct; the interface says so. The initial graph is an illustrative concept preview, not a generated result.

## Architecture

```text
Image → validate / orient / resize → Gemini transcription + category
      → student review → retrieve reference template → Gemini structured lesson
      → AST rejection checks → Manim subprocess → ffprobe checks → local MP4
                                  ↓ render/code failure
                         traceback + code → Gemini repair
                              maximum two repairs
```

The UI uses local CSS and vanilla JavaScript rather than a Tailwind CDN, so sample mode has no external frontend dependency. Five 480p reference scenes cover tangent slopes, Riemann sums, projectiles, vector addition, and the unit circle. Scenes use Pango `Text`, not LaTeX. Video duration is checked against the 8–15 second acceptance range; most scenes target 10–14 seconds. Duration of the resulting video is different from generation latency.

`main.py` manages uploads, a single-render queue, job status, and sample caching. `pipeline.py` owns structured Gemini calls and the repair loop. `renderer.py` runs Manim with a timeout and verifies H.264 MP4 metadata. `validation.py` conservatively rejects unsupported Python. `prompts.py` contains schemas and prompts. `samples.py` contains sample explanations and calculations.

Jobs are held in memory, disappear on restart, and expire from status lookup after an hour once complete. Files in `media/` and `static/outputs/` remain until manually removed while the app is stopped. Images are processed in memory; originals are not saved by the backend. Working scripts and local renderer logs are retained for diagnosis. The queue accepts at most four active jobs. Use one Uvicorn worker; this is not a distributed queue.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Dependency and key presence checks; not a live model-access test |
| `POST /api/analyze` | Multipart image under field `file` |
| `POST /api/generate` | JSON `problem`, `category`, `assumptions`; returns job ID |
| `GET /api/jobs/{job_id}` | Job status, events, final lesson or error |
| `GET /api/samples` | Five known example problems |
| `POST /api/samples/{sample_id}` | Start a no-key sample job |

## Checks

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/verify_renders.py
```

Unit checks cover image normalization, invalid/oversized uploads, key handling, host/origin restrictions, prohibited code, reference compatibility, sample calculations, traceback propagation, timeout behavior, and exactly two repair retries. Render verification executes real Manim for all five scenes and writes `media/render-verification.json`. `tests/evaluation.json` supplies ten manual evaluation cases, including problems that differ from the stock templates.

Optional browser checks use `pip install playwright` with an existing local Chrome installation and `python scripts/browser_check.py`. They exercise sample playback, output download, code display, image upload, error handling, and responsive layouts. The script starts a temporary local server and stops it on exit.

## Privacy and execution boundaries

The app and video rendering run on localhost. Uploaded images and reviewed text are sent to Google for AI analysis/generation; free-tier data handling follows Google's terms. Avoid personal details in problem photos.

Generated Python is executable code. AST checks, a separate process, credential filtering, a timeout, and local host/origin restrictions reduce risk, but **are not a complete security sandbox**. This is for trusted personal localhost experimentation. Do not expose it to a network or run it as an administrator. Public or multi-user use requires OS/container isolation and resource limits. The renderer environment omits application API keys; it still runs as your user and is not filesystem-isolated.

## Troubleshooting

- **No key:** sample cards work without one; custom problems need `.env` and a restart.
- **Model unavailable:** set a supported free-tier `GEMINI_MODEL` for your project. No live account access is implied by the health endpoint.
- **Quota exhausted:** wait for reset or use cached samples. There is no automatic paid fallback.
- **Rendering failure:** inspect `media/<job-id>/<attempt>/render.log`. Missing dependencies and timeouts are not treated as syntax problems.
- **No FFprobe:** add the FFmpeg distribution's `bin` folder to PATH, then restart the terminal and server.
- **Python dependency installation:** Windows wheels are available for the tested setup. If your platform lacks wheels, follow the Manim Community installation guide for its native dependencies.

Hackathon dates and rubric targets in the original brief are user-supplied and have not been independently confirmed.
