"""Shared integer output-frame contract (no ffmpeg side effects on import)."""
from fractions import Fraction
import json
import subprocess


def fps_value(value=24):
    fps = Fraction(str(value))
    if fps <= 0:
        raise ValueError('fps must be positive')
    return fps


def frame_count(duration, fps=24):
    count = Fraction(str(duration)) * fps_value(fps)
    if count <= 0:
        raise ValueError('duration must be positive')
    return (count.numerator + count.denominator - 1) // count.denominator


def decoded_frames(path, fps=24, source_start=0):
    """Count frames after the same fps conversion used by the renderer."""
    command = ['ffmpeg', '-v', 'error', '-ss', str(source_start), '-i', str(path),
               '-map', '0:v:0', '-vf', f'fps={fps}', '-an', '-f', 'null', '-',
               '-progress', 'pipe:1', '-nostats']
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    frames = [int(line.split('=', 1)[1]) for line in result.stdout.splitlines() if line.startswith('frame=')]
    return max(frames, default=0)


def verify_backgrounds(plan, base, fps):
    if fps_value(plan.get('fps', 24)) != fps_value(fps):
        raise ValueError('output fps conflicts with plan; recompile background at requested fps')
    reports = []
    for clip in plan['clips']:
        if clip.get('track') != 'background' or clip.get('kind') != 'video':
            continue
        # Timeline sample instants n/fps in [start,end).
        start = Fraction(str(clip['start_s'])) * fps_value(fps)
        end = Fraction(str(clip['end_s'])) * fps_value(fps)
        ceil = lambda x: (x.numerator + x.denominator - 1) // x.denominator
        required = ceil(end) - ceil(start)
        actual = decoded_frames(base / clip['file'], fps, clip.get('source_start_s', 0))
        if actual < required:
            raise ValueError(f"background {clip['id']}: decoded {actual}, required {required} frames")
        reports.append({'clip_id': clip['id'], 'required_frames': required, 'decoded_frames': actual, 'fps': str(fps)})
    return reports
