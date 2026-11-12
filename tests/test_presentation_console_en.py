"""Display-only service boundaries; no model backend or physics mocking."""
import importlib.util
import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('presentation_entry',ROOT/'presentation_console.py')
entry=importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)


@pytest.fixture
def service(tmp_path):
    manager=entry.original.TaskManager(tmp_path,allow_live=False,api_limit=0,live_episode_limit=0)
    server=ThreadingHTTPServer(('127.0.0.1',0),entry.PresentationHandler)
    server.manager,server.token=manager,'offline-test-worker-token'
    thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':0.02},daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_port}',manager
    server.shutdown();server.server_close();thread.join(2)


def test_english_display_and_original_default_are_separate(service):
    url,manager=service
    with urlopen(url+'/') as r:
        html=r.read().decode()
    assert 'lang="en"'in html
    assert all(s in html for s in ['Live Demo','Benchmark Results','Recorded Replay','Presentation View'])
    assert 'lang="zh-CN"'in(ROOT/'src/when2ask/console_web/index.html').read_text()
    assert entry.original.WEB!=entry.WEB
    assert manager.metadata()['planner_profiles'][0]['id']=='default_v1'


def test_evidence_routes_deny_secret_and_traversal_paths(service):
    url,_=service
    for path in ['/.env','/evidence/../.env','/evidence/%2e%2e/%2eenv','/replay/../../.env','/worker.token']:
        with pytest.raises(HTTPError) as caught:
            urlopen(url+path)
        assert caught.value.code==404


def test_video_seek_range_returns_actual_embedded_bytes(service):
    url,_=service
    path='/replay/media/when2ask_highlight.mp4'
    original=(ROOT/'presentation/final_benchmark/media/when2ask_highlight.mp4').read_bytes()
    with urlopen(Request(url+path,headers={'Range':'bytes=16-31'}))as r:
        assert r.status==206
        assert r.read()==original[16:32]
        assert r.headers['Content-Range']==f'bytes 16-31/{len(original)}'
    with urlopen(Request(url+path,headers={'Range':'bytes=-12'}))as r:
        assert r.read()==original[-12:]


def test_invalid_media_ranges_are_bounded(service):
    url,_=service
    for value in ['bytes=999999999999-','bytes=8-2','bytes=','bytes=1-3,5-7']:
        with pytest.raises(HTTPError)as caught:
            urlopen(Request(url+'/replay/media/when2ask_highlight.mp4',headers={'Range':value}))
        assert caught.value.code==416
        assert caught.value.headers['Content-Length']=='0'


def test_frozen_results_are_served_byte_identically_without_inference(service):
    url,manager=service
    source=ROOT/'outputs/three_task_v8/report/summary.json'
    with urlopen(url+'/evidence/summary.json')as r:
        assert r.read()==source.read_bytes()
    with urlopen(url+'/api/meta')as r:
        meta=json.load(r)
    assert meta['live_enabled']is False
    assert manager.ledger.snapshot()['attempts']==0
    assert manager.ledger.snapshot()['episodes']==0


def test_read_only_replay_allowlist_resolves_all_manifest_frames(service):
    url,_=service
    routes=entry.evidence_routes()
    with urlopen(url+'/replay/timeline.json')as r:
        timeline=json.load(r)
    for frame in timeline['frames']:
        assert routes['/replay/'+frame['image']['path']].is_file()
    assert timeline['frames'][49]['simulation_step']==timeline['frames'][50]['simulation_step']
    assert [timeline['frames'][i]['stage']for i in (49,50)]==['question','answer']
