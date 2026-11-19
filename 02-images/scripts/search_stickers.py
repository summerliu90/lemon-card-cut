#!/usr/bin/env python3
"""检索本地素材及原生ID候选；只读，不自动选择或宣称渲染可用。"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / 'assets' / 'emotional_image_for_cut'


def search(query, provider, limit):
    words = query.casefold().split()
    results = []
    if provider in ('all', 'local'):
        entries = json.loads((LIB / '_AI检索索引.json').read_text())
        for item in entries:
            rel = item.get('file', '')
            path = (LIB / rel).resolve()
            if not path.is_relative_to(LIB.resolve()) or not path.is_file():
                continue
            if rel.startswith('16_'):
                continue
            hay = json.dumps(item, ensure_ascii=False).casefold()
            primary = (rel + ' ' + item.get('name', '')).casefold()
            if any(w in ('666', '六六六') for w in words) and not any(w in primary for w in ('666', '六六六')):
                continue
            score = sum((5 if word in primary else 1 if word in hay else 0) for word in words)
            if score:
                results.append({'provider': 'local', 'score': score, 'file': str(path),
                                'name': item.get('name'), 'emotion': item.get('emotion'),
                                'scene': item.get('scene'), 'status': 'candidate_needs_view'})
    if provider in ('all', 'jianying'):
        catalog = LIB / '16_剪映原生贴纸_jianying' / '_jianying_sticker_catalog.json'
        data = json.loads(catalog.read_text())
        for item in data['items']:
            intent = item.get('intent', '')
            if not intent or '待标注' in intent:
                continue
            hay = json.dumps(item, ensure_ascii=False).casefold()
            primary = (item.get('name', '') + ' ' + intent).casefold()
            if any(w in ('666', '六六六') for w in words) and not any(w in primary for w in ('666', '六六六')):
                continue
            score = sum((5 if word in primary else 1 if word in hay else 0) for word in words)
            if score:
                preview = item.get('preview', '')
                candidate = ROOT / preview if preview.startswith('assets/') else LIB / preview
                results.append({'provider': 'jianying', 'score': score,
                                'resource_id': item['resource_id'], 'name': item.get('name'),
                                'intent': intent, 'preview': str(candidate) if preview and candidate.is_file() else None,
                                'catalog_verified': bool(item.get('verified_in_jianying')),
                                'status': 'candidate_needs_render_verification'})
    return sorted(results, key=lambda x: -x['score'])[:limit]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('query')
    parser.add_argument('--provider', choices=['all', 'local', 'jianying'], default='all')
    parser.add_argument('--limit', type=int, default=8)
    args = parser.parse_args()
    if not args.query.strip() or args.limit < 1:
        parser.error('query不能为空，limit必须为正数')
    print(json.dumps(search(args.query, args.provider, args.limit), ensure_ascii=False, indent=2))
