"""Select from agent-filtered compatible style IDs, reproducibly; no network."""
import argparse
import hashlib
import json
from pathlib import Path

ALGORITHM = 'sha256-sorted-candidates-v1'
CATALOG = Path(__file__).resolve().parents[1] / 'references/image-style-catalog.json'


def choose(seed, candidates):
    candidates = sorted(set(candidates))
    if not candidates or isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError('integer seed and nonempty candidate IDs required')
    payload = json.dumps([ALGORITHM, seed, candidates], ensure_ascii=False, separators=(',', ':'))
    return candidates[int(hashlib.sha256(payload.encode()).hexdigest(), 16) % len(candidates)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--candidates', nargs='+', required=True)
    args = parser.parse_args()
    known = {item['id'] for item in json.loads(CATALOG.read_text())['styles']}
    if not set(args.candidates) <= known:
        parser.error('unknown style IDs: ' + str(set(args.candidates) - known))
    print(json.dumps({'selection_mode': 'semantic_random', 'seed': args.seed,
                     'selection_algorithm': ALGORITHM, 'candidates': sorted(set(args.candidates)),
                     'visual_style_id': choose(args.seed, args.candidates)}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
