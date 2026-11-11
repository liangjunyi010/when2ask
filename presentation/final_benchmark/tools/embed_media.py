"""Add MP4 playback to slide8 without changing editable slide content."""
import json
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile,ZIP_DEFLATED
BASE=Path(__file__).resolve().parents[1]
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships','p14':'http://schemas.microsoft.com/office/powerpoint/2010/main'}
for prefix,uri in NS.items():ET.register_namespace(prefix,uri)
def q(p,n):return f'{{{NS[p]}}}{n}'
with ZipFile(BASE/'.build/authored.pptx')as z:parts={n:z.read(n)for n in z.namelist()}
s=ET.fromstring(parts['ppt/slides/slide8.xml']);pics=s.findall('.//p:pic',NS);assert len(pics)==1
pic=pics[0];prop=pic.find('p:nvPicPr/p:cNvPr',NS);shape=prop.get('id')
fallback=deepcopy(pic);fp=fallback.find('p:nvPicPr/p:cNvPr',NS);fp.set('id',str(max(int(x.get('id'))for x in s.findall('.//p:cNvPr',NS))+1));fp.set('name','Animated replay fallback');fallback.find('p:blipFill/a:blip',NS).set(q('r','embed'),'rIdReplayGif')
tree=s.find('p:cSld/p:spTree',NS);tree.insert(list(tree).index(pic),fallback)
prop.set('name','Embedded synchronized Jev replay');ET.SubElement(prop,q('a','hlinkClick'),{'action':'ppaction://media'})
nv=pic.find('p:nvPicPr/p:nvPr',NS);ET.SubElement(nv,q('a','videoFile'),{q('r','link'):'rIdReplayVideo'});ext=ET.SubElement(ET.SubElement(nv,q('p','extLst')),q('p','ext'),{'uri':'{DAA4B4D4-6D71-4841-9C94-3DE7FCFB9230}'});ET.SubElement(ext,q('p14','media'),{q('r','embed'):'rIdReplayMedia'})
timing=(BASE/'tools/media_timing.xml').read_text().replace('__SHAPE_ID__',shape).replace('__DURATION_MS__','22200')
# Play once with slide entry; do not loop throughout narration.
timing=timing.replace('repeatCount="indefinite"','repeatCount="1000"')
s.append(ET.fromstring(timing));parts['ppt/slides/slide8.xml']=ET.tostring(s,encoding='utf-8',xml_declaration=True)
rns='http://schemas.openxmlformats.org/package/2006/relationships';rels=ET.fromstring(parts['ppt/slides/_rels/slide8.xml.rels'])
for id,typ,file in [('rIdReplayVideo',NS['r']+'/video','when2ask_highlight.mp4'),('rIdReplayMedia','http://schemas.microsoft.com/office/2007/relationships/media','when2ask_highlight.mp4'),('rIdReplayGif',NS['r']+'/image','when2ask_highlight.gif')]:ET.SubElement(rels,f'{{{rns}}}Relationship',{'Id':id,'Type':typ,'Target':'../media/'+file})
parts['ppt/slides/_rels/slide8.xml.rels']=ET.tostring(rels,encoding='utf-8',xml_declaration=True)
ns='http://schemas.openxmlformats.org/package/2006/content-types';types=ET.fromstring(parts['[Content_Types].xml']);ET.register_namespace('',ns)
for ext,mime in [('mp4','video/mp4'),('gif','image/gif')]:
 if not any(x.get('Extension')==ext for x in types):ET.SubElement(types,f'{{{ns}}}Default',{'Extension':ext,'ContentType':mime})
parts['[Content_Types].xml']=ET.tostring(types,encoding='utf-8',xml_declaration=True)
for ext in ['mp4','gif']:parts['ppt/media/when2ask_highlight.'+ext]=(BASE/('media/when2ask_highlight.'+ext)).read_bytes()
with ZipFile(BASE/'.build/with-media.pptx','w',ZIP_DEFLATED)as z:
 for name,content in parts.items():z.writestr(name,content)
print(json.dumps({'slide8':'embedded MP4 + animated GIF fallback','shape_id':shape}))
