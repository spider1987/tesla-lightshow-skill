"""Music-driven Model 3 exterior/display profile; preserve source closures."""
import argparse
import colorsys
import hashlib
import json
import shutil
import struct
from pathlib import Path

import numpy as np
from fseq_writer import FseqWriter
from compose_show import Composer
from role_profile import render_roles


def peaks(values, gap, floor):
    """Local band transients against a 2-second moving background."""
    x = np.asarray(values, dtype=float)
    background = np.convolve(np.pad(x, (50, 50), mode='edge'), np.ones(101)/101, mode='valid')
    threshold = np.maximum(floor, background * 1.05)
    candidates = [f for f in range(1, len(x)-1)
                  if x[f] >= threshold[f] and x[f] >= x[f-1] and x[f] > x[f+1]]
    # Strongest transient wins within the refractory interval.
    selected = []
    for f in sorted(candidates, key=lambda f: x[f]-background[f], reverse=True):
        if all(abs(f-p) >= gap for p in selected):
            selected.append(f)
    return sorted(selected)


def metrics(data, channels, offset, n):
    frames = np.frombuffer(data, np.uint8, count=n*channels, offset=offset).reshape(n, channels)
    active = frames[:, :30] >= 128
    # Model 3 groups channel 4/5/6 and aux/marker outputs together.
    groups = [[0],[1],[2],[3],[4],[5],[6,8,10],[7,9,11],[12],[13],
              [14],[15],[16,17,18,19],[20],[21],[22],[23],[24],[25],[26],[27],[28],[29]]
    logical = np.array([active[:, g].any(axis=1) for g in groups]).T
    dark = ~logical.any(axis=1)
    longest = run = 0
    for v in dark:
        run = run + 1 if v else 0
        longest = max(longest, run)
    return dict(dark_pct=round(float(dark.mean()*100),2),
                front_on_pct=round(float(active[:,:16].any(axis=1).mean()*100),2),
                mean_active_groups=round(float(logical.sum(axis=1).mean()),2),
                longest_dark_s=round(longest*.02,2))


def create(song, palette):
    root = Path(__file__).resolve().parent.parent
    base = root / 'archive' / 'show-sources' / song
    if not base.with_suffix('.analysis.json').exists():
        base = root / 'LightShow' / song
    target = root / 'LightShow' / (song + '-v3')
    report_path = root / 'archive' / 'validation' / (song + '-v3.validation.json')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    a = json.loads(base.with_suffix('.analysis.json').read_text())
    if not base.with_suffix('.fseq').exists():
        composition_analysis = dict(a, music_start=0, music_end=a['n_frames'], segments=[])
        composer = Composer(composition_analysis, 'model_3')
        composer.compose()
        composer.w.save(base.with_suffix('.fseq'))
    source = base.with_suffix('.fseq').read_bytes()
    offset = struct.unpack_from('<H',source,4)[0]
    channels,n = struct.unpack_from('<II',source,10)
    assert source[:4] == b'PSEQ' and source[7] == 2 and source[20:24] == bytes(4)
    assert source[18] == 20 and n == a['n_frames'] and len(source) == offset+n*channels
    w = FseqWriter(200,n,20)
    for f in range(n):
        w.frames[f*200+30:f*200+48] = source[offset+f*channels+30:offset+f*channels+48]
    events = render_roles(a, w, palette)
    rms = np.asarray(a['rms'])
    bass = [f for f in peaks(a['bass'], 18, .28) if max(a['perc_onset'][max(0,f-3):min(n,f+4)]) > .12]

    output=target.with_suffix('.fseq')
    if output.exists():
        previous=json.loads(report_path.read_text())
        assert hashlib.sha256(output.read_bytes()).hexdigest()==previous['fseq_sha256'], 'Output was changed externally'
    # All source motion commands must remain byte-identical.
    for f in range(n):
        assert w.frames[f*200+30:f*200+48] == source[offset+f*channels+30:offset+f*channels+48]
        assert not any(w.frames[f*200+48:f*200+175])
        assert not any(w.frames[f*200+178:(f+1)*200])
    assert not any(w.frames[(n-1)*200:(n-1)*200+30])
    assert not any(w.frames[(n-1)*200+175:(n-1)*200+178])
    # Prove no non-bass layer can operate any of the four main beams.
    allowed=np.zeros(n,dtype=bool)
    for f in bass:
        if rms[f]>=.025:
            allowed[f:min(n-1,f+10)]=True
    rendered=np.frombuffer(w.frames,np.uint8).reshape(n,200)
    assert not rendered[~allowed,:4].any()
    for channel,limit in [(35,20),(36,20),(37,6),(38,6),(39,6),(40,6),(41,6),(46,3)]:
        values=rendered[:,channel-1]
        commands=sum(int(v) in (64,128,191) and (i==0 or v!=values[i-1]) for i,v in enumerate(values))
        assert commands<=limit,(channel,commands,limit)
    w.save(output)
    result=output.read_bytes()
    data_offset=struct.unpack_from('<H',result,4)[0]
    assert len(result)==data_offset+n*200 and result[20:24]==bytes(4)
    assert result[6:8]==bytes([0,2]) and n*.02<=14400
    before=metrics(source,channels,offset,n)
    after=metrics(result,200,data_offset,n)
    assert after['dark_pct'] < before['dark_pct']*.6
    assert after['front_on_pct'] > before['front_on_pct']+25
    mp3=root/'LightShow'/(song+'.mp3')
    archived_mp3=base.with_suffix('.mp3')
    audio=mp3 if mp3.exists() else archived_mp3 if archived_mp3.exists() else base.with_suffix('.wav')
    audio_target=target.with_suffix(audio.suffix)
    shutil.copyfile(audio,audio_target)
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    assert digest(audio) == digest(audio_target)
    report=dict(song=song,duration_s=n*.02,before=before,after=after,
                events=events,
                profile='frequency-roles-v3',main_beams_bass_only=True,
                closures_preserved=True,audio_identical=True,vehicle_tested=False,
                fseq_sha256=digest(output))
    report_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2,ensure_ascii=True))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--song',required=True)
    parser.add_argument('--palette',choices=['fire','neon'],required=True)
    args=parser.parse_args()
    create(args.song,args.palette)
