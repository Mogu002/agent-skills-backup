#!/usr/bin/env python3
"""Local request/export helper. Browser execution is performed by the Agent Skill."""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, parse_qs


def normalize(value):
    urls = re.findall(r'https?://[^\s<>"\u3002\uff0c]+', value)
    if len(urls) != 1:
        raise ValueError('Provide exactly one Douyin URL (share text is accepted).')
    url = urls[0].rstrip('.,;!?)）】')
    p = urlparse(url)
    if p.scheme != 'https' or p.username or p.password or p.port:
        raise ValueError('Only ordinary HTTPS Douyin links are supported.')
    if p.hostname not in {'www.douyin.com', 'douyin.com', 'v.douyin.com', 'www.iesdouyin.com', 'iesdouyin.com'}:
        raise ValueError('Unsupported host.')
    q = parse_qs(p.query)
    ids = re.findall(r'/(?:share/)?video/(\d+)(?:/|$)', p.path)
    ids += q.get('modal_id', []) + q.get('vid', []) + q.get('item_id', [])
    if any(not re.fullmatch(r'\d{15,22}', x) for x in ids) or len(set(ids)) > 1:
        raise ValueError('Invalid or conflicting video IDs.')
    video_id = ids[0] if ids else None
    if not video_id and not (p.hostname == 'v.douyin.com' and p.path.strip('/')):
        raise ValueError('A video URL or Douyin short link is required, not a profile URL.')
    canonical = f'https://www.douyin.com/video/{video_id}' if video_id else url
    return {'input_url': url, 'source_url': canonical, 'video_id': video_id}


def make_request(value):
    result = normalize(value)
    result['prompt'] = (result['source_url'] + '\n给我这个视频的文字稿。'
        '请保留实际口播原话，不总结、不润色、不补写。'
        '用 <transcript> 和 </transcript> 包住口播正文；'
        '来源和完整性无法确定就写未知。没有取得口播文本则明确说明，不要编造。')
    return result


def parse_capture(capture):
    request = capture.get('request', {})
    raw = capture.get('raw_response', '')
    if not isinstance(raw, str):
        raise ValueError('raw_response must be a string')
    result = {
        'schema_version': 1, 'provider': 'doubao-web',
        'source_url': request.get('source_url'), 'video_id': request.get('video_id'),
        'conversation_url': capture.get('conversation_url'),
        'captured_at': capture.get('captured_at'),
        'elapsed_upper_bound_seconds': capture.get('elapsed_upper_bound_seconds'),
        'status': 'needs_review', 'completeness': 'unknown',
        'audio_verified': False, 'transcript': None,
        'raw_response': raw, 'sources': capture.get('sources', []),
        'warnings': [],
    }
    if not capture.get('complete') or not capture.get('prompt_matches'):
        result['status'] = 'incomplete_capture'
        result['warnings'].append('No verified completion or matching submitted prompt.')
        return result
    if not raw.strip():
        result['status'] = 'empty'
        return result
    if re.search(r'<unavailable\b', raw, re.I):
        result['status'] = 'unavailable'
        return result
    matches = re.findall(r'<transcript\s*>(.*?)</transcript\s*>', raw, re.S | re.I)
    if len(matches) != 1:
        result['warnings'].append('Missing or ambiguous transcript delimiters; raw response preserved.')
        return result
    candidate = matches[0].strip()
    if not candidate:
        result['status'] = 'empty'
        return result
    if re.search(r'无法.{0,25}(获取|提取|访问)|未能.{0,20}(获取|提取)|没有.{0,20}(口播|文本)', candidate):
        result['status'] = 'unavailable'
        return result
    result['transcript'] = candidate
    result['status'] = 'extracted_unverified'
    result['warnings'].append('Model-mediated text; exactness and completeness have not been checked against audio.')
    if re.search(r'复原|重构|概括|改写|补全|片段|部分摘要|缺段', raw):
        result['status'] = 'needs_review'
        result['warnings'].append('Response contains a reconstruction, summary, partial-content or missing-segment cue.')
    result['content_sha256'] = hashlib.sha256(candidate.encode()).hexdigest()
    return result


def export(capture, out):
    result = parse_capture(capture)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    (out / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    (out / 'raw-response.txt').write_text(result['raw_response'] + '\n')
    text = result['transcript']
    if text is not None:
        (out / 'transcript.txt').write_text(text + '\n')
    front = {
        'source': result['source_url'], 'provider': result['provider'],
        'status': result['status'], 'completeness': 'unknown',
        'audio_verified': False, 'conversation': result['conversation_url'],
        'captured_at': result['captured_at']}
    fm = '\n'.join(f'{k}: {json.dumps(v, ensure_ascii=False)}' for k, v in front.items())
    md = f'---\n{fm}\n---\n\n# 抖音口播候选稿\n\n'
    md += '> 豆包返回的候选文本，尚未与视频音频核对；不得视为已验证逐字稿。\n\n'
    md += (text if text is not None else '未获得可提取的口播文本，详见 raw-response.txt。') + '\n'
    (out / 'source.md').write_text(md)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    p = sub.add_parser('request', help='Normalize URL and generate prompt; does not call Doubao')
    p.add_argument('url')
    p = sub.add_parser('export', help='Export an Agent-captured response to wiki intake files')
    p.add_argument('capture', type=Path)
    p.add_argument('--out', required=True, type=Path)
    args = ap.parse_args()
    try:
        if args.command == 'request':
            print(json.dumps(make_request(args.url), ensure_ascii=False, indent=2))
        else:
            result = export(json.loads(args.capture.read_text()), args.out)
            print(json.dumps({'status': result['status'], 'output_dir': str(args.out.resolve()),
                'characters': len(result['transcript'] or '')}, ensure_ascii=False))
    except (ValueError, OSError, KeyError) as exc:
        ap.exit(2, f'{exc}\n')


if __name__ == '__main__':
    main()
