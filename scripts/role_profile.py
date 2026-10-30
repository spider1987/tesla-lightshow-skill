"""Shared frequency-role rendering used by CLI and Webstudio."""
import colorsys
import numpy as np

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


def render_roles(a, w, palette='neon', density='balanced', bass_only=True):
    n=a['n_frames']
    bass_gap,bass_floor,mid_gap,high_gap,band_floor,phrase_gap,hold_scale={
        'calm': (24,.35,24,18,.22,45,.85),
        'balanced': (18,.28,16,10,.16,30,1.),
        'intense': (14,.23,12,9,.12,26,1.15),
    }[density]
    rms = np.asarray(a['rms'])
    bass = [f for f in peaks(a['bass'], bass_gap, bass_floor)
            if a['perc_onset'][max(0,f-3):min(n,f+4)] and
            max(a['perc_onset'][max(0,f-3):min(n,f+4)]) > .12]
    mid = peaks(a['mid'], mid_gap, band_floor)
    high = peaks(a['high'], high_gap, band_floor + .04)
    detected = sorted(set(a['onset_frames']) | set(bass))
    # These events drive both exterior choreography and display accents.
    hits = []
    for f in detected:
        if rms[f] >= .06 and (not hits or f-hits[-1] >= 9):
            hits.append(f)

    def pulse(f, group, length):
        if rms[min(f,n-1)] < .025:
            return
        for c in group:
            w.set_range(f,min(n-1,f+max(3,round(length*hold_scale))),c,255)

    # Phrase accents use amber and plate light; main beams are BASS ONLY.
    for i,f in enumerate(hits):
        if not bass_only and i%4 == 0:
            pulse(f,[1,2],8)
        if i % 4 == 0:
            pulse(f,[13,23] if (i//4)%2 == 0 else [14,24],9)
        if i % 8 == 7:
            pulse(f,[30],14)
    for i,f in enumerate(bass):
        pulse(f,[1,2,3,4,25],10)
        if not bass_only and i%4==0:
            pulse(max(0,f-5),[5,6],10)
        if a['bass'][f] > .65 and rms[f] > .55:
            pulse(f,[15,16],15)
        if a['bass'][f] > .8 and rms[f] > .7 and i%4 == 0:
            pulse(f,[28,29],10) # rare reverse/rear-fog emphasis
    for i,f in enumerate(mid):
        pulse(f,[7,8] if (i//8)%2 == 0 else ([7] if i%2 == 0 else [8]),10)
    for i,f in enumerate(high):
        # Aux/marker channels act as one Model-3 group: don't fake a chase.
        pulse(f,[17,21 if i%2 == 0 else 22],7)

    # Sustained harmony drives signature and tail phrases, never the beams.
    harm = np.asarray(a.get('harm_rms', a['mid']))
    phrase = np.convolve(np.pad(harm,(10,10),mode='edge'),np.ones(21)/21,mode='valid')
    for f in range(0,n-1,phrase_gap):
        if rms[f] > .04:
            pulse(f,[26,27],25)
            if phrase[f] > .12 or a['mid'][f] > .15:
                pulse(f,[5,6],23 if rms[f]>.5 else 18)

    event_set=set(bass)
    event_count=0
    flash=0.
    energy=0.
    hue=.0 if palette=='fire' else .55
    hues={'fire':(0.,.035,.085,.015), 'neon':(.54,.67,.84,.61), 'halloween':(.06,.78,.3,.84), 'ice':(.5,.55,.61,.52)}[palette]
    for f in range(n):
        if f in event_set:
            event_count+=1
            flash=1.
        else:
            flash*=.86
        energy+=(float(rms[f])-energy)*.15
        # Harmony chooses palette position; bass controls brightness accents.
        chroma=a.get('chroma')
        pitch=int(np.argmax(chroma[f])) if chroma else event_count//8
        destination=hues[(pitch//3)%len(hues)]
        hue+=(destination-hue)*.08
        fade=max(0.,min(1.,f/40,(n-1-f)/65))
        value=min(.95,.08+.6*energy+.25*flash)*fade if rms[f]>.025 else 0.
        rgb=colorsys.hsv_to_rgb(hue,.97-.25*flash,value)
        for c,v in enumerate(rgb):
            w.set(f,176+c,round(v*255))

    allowed=np.zeros(n,dtype=bool)
    for f in bass:
        if rms[f]>=.025:
            allowed[f:min(n-1,f+max(3,round(10*hold_scale)))]=True
    if bass_only:
        rendered=np.frombuffer(w.frames,np.uint8).reshape(n,w.channel_count)
        assert not rendered[~allowed,:4].any()
    return dict(broad=len(hits),bass=len(bass),mid=len(mid),high=len(high))
