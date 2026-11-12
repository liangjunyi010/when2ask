"""Archive ignored research evidence for a private GitHub Release.

Keeps source files untouched. Never includes credentials, runtime process
control, virtual environments, renderer intermediates or caches.
"""
from __future__ import annotations
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'handoff'
BUILD=BASE/'.build'
TAG='team11-handoff-20261112'
PATTERN=re.compile(rb'(?:sk-[A-Za-z0-9_-]{24,}|apikey_[A-Za-z0-9_]{40,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)')


def known_secrets():
    values=[]
    env=ROOT/'.env'
    if env.exists():
        for line in env.read_text().splitlines():
            m=re.match(r'\s*(?:export\s+)?(?:DEEPSEEK_API_KEY|TYPESAFE_API_KEY)\s*=\s*(.+?)\s*$',line)
            if m:
                value=m.group(1).strip().strip('\"\'')
                if len(value)>16:values.append(value.encode())
    for p in (ROOT/'outputs/local_console').rglob('*.token'):
        value=p.read_bytes().strip()
        if len(value)>16:values.append(value)
    return values


def main():
    BUILD.mkdir(parents=True,exist_ok=True)
    secrets=known_secrets()
    names=subprocess.check_output(['git','ls-files','--others','--ignored','--exclude-standard','-z','outputs'],cwd=ROOT).decode().split('\0')
    files=sorted(ROOT/n for n in names if n and (ROOT/n).is_file())
    packages={'raw-recordings':[],'local-console-evidence':[]}
    omissions=[]
    for p in files:
        rel=p.relative_to(ROOT)
        if p.suffix in ['.token','.pid','.stderr']or p.name=='session_budget.json':
            omissions.append({'path':str(rel),'reason':'volatile runtime authentication, process or budget state'})
            continue
        # Any per-frame intermediate can be rebuilt from the preserved recording.
        if 'frames'in rel.parts:
            omissions.append({'path':str(rel),'reason':'reproducible per-frame intermediate'})
            continue
        group='local-console-evidence'if str(rel).startswith('outputs/local_console/')else'raw-recordings'
        packages[group].append(p)
    result={'schema_version':'when2ask.private_handoff_assets.v1','release_tag':TAG,
            'repository':'liangjunyi010/when2ask','packages':[],'omissions':omissions,
            'not_project_deliverables':['.env and credentials','.venv','Python/test caches',
                'PowerPoint/HTML renderer build intermediates','live process control state'],
            'no_source_or_experiment_mutation':True,'new_model_api_calls':0}
    for group,items in packages.items():
        name=f"when2ask_{group.replace('-', '_')}_20261112.tar.gz"
        target=BUILD/name
        included=[]
        with target.open('wb')as raw:
            with gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0,compresslevel=6)as compressed:
                with tarfile.open(fileobj=compressed,mode='w|',format=tarfile.PAX_FORMAT)as archive:
                    for p in items:
                        data=p.read_bytes();rel=str(p.relative_to(ROOT))
                        if PATTERN.search(data)or any(v in data for v in secrets):
                            result['omissions'].append({'path':rel,'reason':'runtime credential detected; file omitted without modifying original'})
                            continue
                        entry=tarfile.TarInfo(rel);entry.size=len(data);entry.mode=0o644;entry.mtime=0
                        archive.addfile(entry,io.BytesIO(data))
                        included.append({'path':rel,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
        # Validate every archive entry and its exact bytes after compression.
        with tarfile.open(target,'r:gz')as archive:
            members=archive.getmembers()
            assert len(members)==len(included)
            for m,f in zip(members,included):
                assert m.name==f['path']and m.isfile()and not Path(m.name).is_absolute()and '..'not in Path(m.name).parts
                data=archive.extractfile(m).read()
                assert hashlib.sha256(data).hexdigest()==f['sha256']
                assert not PATTERN.search(data)and not any(v in data for v in secrets)
        package={'asset_name':name,'file_count':len(included),'original_bytes':sum(x['bytes']for x in included),
                 'archive_bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
                 'files':included}
        result['packages'].append(package)
        print(json.dumps({k:v for k,v in package.items()if k!='files'}),flush=True)
    (BASE/'raw_assets_manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    (BUILD/'SHA256SUMS').write_text(''.join(f"{p['sha256']}  {p['asset_name']}\n"for p in result['packages']))
    print(json.dumps({'archived_files':sum(p['file_count']for p in result['packages']),
                     'omitted_files':len(result['omissions']),'new_model_api_calls':0}),flush=True)


if __name__=='__main__':main()
