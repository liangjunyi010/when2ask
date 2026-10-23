"""Validate deck media, editable data, and factual claims against preserved logs."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from PIL import Image

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[1]
NS = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main"}


def main() -> None:
    deck = BASE / "When2Ask_Milestone_Presentation.pptx"
    with ZipFile(deck) as z:
        assert z.testzip() is None
        p = ET.fromstring(z.read("ppt/presentation.xml"))
        size = p.find("p:sldSz", NS)
        assert (int(size.get("cx")), int(size.get("cy"))) == (18288000, 10287000)
        assert len(p.findall("p:sldIdLst/p:sldId", NS)) == 2
        slide1 = ET.fromstring(z.read("ppt/slides/slide1.xml"))
        slide2 = ET.fromstring(z.read("ppt/slides/slide2.xml"))
        assert len(slide1.findall(".//p:pic", NS)) == 2
        assert len(slide1.findall(".//a:videoFile", NS)) == 1
        assert len(slide1.findall(".//p:video/p:cMediaNode", NS)) == 1
        assert slide1.find(".//p:video/p:cMediaNode/p:cTn/p:stCondLst/p:cond", NS).get("delay") == "0"
        for ext in ("gif", "mp4"):
            embedded = z.read(f"ppt/media/when2ask-replay.{ext}")
            standalone = (BASE / f"media/when2ask_milestone_highlight.{ext}").read_bytes()
            assert embedded == standalone
        gif = Image.open(io.BytesIO(z.read("ppt/media/when2ask-replay.gif")))
        assert gif.n_frames == 287 and gif.size == (1280, 720)
        table = slide2.find(".//a:tbl", NS)
        assert table is not None
        rows = [["".join(c.itertext()) for c in r.findall("a:tc", NS)] for r in table.findall("a:tr", NS)]
        assert rows[0] == ["Method", "Success", "Avg. burden", "API latency"]
        totals = []
        for label, condition in [("LLM-NoAsk", "llm_noask"), ("LLM-Gate", "llm_gate"), ("Jev-Gate (0.5)", "jev_gate_t0p5")]:
            paths = sorted((ROOT / "outputs/phase3_live/dev").glob(f"*__{condition}/episode.json"))
            assert len(paths) == 8
            episodes = [json.loads(f.read_text()) for f in paths]
            assert len({e["group_id"] for e in episodes}) == 8
            assert all(e["evidence_kind"] == "live_model_and_physics" for e in episodes)
            successes = sum(e["evaluation"]["task_success"] for e in episodes)
            burden = sum(e["evaluation"]["clarification_burden"] for e in episodes) / 8
            latency_s = sum(e["cost"]["api_latency_ms"] for e in episodes) / 1000
            expected = [label, f"{successes}/8", f"{burden:.3f}", f"{latency_s:.2f} s"]
            assert rows[len(totals) + 1] == expected, (rows, expected)
            totals.append({"condition": condition, "success": successes, "episodes": 8,
                           "average_burden": burden, "cumulative_api_latency_s": latency_s,
                           "source_files": [str(f.relative_to(ROOT)) for f in paths]})
        notes = [ET.fromstring(z.read(f"ppt/notesSlides/notesSlide{i}.xml")) for i in (1, 2)]
        assert all(len("".join(n.itertext()).split()) > 100 for n in notes)
        all_text = " ".join(slide2.itertext())
        for claim in ["32 Dev / 128 held-out Test samples", "160/160 physical oracle validation",
                      "96 automated tests passed", "Formal Test has not run."]:
            assert claim in all_text
    audit = json.loads((ROOT / "outputs/phase3/data_validation.json").read_text())
    assert audit["grouping"]["distribution"]["dev"]["samples"] == 32
    assert audit["grouping"]["distribution"]["test"]["samples"] == 128
    oracles = [json.loads(p.read_text()) for partition in ("dev", "test")
               for p in sorted((ROOT / "outputs/phase3/oracle" / partition).glob("v3_*.json"))]
    assert len(oracles) == 160 and all(o["evaluation"]["task_success"] for o in oracles)
    baseline_tests = ET.parse(ROOT / "outputs/phase3/pytest_final.xml").getroot().find("testsuite")
    assert baseline_tests.get("tests") == "96" and baseline_tests.get("failures") == "0"
    new_tests = ET.parse(BASE / "pytest.xml").getroot().find("testsuite")
    assert new_tests.get("tests") == "102" and new_tests.get("failures") == "0"
    previews = [BASE / f"slide_previews/slide-rendered-{i}.png" for i in (1, 2)]
    for p in previews:
        assert Image.open(p).size == (1920, 1080)
    report = {
        "passed": True, "pptx_sha256": hashlib.sha256(deck.read_bytes()).hexdigest(),
        "slide_count": 2, "dimensions_emu": [18288000, 10287000], "aspect": "16:9",
        "embedded_video_byte_identical": True, "embedded_animated_gif_byte_identical": True,
        "embedded_gif_frames": 287, "autoplay_timing_declared": True,
        "slide_2_table_editable": True, "table_rows_verified_from_raw_episodes": totals,
        "benchmark_tests_at_milestone": 96, "current_tests_including_replay": 102,
        "oracle_passed": 160, "oracle_total": 160, "speaker_notes_embedded": True,
        "render_engine": "Local LibreOfficeDev 26.8 headless PDF + Poppler PNG, 1920x1080",
        "rendered_slides": [str(p.relative_to(BASE)) for p in previews],
        "visual_review": "Both slides individually inspected. Final fallback image visible. No title/table/text clipping.",
        "native_powerpoint_slideshow_verified": False,
        "limitation": "Microsoft PowerPoint AppleEvent opening timed out (-1712); desktop Computer Use permissions pending. Automatic playback in native Slide Show could not be observed. Actual embedded H.264 video and full animated GIF independently decoded and verified. Standalone MP4 provided.",
        "new_model_api_requests": 0,
    }
    (BASE / "pptx_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    finalization = json.loads((BASE / "pptx_finalization.json").read_text())
    finalization["file_sha256"] = report["pptx_sha256"]
    (BASE / "pptx_finalization.json").write_text(json.dumps(finalization, indent=2) + "\n")
    print(json.dumps({"passed": True, "slides": 2, "native_video": True, "animated_gif_frames": gif.n_frames, "raw_episode_rows": len(totals)}))


if __name__ == "__main__":
    main()
