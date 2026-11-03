"""Bounded controller service. Local and remote workers use identical HTTP RPC."""
from __future__ import annotations

import argparse
import hmac
import json
import os
import secrets
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .accounting import BackendBlocked, BudgetExceeded
from .config import ROOT
from .console_state import Conflict, TaskManager

WEB = Path(__file__).with_name('console_web')


class ConsoleHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, manager, token):
        self.manager, self.token = manager, token
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *args):
        pass  # Never log authentication headers or uncontrolled request data.

    def allowed_host(self):
        try:
            host = urlsplit('http://' + self.headers.get('Host', '')).hostname
        except ValueError:
            return False
        return host in ('127.0.0.1', 'localhost', '::1', self.server.server_address[0], getattr(self.server, 'advertise_host', None))

    def authorized(self, worker=False):
        supplied = self.headers.get('Authorization', '').removeprefix('Bearer ')
        if hmac.compare_digest(supplied, self.server.token):
            return True
        return not worker and self.client_address[0] in ('127.0.0.1', '::1')

    def json_response(self, value, status=200):
        data = json.dumps(self.server.manager.config.sanitize(value), ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlsplit(self.path).path
        if not self.allowed_host():
            return self.json_response(dict(error='Unrecognized service host'), 403)
        if path in ('/', '/app.js', '/style.css'):
            file = WEB / {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css'}[path]
            data = file.read_bytes()
            mime = {'/': 'text/html; charset=utf-8', '/app.js': 'text/javascript; charset=utf-8', '/style.css': 'text/css; charset=utf-8'}[path]
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            return self.wfile.write(data)
        if not self.authorized():
            return self.json_response(dict(error='Controller access token required'), 401)
        manager = self.server.manager
        if path == '/api/meta':
            data = manager.metadata()
            with manager.lock:
                data['workers'] = [w for w in manager.workers.values() if time.time() - w['last_seen'] < 10]
            return self.json_response(data)
        if path == '/api/tasks':
            with manager.lock:
                return self.json_response(dict(tasks=[t.public() for t in manager.tasks.values()]))
        parts = path.strip('/').split('/')
        if len(parts) == 3 and parts[:2] == ['api', 'tasks']:
            with manager.lock:
                task = manager.tasks.get(parts[2])
                return self.json_response(task.public() if task else dict(error='Task not found'), 200 if task else 404)
        if len(parts) == 4 and parts[:2] == ['api', 'tasks'] and parts[3] == 'episode':
            with manager.lock:
                task = manager.tasks.get(parts[2])
                if task and (task.output / 'episode.json').exists():
                    return self.json_response(json.loads((task.output / 'episode.json').read_text()))
            return self.json_response(dict(error='Episode is not finalized'), 404)
        if path == '/api/events':
            return self.events()
        return self.json_response(dict(error='Not found'), 404)

    def events(self):
        manager = self.server.manager
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'close')
        self.end_headers()
        self.connection.settimeout(15)
        try:
            with manager.lock:
                cursor = manager.sequence
                initial = dict(type='snapshot', tasks=[t.public() for t in manager.tasks.values()])
            self.wfile.write(('id: %d\ndata: %s\n\n' % (cursor, json.dumps(initial))).encode())
            self.wfile.flush()
            while not manager.closed:
                with manager.changed:
                    manager.changed.wait_for(lambda: manager.sequence > cursor or manager.closed, timeout=5)
                    # A slow/reconnected client receives current state, never
                    # replays a robot command or recreates a pending question.
                    if manager.stream and cursor < manager.stream[0]['id'] - 1:
                        rows = [dict(id=manager.sequence, type='snapshot', tasks=[t.public() for t in manager.tasks.values()])]
                    else:
                        rows = [r for r in manager.stream if r['id'] > cursor]
                if not rows:
                    self.wfile.write(b': keepalive\n\n')
                for row in rows:
                    cursor = row['id']
                    self.wfile.write(('id: %d\ndata: %s\n\n' % (cursor, json.dumps(row))).encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, TimeoutError, OSError):
            pass
        self.close_connection = True

    def do_POST(self):
        path = urlsplit(self.path).path
        if not self.allowed_host():
            return self.json_response(dict(error='Unrecognized service host'), 403)
        origin = self.headers.get('Origin')
        if origin and urlsplit(origin).netloc != self.headers.get('Host'):
            return self.json_response(dict(error='Cross-origin control requests are not allowed'), 403)
        worker = path.startswith('/api/worker/')
        if not self.authorized(worker):
            return self.json_response(dict(error='Execution worker token required' if worker else 'Controller access token required'), 401)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 2_000_000:
                raise ValueError('Invalid request length')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('JSON object required')
            manager = self.server.manager
            if path == '/api/tasks':
                result = manager.create(data['options'], data['request_id'])
                return self.json_response(result, 201)
            parts = path.strip('/').split('/')
            if len(parts) == 4 and parts[:2] == ['api', 'tasks']:
                if parts[3] == 'answer':
                    return self.json_response(manager.answer(parts[2], data['question_id'], data.get('response'), source=data.get('source', 'human')))
                if parts[3] == 'cancel':
                    return self.json_response(manager.cancel_task(parts[2]))
                if parts[3] == 'inspect':
                    with manager.changed:
                        task = manager.tasks[parts[2]]
                        if task.status != 'waiting_answer':
                            raise Conflict('An idle ASK task is required for a physics inspection')
                        command_id = manager.command(task, 'inspect')
                    manager.wait(task, lambda: command_id in task.inspections, timeout=15)
                    return self.json_response(task.inspections[command_id])
            if path == '/api/worker/claim':
                return self.json_response(dict(job=manager.claim(data['worker_id'], int(data.get('capacity', 1)))))
            if path == '/api/worker/heartbeat':
                with manager.lock:
                    ident, capacity = data['worker_id'], int(data['capacity'])
                    if not isinstance(ident, str) or not 1 <= len(ident) <= 100 or not 1 <= capacity <= 8:
                        raise ValueError('Invalid worker heartbeat')
                    manager.workers[ident] = dict(id=ident, capacity=capacity, last_seen=time.time())
                return self.json_response(dict(accepted=True))
            if path == '/api/worker/event':
                return self.json_response(manager.worker_event(data))
            if path == '/api/worker/commands':
                return self.json_response(manager.poll_commands(data['task_id'], data['worker_id'], int(data['after'])))
            if path == '/api/worker/exited':
                with manager.changed:
                    task = manager.owned(data['task_id'], data['worker_id'])
                    if task.finalization is None:
                        task.error = 'Execution process exited before returning final physical evidence'
                        manager.publish(task)
                return self.json_response(dict(accepted=True))
            return self.json_response(dict(error='Not found'), 404)
        except (Conflict, BudgetExceeded, BackendBlocked) as exc:
            self.json_response(dict(error=str(exc)), 409)
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            self.json_response(dict(error=f'Invalid request: {exc}'), 400)
        except Exception as exc:
            self.json_response(dict(error=f'Controller error: {type(exc).__name__}'), 500)


def main(argv=None):
    parser = argparse.ArgumentParser(description='When2Ask local/VPN task console')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8877)
    parser.add_argument('--advertise-host', help='Allowed VPN address/hostname when binding 0.0.0.0')
    parser.add_argument('--output-dir')
    parser.add_argument('--live', action='store_true', help='Allow explicit live-model task launches')
    parser.add_argument('--capacity', type=int, default=3)
    parser.add_argument('--api-limit', type=int, default=60)
    parser.add_argument('--live-episode-limit', type=int, default=6)
    parser.add_argument('--no-local-worker', action='store_true')
    args = parser.parse_args(argv)
    if not 1 <= args.capacity <= 8 or not 0 <= args.api_limit <= 200 or not 0 <= args.live_episode_limit <= 12:
        parser.error('Invalid concurrency or inference budget')
    output = Path(args.output_dir or ROOT / 'outputs/local_console' / ('session-' + uuid.uuid4().hex[:12])).resolve()
    manager = TaskManager(output, allow_live=args.live, capacity=args.capacity, api_limit=args.api_limit,
                          live_episode_limit=args.live_episode_limit)
    token_file = output / 'worker.token'
    if token_file.exists():
        token = token_file.read_text().strip()
    else:
        token = secrets.token_hex(32)
        fd = os.open(token_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as handle:
            handle.write(token)
    server = ConsoleHTTPServer((args.host, args.port), manager, token)
    server.advertise_host = args.advertise_host
    local = None
    if not args.no_local_worker:
        url_host = '127.0.0.1' if args.host == '0.0.0.0' else args.host
        environment = {k: v for k, v in os.environ.items() if k not in ('DEEPSEEK_API_KEY', 'TYPESAFE_API_KEY')}
        local = subprocess.Popen([sys.executable, str(ROOT / 'console.py'), 'worker', '--server', f'http://{url_host}:{server.server_port}',
                                  '--token-file', str(token_file), '--capacity', str(args.capacity)], cwd=ROOT, env=environment)
    print(json.dumps(dict(url=f'http://{args.host}:{server.server_port}/', output_dir=str(output), live_enabled=args.live,
                          concurrency=args.capacity, api_limit=args.api_limit, live_episode_limit=args.live_episode_limit)), flush=True)
    try:
        server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:
        pass
    finally:
        with manager.changed:
            manager.closed = True
            for task in manager.tasks.values():
                if task.status not in ('done', 'error', 'cancelled'):
                    task.cancel = True
            manager.changed.notify_all()
        if local:
            local.terminate()
            try:
                local.wait(timeout=8)
            except subprocess.TimeoutExpired:
                local.kill()
        server.server_close()
