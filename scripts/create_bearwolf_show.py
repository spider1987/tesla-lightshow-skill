"""Compose the Model 3 show and add a music-driven center-display layer."""
import colorsys
import argparse
import hashlib
import json
import struct
import wave
from pathlib import Path

from compose_show import Composer
from fseq_writer import FseqWriter

root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument('--song', default='BEARWOLF-Владивосток')
parser.add_argument('--palette', choices=['neon', 'fire'], default='neon')
args = parser.parse_args()
base = root / 'LightShow' / args.song
analysis = json.loads(base.with_suffix('.analysis.json').read_text())
# The fallback analyzer marked the audible intro as non-music and gave
# every section the same label. Keep the full recording and use the
# composer's energy-peak narrative fallback rather than those labels.
analysis['music_start'] = 0
analysis['music_end'] = analysis['n_frames']
analysis['segments'] = []
composer = Composer(analysis, 'model_3')
composer.compose()
n = composer.n
writer = FseqWriter(200, n, composer.STEP_MS)
beats = set(analysis['beat_frames'])
envelope = 0.0
flash = 0.0
start = analysis.get('music_start', 0)
end = analysis.get('music_end', n)
duration = n * composer.STEP_MS / 1000
for f in range(n):
    writer.frames[f*200:f*200+48] = composer.w.frames[f*48:(f+1)*48]
    t = f * composer.STEP_MS / 1000
    rms = analysis['rms'][f]
    envelope += (rms - envelope) * (0.4 if rms > envelope else 0.08)
    flash = max(flash * 0.87, 0.65 if f in beats else 0.0)
    # Fire uses red/orange/amber; neon uses blue/cyan/magenta.
    phase = (t / (4 if args.palette == 'fire' else 8)) % 3
    hues = (0.0, 0.045, 0.105, 0.0) if args.palette == 'fire' else (0.54, 0.66, 0.86, 0.54)
    i = int(phase)
    mix = phase - i
    mix = mix * mix * (3 - 2 * mix)
    hue = hues[i] * (1-mix) + hues[i+1] * mix
    fade = max(0.0, min(1.0, (f-start)/60, (end-1-f)/100))
    value = min(0.9, 0.1 + 0.6 * envelope + 0.2 * flash) * fade
    saturation = 0.92 - 0.2 * flash
    rgb = colorsys.hsv_to_rgb(hue, saturation, value)
    for c, v in enumerate(rgb):
        writer.set(f, 176+c, round(v*255))

# Verify preservation and exclusive RGB assignment before writing.
for f in range(n):
    assert writer.frames[f*200:f*200+48] == composer.w.frames[f*48:(f+1)*48]
    assert not any(writer.frames[f*200+48:f*200+175])
    assert not any(writer.frames[f*200+178:(f+1)*200])
assert not any(writer.frames[(n-1)*200+175:(n-1)*200+178])
assert any(writer.frames[f*200+175] for f in range(n))

# Count discrete closure commands per channel against documented budgets.
closures = {}
for channel, limit in [(35,20),(36,20),(37,6),(38,6),(39,6),(40,6),(41,6),(46,3)]:
    values = writer.frames[channel-1::200]
    count = sum(v in (64,128,191) and (i == 0 or v != values[i-1]) for i,v in enumerate(values))
    assert count <= limit, (channel, count, limit)
    closures[channel] = count
with wave.open(str(base.with_suffix('.wav')), 'rb') as audio:
    assert audio.getframerate() == 44100
    audio_duration = audio.getnframes() / audio.getframerate()
assert abs(audio_duration-duration) <= 0.04
output = base.with_suffix('.fseq')
assert not output.exists(), 'Refusing to overwrite an existing show'
writer.save(output)
data = output.read_bytes()
offset = struct.unpack_from('<H', data, 4)[0]
assert data[:4] == b'PSEQ' and data[6:8] == bytes([0,2])
assert struct.unpack_from('<I', data, 10)[0] == 200
assert struct.unpack_from('<I', data, 14)[0] == n
assert data[18] == 20 and data[20] == 0
assert len(data) == offset+n*200 and duration <= 14400
report = dict(frames=n, step_ms=20, duration_s=duration, audio_duration_s=audio_duration,
              tempo_bpm=analysis['tempo_bpm'], channels=200, display_channels=[176,177,178],
              palette=args.palette,
              closure_commands=closures, climax_s=composer.climax_peak*0.02,
              fseq_sha256=hashlib.sha256(data).hexdigest(), vehicle_tested=False)
base.with_suffix('.validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
