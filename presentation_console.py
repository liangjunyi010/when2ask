"""Independent English presentation frontend over the unchanged console engine.

This entry point changes display assets and adds read-only evidence routes only.
Original console.py, worker/agent protocols, defaults and frozen files stay intact.
"""
from __future__ import annotations
import json
import mimetypes
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
from when2ask import console_server as original

WEB = ROOT / 'presentation/console_en/web'


def evidence_routes():
    """Explicit allowlist: no filesystem browsing or configuration/secret files."""
    routes = {f'/{name}': WEB / name for name in ['index.html','app.js','style.css','hub.js','hub.css','english.js']}
    study = ROOT / 'outputs/three_task_v8'
    for name in ['summary.json','episodes.csv','methods.csv','disclosure_breakdown.csv','report.md',
                 'paired_outcomes.png','clarification_timing.png','benchmark_summary.png']:
        routes['/evidence/' + name] = study / 'report' / name
    routes['/evidence/frozen_manifest.json'] = study / 'frozen_manifest.json'
    routes['/evidence/gallery.json'] = study / 'gallery.json'
    gallery = json.loads((study / 'gallery.json').read_text())
    for sample in gallery['samples']:
        for media in sample['methods']:
            routes['/evidence/episodes/' + Path(media['episode_path']).parent.name + '.json'] = study / media['episode_path']
            routes['/evidence/videos/' + media['file']] = ROOT / 'presentation/three_task_v8/media' / media['file']
    replay = ROOT / 'presentation/final_benchmark/web'
    routes['/replay/'] = replay / 'index.html'
    routes['/replay/timeline.json'] = replay / 'timeline.json'
    for p in (replay / 'assets').glob('frames-*.webp'):
        routes['/replay/assets/' + p.name] = p
    for name in ['when2ask_highlight.mp4','when2ask_full.mp4','when2ask_highlight.gif']:
        routes['/replay/media/' + name] = ROOT / 'presentation/final_benchmark/media' / name
    return routes


class PresentationHandler(original.Handler):
    def do_GET(self):
        path = unquote(urlsplit(self.path).path)
        if path == '/':
            path = '/index.html'
        routes = evidence_routes()
        if path not in routes:
            return super().do_GET()
        if not self.allowed_host():
            return self.json_response(dict(error='Unrecognized service host'), 403)
        if not self.authorized():
            return self.json_response(dict(error='Controller access token required'), 401)
        file = routes[path]
        if not file.is_file():
            return self.json_response(dict(error='Evidence asset is unavailable'), 404)
        size = file.stat().st_size
        start, end, status = 0, size - 1, 200
        request_range = self.headers.get('Range')
        if request_range:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', request_range)
            if not match or not any(match.groups()):
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.send_header('Content-Length','0')
                self.end_headers()
                return
            left, right = match.groups()
            if left:
                start = int(left)
                end = min(int(right), size - 1) if right else size - 1
            else:
                start = max(0, size - int(right))
            if start > end or start >= size:
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.send_header('Content-Length','0')
                self.end_headers()
                return
            status = 206
        self.send_response(status)
        mime = mimetypes.guess_type(file.name)[0] or 'application/octet-stream'
        self.send_header('Content-Type', mime + ('; charset=utf-8' if mime.startswith('text/') or mime in ('application/json','application/javascript') else ''))
        self.send_header('Content-Length', str(end - start + 1))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-store')
        if status == 206:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        try:
            with file.open('rb') as f:
                f.seek(start)
                remaining = end - start + 1
                while remaining:
                    data = f.read(min(262144, remaining))
                    if not data:
                        break
                    self.wfile.write(data)
                    remaining -= len(data)
        except (BrokenPipeError, ConnectionResetError):
            pass


def main(argv=None):
    original.WEB = WEB
    original.Handler = PresentationHandler
    args = list(sys.argv[1:] if argv is None else argv)
    if '--port' not in args:
        args += ['--port','8902']
    original.main(args)


if __name__ == '__main__':
    main()
