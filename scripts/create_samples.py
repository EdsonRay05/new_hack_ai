"""Draw original sample problem cards; no downloaded or generated raster assets."""
from pathlib import Path
import sys
import textwrap

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from samples import SAMPLES

destination = ROOT / 'static' / 'samples'
destination.mkdir(parents=True, exist_ok=True)
font_path = 'C:/Windows/Fonts/arial.ttf'
font = ImageFont.truetype(font_path, 29) if Path(font_path).exists() else ImageFont.load_default(size=29)
small = ImageFont.truetype(font_path, 19) if Path(font_path).exists() else ImageFont.load_default(size=19)
for category in list(SAMPLES)[:3]:
    lesson = SAMPLES[category]
    image = Image.new('RGB', (1024, 560), '#f6f8fb')
    draw = ImageDraw.Draw(image)
    draw.text((60, 48), 'INTUITIONLENS / SAMPLE PROBLEM', font=small, fill='#496777')
    draw.line((60, 95, 964, 95), fill='#bbcbd3', width=2)
    lines = textwrap.fill(lesson['problem'], width=51)
    draw.multiline_text((60, 145), lines, font=font, fill='#152631', spacing=18)
    draw.text((60, 475), 'Explain the idea visually. State your assumptions.', font=small, fill='#496777')
    image.save(destination / f'{category}.png')
