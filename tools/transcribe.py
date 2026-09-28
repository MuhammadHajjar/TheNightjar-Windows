"""Transcribe the game's speech offline with faster-whisper.

    python tools/transcribe.py [model]      -> build/transcripts/<model>.json

Every sound in the bundle that could hold speech is transcribed: everything
under nightjar_sounds/ except footsteps/, the top-level VoiceOver prompts, the
advertisement clip and the audio track of the sponsor video.  Segment start and
end times are kept so triggers can be placed against lines.  A file with no
speech comes back with empty text (or a short whisper hallucination - check by
ear before trusting a one-word result).
"""
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, 'reference', 'Payload', 'The Nightjar.app')
AUDIO = ('.m4a', '.mp3', '.wav', '.m4v')


def wanted():
    out = []
    for dp, dirs, fs in os.walk(os.path.join(APP, 'nightjar_sounds')):
        dirs[:] = [d for d in dirs if d != 'footsteps']
        out += [os.path.join(dp, f) for f in fs if f.lower().endswith(AUDIO)]
    for f in os.listdir(APP):
        if f.lower().endswith(('.m4a', '.m4v')):
            out.append(os.path.join(APP, f))
    out.append(os.path.join(APP, 'advertisement', 'AD_Demo.m4a'))
    return sorted(out)


def main():
    model_name = sys.argv[1] if len(sys.argv) > 1 else 'medium.en'
    from faster_whisper import WhisperModel
    model = WhisperModel(model_name, device='cpu', compute_type='int8')
    files = wanted()
    print(len(files), 'files', flush=True)
    res = {}
    t0 = time.time()
    for i, p in enumerate(files):
        rel = os.path.relpath(p, APP).replace(os.sep, '/')
        try:
            segs, info = model.transcribe(p, language='en', beam_size=5, vad_filter=False)
            segs = [(round(s.start, 2), round(s.end, 2), s.text.strip()) for s in segs]
            res[rel] = {'text': ' '.join(s[2] for s in segs).strip(),
                        'duration': round(info.duration, 2), 'segments': segs}
        except Exception as e:                       # noqa: BLE001
            res[rel] = {'text': '', 'error': repr(e)}
        print(f'{i + 1}/{len(files)} {rel}: {res[rel]["text"][:90]}', flush=True)
    out = os.path.join(ROOT, 'build', 'transcripts', model_name + '.json')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False)
    print('wrote', out, f'{time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
