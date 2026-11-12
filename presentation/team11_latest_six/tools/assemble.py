"""Graft only authored slides 6–11 into the original package; embed the real movie."""
import copy
import json
import posixpath
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from xml.etree import ElementTree as E

BASE=Path(__file__).resolve().parents[1]
ROOT=BASE.parents[1]
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships','p14':'http://schemas.microsoft.com/office/powerpoint/2010/main'}
RNS='http://schemas.openxmlformats.org/package/2006/relationships'
CNS='http://schemas.openxmlformats.org/package/2006/content-types'
for prefix,uri in NS.items():E.register_namespace(prefix,uri)
def q(prefix,name):return f'{{{NS[prefix]}}}{name}'
def readzip(path):
    with ZipFile(path) as z:return {n:z.read(n) for n in z.namelist()}
def rels(part):return posixpath.join(posixpath.dirname(part),'_rels',posixpath.basename(part)+'.rels')
def resolve(part,target):return posixpath.normpath(posixpath.join(posixpath.dirname(part),target)).lstrip('/')
def dump(root):return E.tostring(root,encoding='utf-8',xml_declaration=True)

def main():
    original=readzip(BASE/'.build/source.pptx');authored=readzip(BASE/'.build/authored.pptx');parts=dict(original)
    content=E.fromstring(parts['[Content_Types].xml']);source_types=E.fromstring(authored['[Content_Types].xml'])
    ctypes={x.get('PartName','').lstrip('/'):x.get('ContentType') for x in source_types if x.tag.endswith('Override')}
    mapping={f'ppt/slides/slide{i}.xml':f'ppt/slides/slide{i}.xml' for i in range(1,12)}
    seen=set()
    def import_part(old):
        if old in seen:return mapping[old]
        new=mapping.setdefault(old,posixpath.join(posixpath.dirname(old),'w2a_'+posixpath.basename(old)))
        seen.add(old);parts[new]=authored[old]
        if ctypes.get(old):
            for existing in list(content):
                if existing.get('PartName')=='/'+new:content.remove(existing)
            E.SubElement(content,f'{{{CNS}}}Override',{'PartName':'/'+new,'ContentType':ctypes[old]})
        rp=rels(old)
        if rp in authored:
            tree=E.fromstring(authored[rp])
            for rel in tree:
                if rel.get('TargetMode')=='External':continue
                target=resolve(old,rel.get('Target'));kind=rel.get('Type','').split('/')[-1]
                if kind=='slideLayout':
                    oldrels=E.fromstring(original[rels(new)])
                    targetnew=resolve(new,next(r.get('Target') for r in oldrels if r.get('Type','').endswith('/slideLayout')))
                elif kind=='notesMaster':targetnew='ppt/notesMasters/notesMaster1.xml'
                elif kind=='slide' and target in mapping:targetnew=mapping[target]
                else:targetnew=import_part(target)
                rel.set('Target',posixpath.relpath(targetnew,posixpath.dirname(new)))
            parts[rels(new)]=dump(tree)
        return new
    for i in range(6,12):import_part(f'ppt/slides/slide{i}.xml')
    for x in source_types:
        if x.tag.endswith('Default') and not any(y.get('Extension')==x.get('Extension') for y in content):content.append(copy.deepcopy(x))

    # Native PowerPoint media relationship and autoplay timing. Static poster remains behind it.
    slide=E.fromstring(parts['ppt/slides/slide10.xml']);pic=slide.find('.//p:pic',NS);assert pic is not None
    prop=pic.find('p:nvPicPr/p:cNvPr',NS);ident=prop.get('id')
    fallback=copy.deepcopy(pic);fp=fallback.find('p:nvPicPr/p:cNvPr',NS)
    fp.set('id',str(max(int(x.get('id')) for x in slide.findall('.//p:cNvPr',NS))+1));fp.set('name','Command center poster fallback')
    tree=slide.find('p:cSld/p:spTree',NS);tree.insert(list(tree).index(pic),fallback)
    prop.set('name','When2Ask 50 second live console demo');E.SubElement(prop,q('a','hlinkClick'),{'action':'ppaction://media'})
    nv=pic.find('p:nvPicPr/p:nvPr',NS);E.SubElement(nv,q('a','videoFile'),{q('r','link'):'rIdConsoleVideo'})
    ext=E.SubElement(E.SubElement(nv,q('p','extLst')),q('p','ext'),{'uri':'{DAA4B4D4-6D71-4841-9C94-3DE7FCFB9230}'})
    E.SubElement(ext,q('p14','media'),{q('r','embed'):'rIdConsoleMedia'})
    timing=(ROOT/'presentation/team11_final/tools/media_timing.xml').read_text().replace('__SHAPE_ID__',ident).replace('__DURATION_MS__','50000').replace('repeatCount="indefinite"','repeatCount="1000"')
    oldtiming=slide.find('p:timing',NS)
    if oldtiming is not None:slide.remove(oldtiming)
    slide.append(E.fromstring(timing));parts['ppt/slides/slide10.xml']=dump(slide)
    rr=E.fromstring(parts['ppt/slides/_rels/slide10.xml.rels'])
    for rid,typ in [('rIdConsoleVideo',NS['r']+'/video'),('rIdConsoleMedia','http://schemas.microsoft.com/office/2007/relationships/media')]:
        E.SubElement(rr,f'{{{RNS}}}Relationship',{'Id':rid,'Type':typ,'Target':'../media/w2a_console_50s.mp4'})
    parts['ppt/slides/_rels/slide10.xml.rels']=dump(rr)
    parts['ppt/media/w2a_console_50s.mp4']=(ROOT/'presentation/command_center_demo_v1/media/When2Ask_Command_Center_50s.mp4').read_bytes()
    if not any(x.get('Extension')=='mp4'for x in content):E.SubElement(content,f'{{{CNS}}}Default',{'Extension':'mp4','ContentType':'video/mp4'})
    # Drop unreachable old back-half media/charts; referenced first-five assets remain untouched.
    reachable={'[Content_Types].xml','_rels/.rels'}
    def visit(part):
        if part in reachable:return
        reachable.add(part);rp=rels(part)
        if rp in parts:
            reachable.add(rp)
            for r in E.fromstring(parts[rp]):
                if r.get('TargetMode')!='External':visit(resolve(part,r.get('Target')))
    for r in E.fromstring(parts['_rels/.rels']):
        if r.get('TargetMode')!='External':visit(posixpath.normpath(r.get('Target').lstrip('/')))
    parts={n:v for n,v in parts.items() if n in reachable}
    for x in list(content):
        if x.tag.endswith('Override') and x.get('PartName','').lstrip('/') not in parts:content.remove(x)
    E.register_namespace('',CNS)
    parts['[Content_Types].xml']=dump(content)
    for i in range(1,6):
        assert parts[f'ppt/slides/slide{i}.xml']==original[f'ppt/slides/slide{i}.xml']
        assert parts[f'ppt/slides/_rels/slide{i}.xml.rels']==original[f'ppt/slides/_rels/slide{i}.xml.rels']
    dest=BASE/'.build/with-media.pptx'
    with ZipFile(dest,'w',ZIP_DEFLATED) as z:
        for n,v in parts.items():z.writestr(n,v)
    print(json.dumps({'path':str(dest),'first_five_slides_exact':True,'video_bytes':len(parts['ppt/media/w2a_console_50s.mp4']),'parts':len(parts)}))

if __name__=='__main__':main()
