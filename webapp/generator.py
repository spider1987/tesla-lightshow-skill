"""Audio conversion, shared choreography and two-file package generation."""
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import wave
import zipfile

import numpy as np

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from analyze_audio import analyze, load_wav_stereo
from compose_show import Composer
from fseq_writer import FseqWriter
from role_profile import render_roles

MODELS = {'model_3': 'Model 3 · vor 2024', 'model_3_highland': 'Model 3 Highland',
          'model_y': 'Model Y', 'model_s': 'Model S', 'model_x': 'Model X', 'cybertruck': 'Cybertruck'}


def ffmpeg():
    configured = os.getenv('FFMPEG_PATH')
    if configured:
        return configured
    found = shutil.which('ffmpeg')
    if found:
        return found
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def convert(args):
    result = subprocess.run([ffmpeg(), '-nostdin', '-hide_banner', '-loglevel', 'error', '-y', *args],
                            stdin=subprocess.DEVNULL, capture_output=True, timeout=180,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise ValueError('Die MP3 konnte nicht gelesen oder umgewandelt werden.')


def validate_sequence(path, max_duration):
    data = path.read_bytes()
    if len(data) < 32:
        raise ValueError('Sequenzdatei ist unvollständig.')
    offset = struct.unpack_from('<H', data, 4)[0]
    channels, frames = struct.unpack_from('<II', data, 10)
    if not (data[:4] == b'PSEQ' and data[6:8] == bytes([0, 2]) and offset >= 32
            and channels in (48, 200) and frames > 0 and data[18] == 20
            and data[20:24] == bytes(4) and len(data) == offset + channels*frames
            and frames*.02 <= min(14400, max_duration + .1)):
        raise ValueError('Die Sequenz hat die Formatprüfung nicht bestanden.')
    arr = np.frombuffer(data, np.uint8, offset=offset).reshape(frames, channels)
    budgets = {31:6,32:6,33:6,34:6,35:20,36:20,37:6,38:6,39:6,40:6,41:6,
               42:20,43:20,44:20,45:20,46:3}
    for channel, limit in budgets.items():
        values = arr[:, channel-1]
        transitions = np.concatenate(([True], values[1:] != values[:-1]))
        if int((np.isin(values, [64,128,191]) & transitions).sum()) > limit:
            raise ValueError('Das Bewegungsbudget wurde überschritten.')
    return arr


def schedule_liftgate(writer):
    """One opening at show start; allow four seconds to close before the end."""
    if writer.frame_count * .02 < 19:
        raise ValueError('Mit Heckklappenbewegung muss die Show mindestens 19 Sekunden lang sein.')
    arr=np.frombuffer(writer.frames,np.uint8).reshape(writer.frame_count,writer.channel_count)
    arr[:,40]=0
    writer.set_range(0,15,41,64)
    close_frame=writer.frame_count-200
    writer.set_range(close_frame,close_frame+15,41,191)


def shift_lights(writer, milliseconds):
    """Positive offset delays lights/display only, within unchanged show duration."""
    shift=round(milliseconds/20)
    if not shift:
        return
    arr=np.frombuffer(writer.frames,np.uint8).reshape(writer.frame_count,writer.channel_count)
    channels=list(range(30))+list(range(46,174))+list(range(175,193))
    source=arr[:,channels].copy()
    arr[:,channels]=0
    if abs(shift)<writer.frame_count:
        if shift>0:
            arr[shift:,channels]=source[:-shift]
        else:
            arr[:shift,channels]=source[-shift:]


def compose_analysis(analysis, options):
    a = dict(analysis, music_start=0, music_end=analysis['n_frames'], segments=[])
    # Cybertruck has different rear/front mappings; retain its dedicated composer.
    if options['model'] == 'cybertruck' and options['density'] == 'calm':
        a['beat_frames'] = a['beat_frames'][::2]
    composer = Composer(a, options['model'])
    composer.compose()
    w = FseqWriter(200, composer.n, 20)
    if options['model'] == 'cybertruck':
        w.frames[:] = composer.w.frames
        if options['density'] == 'intense':
            for f in a.get('onset_frames', []):
                if a['rms'][f] > .6:
                    for ch in (1,2,3,4):
                        w.set_range(f, f+8, ch, 255)
        if options['bass_only']:
            from role_profile import peaks
            mask = np.zeros(composer.n, bool)
            for f in peaks(a['bass'], 18, .28):
                mask[f:min(composer.n-1,f+10)] = True
            values = np.frombuffer(w.frames, np.uint8).reshape(composer.n, 200)
            values[~mask,:4] = 0
    else:
        for f in range(composer.n):
            w.frames[f*200+30:f*200+46] = composer.w.frames[f*composer.channels+30:f*composer.channels+46]
        render_roles(a, w, options['palette'], options['density'], options['bass_only'])
    # Screen/accents on the CT also follow the selected palette and density.
    if options['model'] == 'cybertruck':
        rgb = FseqWriter(200, composer.n,20)
        render_roles(a,rgb,options['palette'],options['density'],True)
        for f in range(composer.n):
            w.frames[f*200+175:f*200+178] = rgb.frames[f*200+175:f*200+178]
    arr = np.frombuffer(w.frames,np.uint8).reshape(composer.n,200)
    arr[:,178:193] = 0
    if options['model'] in ('model_3_highland','cybertruck') and options['accents']:
        for base in (178,181,184,187,190):
            arr[:,base:base+3] = arr[:,175:178]
    if not options['display']:
        arr[:,175:178] = 0
    enabled = set()
    if options['mirrors']: enabled.update((35,36))
    if options['liftgate']: enabled.add(41)
    if options['charge_port']: enabled.add(46)
    # Windows and doors have no UI controls and therefore remain disabled.
    for ch in range(31,47):
        if ch not in enabled:
            arr[:,ch-1] = 0
    if options['liftgate'] and options.get('liftgate_mode','start_end')=='start_end':
        schedule_liftgate(w)
    shift_lights(w,options.get('light_offset_ms',0))
    arr[-1,:30] = 0
    arr[-1,46:] = 0
    return w


def preview_data(arr, duration):
    groups = [('bass','Bass · Hauptscheinwerfer',[0,1,2,3]),
              ('melody','Melodie · Signatur',[4,5]), ('mid','Mitten · Segmente',[6,7,8,9,10,11]),
              ('fog','Bass · Nebel vorne',[14,15]), ('high','Höhen · Seitenlichter',[16,17,18,19,20,21]),
              ('turn','Akzente · Blinker',[12,13,22,23]), ('tail','Begleitung · Rücklichter',[25,26]),
              ('brake','Bass · Bremslicht',[24]), ('accent','Heckakzente',[27,28,29]),
              ('motion','Bewegungen',list(range(30,46)))]
    if arr.shape[1] == 200 and np.any(arr[:,46:175]):
        groups.append(('bar','Cybertruck · Lichtleisten',list(range(46,175))))
    stride = max(1, math.ceil(len(arr)/1800))
    tracks=[]
    for key,label,channels in groups:
        values=(arr[:,channels].max(axis=1) >= (1 if key=='motion' else 128)).astype(np.uint8)
        values=[int(values[i:i+stride].max()) for i in range(0,len(values),stride)]
        tracks.append(dict(key=key,label=label,values=values))
    colors = [arr[i:i+stride,175:178].max(axis=0).tolist() for i in range(0,len(arr),stride)]
    return dict(duration=duration,step=stride*.02,tracks=tracks,colors=colors,
                front_active_pct=round(float((arr[:,:16]>=128).any(axis=1).mean()*100),1))


def generate(directory, metadata, progress):
    directory=Path(directory)
    options=metadata['options']
    limit=float(metadata['max_duration'])
    # Reject overlong inputs by decoding at most limit+1 seconds.
    progress(12,'MP3 prüfen und auf 44,1 kHz vorbereiten')
    wav=directory/'analysis.wav'
    convert(['-f','mp3','-protocol_whitelist','file,pipe','-i',str(directory/'input.mp3'),'-t',str(limit+1),'-vn','-map','0:a:0',
             '-ac','2','-ar','44100','-c:a','pcm_s16le',str(wav)])
    with wave.open(str(wav),'rb') as audio:
        duration=audio.getnframes()/audio.getframerate()
    if duration<2 or duration>limit:
        raise ValueError(f'Die Musik muss zwischen 2 und {int(limit)} Sekunden lang sein.')
    mp3=directory/'playback.mp3'
    convert(['-i',str(wav),'-map_metadata','-1','-c:a','libmp3lame','-b:a','320k','-ar','44100',str(mp3)])
    # Analyze the actual playback encode, including encoder delay/padding handling.
    convert(['-i',str(mp3),'-ac','2','-ar','44100','-c:a','pcm_s16le',str(wav)])
    progress(30,'Bass, Mitten, Höhen und musikalische Anschläge analysieren')
    left,right,rate=load_wav_stereo(wav)
    analysis=analyze(left,right,rate)
    progress(70,'Lichtgruppen und Display choreografieren')
    writer=compose_analysis(analysis,options)
    fseq=directory/'sequence.fseq'
    writer.save(fseq)
    progress(90,'Sequenz prüfen und ZIP zusammenstellen')
    arr=validate_sequence(fseq,limit)
    actual=writer.frame_count*.02
    if abs(actual-len(left)/rate)>.04:
        raise ValueError('Musik- und Sequenzlänge passen nicht zusammen.')
    preview=preview_data(arr,actual)
    preview['model']=MODELS[options['model']]
    preview['bass_only']=options['bass_only']
    (directory/'preview.json').write_text(json.dumps(preview),encoding='utf-8')
    stem=metadata['stem']
    with zipfile.ZipFile(directory/'show.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(mp3,stem+'.mp3')
        archive.write(fseq,stem+'.fseq')
    with zipfile.ZipFile(directory/'show.zip') as archive:
        if sorted(archive.namelist()) != sorted([stem+'.mp3',stem+'.fseq']) or archive.testzip():
            raise ValueError('ZIP-Prüfung fehlgeschlagen.')
    for name in ('input.mp3','analysis.wav','sequence.fseq'):
        (directory/name).unlink(missing_ok=True)
    progress(100,'Fertig – ZIP und Vorschau sind bereit')
