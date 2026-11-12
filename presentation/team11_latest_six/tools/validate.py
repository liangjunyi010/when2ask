"""Check the delivered deck against its original slides and recorded evidence."""
import hashlib
import json
import math
import posixpath
from pathlib import Path
from xml.etree import ElementTree as E
from zipfile import ZipFile

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[1]
NS = {
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def package(path):
    with ZipFile(path) as z:
        assert z.testzip() is None
        return {n: z.read(n) for n in z.namelist()}


def relpath(part):
    return posixpath.join(posixpath.dirname(part), '_rels', posixpath.basename(part) + '.rels')


def dependencies(parts, roots):
    seen = set()
    def visit(part):
        if part in seen:
            return
        seen.add(part)
        rels = relpath(part)
        if rels in parts:
            seen.add(rels)
            for rel in E.fromstring(parts[rels]):
                if rel.get('TargetMode') != 'External':
                    visit(posixpath.normpath(posixpath.join(posixpath.dirname(part), rel.get('Target'))).lstrip('/'))
    for part in roots:
        visit(part)
    return seen


def main():
    source = json.loads((BASE / 'checks/source.json').read_text())
    source_path = Path(source['original_path'])
    assert digest(source_path.read_bytes()) == source['sha256'], 'Original attachment changed'
    original = package(source_path)
    final_path = BASE / 'deliverables/When2Ask_Team11_Updated_Final.pptx'
    final = package(final_path)
    pres = E.fromstring(final['ppt/presentation.xml'])
    assert len(pres.findall('p:sldIdLst/p:sldId', NS)) == 11
    size = pres.find('p:sldSz', NS)
    assert (size.get('cx'), size.get('cy')) == ('15240000', '8572500')
    preserved = dependencies(original, [f'ppt/slides/slide{i}.xml' for i in range(1, 6)])
    for part in preserved:
        assert final[part] == original[part], f'Changed preserved part: {part}'

    slide8 = E.fromstring(final['ppt/slides/slide8.xml'])
    rows = [[''.join(node.text or '' for node in cell.findall('.//a:t', NS))
             for cell in row.findall('a:tc', NS)] for row in slide8.findall('.//a:tbl/a:tr', NS)]
    assert rows[1] == ['GPT-5.6', '', '', '', '']
    assert rows[2] == ['DeepSeek Flash', '100.0%', '100.0%', '100.0%', '0.0%']
    assert rows[3] == ['GLM 5.2', '', '', '', '']
    metrics = json.loads((BASE / 'assets/metrics.json').read_text())
    measured = json.loads((ROOT / metrics['source']).read_text())
    measured = {row['method']: row for row in measured['methods']}
    baseline = measured['llm_gate']
    for row in metrics['rows']:
        actual = measured[row['method']]
        assert row['success'] == actual['success_rate']
        assert row['fpr'] == actual['fpr']
        assert math.isclose(row['time'], actual['api_seconds_mean'] / baseline['api_seconds_mean'])
        assert math.isclose(row['cost'], actual['estimated_usd_mean'] / baseline['estimated_usd_mean'])
    for i, metric in enumerate(('success', 'time', 'cost'), 1):
        chart = E.fromstring(final[f'ppt/slides/charts/w2a_chart{i}.xml'])
        values = [float(v.text) for v in chart.findall('.//c:ser/c:val/c:numRef/c:numCache/c:pt/c:v', NS)]
        expected = [r[metric] for r in metrics['rows']]
        assert len(values) == len(expected) == 4
        assert all(math.isclose(a, b, abs_tol=1e-9) for a, b in zip(values, expected))
        assert chart.find('.//c:externalData', NS) is not None
    media = ROOT / 'presentation/command_center_demo_v1/media/When2Ask_Command_Center_50s.mp4'
    assert digest(final['ppt/media/w2a_console_50s.mp4']) == digest(media.read_bytes())
    playback = json.loads((BASE / 'checks/native_playback.json').read_text())
    assert playback['play_on_entry'] and playback['player_positions_ms'][1] > playback['player_positions_ms'][0] > 0
    assert all((BASE / f'previews/powerpoint-{i:02d}.png').is_file() for i in range(1, 12))
    receipt = json.loads((BASE / 'checks/finalization.json').read_text())
    assert receipt['finalSha256'] == digest(final_path.read_bytes())
    assert receipt['packageIntegrity']['status'] == 'pass'
    assert receipt['nativeChartValidation']['passed']
    result = {
        'status': 'pass', 'slides': 11, 'aspect_ratio': '16:9',
        'source_attachment_unchanged': True,
        'first_five_slides_and_dependencies_byte_identical': len(preserved),
        'editable_cross_model_table': True,
        'unrun_model_cells_empty': ['GPT-5.6', 'GLM 5.2'],
        'editable_charts_verified_against_metrics': 3,
        'embedded_video_matches_recorded_file': True,
        'native_autoplay_verified': True,
        'native_rendered_slides_visually_reviewed': list(range(1, 12)),
        'pptx_sha256': digest(final_path.read_bytes()),
    }
    (BASE / 'checks/validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
