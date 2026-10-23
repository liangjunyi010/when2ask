"""Add an embedded H.264 movie and animated GIF poster to authored slide 1.

The deck is authored with Artifact Tool. This narrowly scoped OOXML step adds
media, which that authoring API does not expose. It never changes source logs.
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from xml.etree import ElementTree as ET

BASE = Path(__file__).resolve().parents[1]
NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "p14": "http://schemas.microsoft.com/office/powerpoint/2010/main",
}
for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def main() -> None:
    source = BASE / ".build/slides-authored.pptx"
    target = BASE / ".build/slides-with-media.pptx"
    with ZipFile(source) as z:
        parts = {name: z.read(name) for name in z.namelist()}
    slide = ET.fromstring(parts["ppt/slides/slide1.xml"])
    pics = slide.findall(".//p:pic", NS)
    assert len(pics) == 1, "Expected exactly the replay poster"
    pic = pics[0]
    # Some PDF/static renderers omit media objects entirely. A real animated
    # GIF picture below the movie supplies a visible, playable fallback.
    fallback = deepcopy(pic)
    fallback_props = fallback.find("p:nvPicPr/p:cNvPr", NS)
    assert fallback_props is not None
    all_ids = [int(x.attrib["id"]) for x in slide.findall(".//p:cNvPr", NS)]
    fallback_props.set("id", str(max(all_ids) + 1))
    fallback_props.set("name", "When2Ask synchronized replay (animated GIF fallback)")
    fallback_props.set("descr", "Full 287-frame synchronized HTML animation, not a static first frame.")
    fallback.find("p:blipFill/a:blip", NS).set(q("r", "embed"), "rIdReplayAnimatedPoster")
    tree = slide.find("p:cSld/p:spTree", NS)
    assert tree is not None
    tree.insert(list(tree).index(pic), fallback)
    cnv = pic.find("p:nvPicPr/p:cNvPr", NS)
    assert cnv is not None
    shape_id = cnv.attrib["id"]
    cnv.set("name", "When2Ask synchronized replay (embedded MP4)")
    cnv.set("descr", "Actual HTML replay. Click to play if automatic playback is disabled by the viewer.")
    ET.SubElement(cnv, q("a", "hlinkClick"), {"action": "ppaction://media"})
    nv = pic.find("p:nvPicPr/p:nvPr", NS)
    assert nv is not None
    ET.SubElement(nv, q("a", "videoFile"), {q("r", "link"): "rIdReplayVideo"})
    ext = ET.SubElement(ET.SubElement(nv, q("p", "extLst")), q("p", "ext"),
                        {"uri": "{DAA4B4D4-6D71-4841-9C94-3DE7FCFB9230}"})
    ET.SubElement(ext, q("p14", "media"), {q("r", "embed"): "rIdReplayMedia"})
    blip = pic.find("p:blipFill/a:blip", NS)
    assert blip is not None
    blip.set(q("r", "embed"), "rIdReplayAnimatedPoster")

    # One media node on the slide timeline, beginning at slide entry.
    # CommonMediaNode/Video follow ISO/IEC 29500 (Microsoft Learn reference).
    assert slide.find("p:timing", NS) is None
    timing = ET.SubElement(slide, q("p", "timing"))
    root = ET.SubElement(ET.SubElement(ET.SubElement(timing, q("p", "tnLst")), q("p", "par")),
                         q("p", "cTn"), {"id": "1", "dur": "indefinite", "restart": "never", "nodeType": "tmRoot"})
    video = ET.SubElement(ET.SubElement(root, q("p", "childTnLst")), q("p", "video"))
    media_node = ET.SubElement(video, q("p", "cMediaNode"), {"vol": "0", "numSld": "1", "showWhenStopped": "1"})
    time_node = ET.SubElement(media_node, q("p", "cTn"), {"id": "2", "fill": "hold", "display": "0"})
    ET.SubElement(ET.SubElement(time_node, q("p", "stCondLst")), q("p", "cond"), {"delay": "0"})
    ET.SubElement(ET.SubElement(media_node, q("p", "tgtEl")), q("p", "spTgt"), {"spid": shape_id})
    parts["ppt/slides/slide1.xml"] = ET.tostring(slide, encoding="utf-8", xml_declaration=True)

    rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    rels = ET.fromstring(parts["ppt/slides/_rels/slide1.xml.rels"])
    for ident, typ, name in [
        ("rIdReplayVideo", NS["r"] + "/video", "when2ask-replay.mp4"),
        ("rIdReplayMedia", "http://schemas.microsoft.com/office/2007/relationships/media", "when2ask-replay.mp4"),
        ("rIdReplayAnimatedPoster", NS["r"] + "/image", "when2ask-replay.gif"),
    ]:
        ET.SubElement(rels, f"{{{rel_ns}}}Relationship", {"Id": ident, "Type": typ, "Target": f"../media/{name}"})
    parts["ppt/slides/_rels/slide1.xml.rels"] = ET.tostring(rels, encoding="utf-8", xml_declaration=True)
    types_ns = "http://schemas.openxmlformats.org/package/2006/content-types"
    types = ET.fromstring(parts["[Content_Types].xml"])
    for extension, mime in [("mp4", "video/mp4"), ("gif", "image/gif")]:
        assert not any(x.get("Extension") == extension for x in types)
        ET.SubElement(types, f"{{{types_ns}}}Default", {"Extension": extension, "ContentType": mime})
    ET.register_namespace("", types_ns)
    parts["[Content_Types].xml"] = ET.tostring(types, encoding="utf-8", xml_declaration=True)
    parts["ppt/media/when2ask-replay.mp4"] = (BASE / "media/when2ask_milestone_highlight.mp4").read_bytes()
    parts["ppt/media/when2ask-replay.gif"] = (BASE / "media/when2ask_milestone_highlight.gif").read_bytes()
    with ZipFile(target, "w", ZIP_DEFLATED) as z:
        for name, content in parts.items():
            z.writestr(name, content)
    print(json.dumps({"draft": str(target), "media_shape_id": shape_id, "embedded": ["MP4", "animated GIF"], "slide_count": 2}))


if __name__ == "__main__":
    main()
