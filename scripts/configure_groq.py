"""Select Groq without displaying or replacing any existing credentials."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
path = root / '.env'
content = path.read_text(encoding='utf-8') if path.exists() else ''
settings = {'AI_PROVIDER': 'groq', 'GROQ_API_KEY': '', 'GROQ_MODEL': 'openai/gpt-oss-20b',
            'GROQ_VISION_MODEL': 'qwen/qwen3.8-27b'}
for name, value in settings.items():
    pattern = rf'^{name}=.*$'
    if re.search(pattern, content, flags=re.MULTILINE):
        if name == 'AI_PROVIDER':
            content = re.sub(pattern, name + '=' + value, content, flags=re.MULTILINE)
    else:
        content = content.rstrip() + '\n' + name + '=' + value + '\n'
path.write_text(content, encoding='utf-8')
print('Groq selected. Existing keys preserved. Add GROQ_API_KEY locally and restart.')
