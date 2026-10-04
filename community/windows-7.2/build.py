"""Append the v7 UI addon to the verified v6 executable; every existing payload stays intact."""
import hashlib,json,marshal,pathlib,struct,zlib,sys
work=pathlib.Path(__file__).resolve().parent/'src'
expected={'folder':'68f16789cc4571f3d4b3486e437933935c3cf73c757b08d74e0179d6cca800b1','portable':'094580c433afc006d053d8f9a8ee233e819a532e650b5251f49185a92bd4d389'}
modules=[('glass_theme.py','speed_editor_glass_theme'),('glass_overlay.py','speed_editor_glass_overlay'),('glass_help.py','speed_editor_glass_help'),('uniform_controls.py','speed_editor_uniform_controls'),('precision_input.py','speed_editor_precision_input'),('shared_controls.py','speed_editor_shared_controls'),('consistent_ui.py','speed_editor_consistent_ui'),('switch_reliability.py','speed_editor_switch_reliability'),('extra_editor.py','speed_editor_extra_editor'),('glass_ui.py','speed_editor_glass_ui')]
loader='import sys,types\n';hashes={}
for filename,name in modules:
    text=(work/filename).read_text(encoding='utf8');hashes[filename]=hashlib.sha256(text.encode()).hexdigest()
    compile(text,filename,'exec');loader+=f'mod=types.ModuleType({name!r})\nmod.__file__={filename!r}\nsys.modules[mod.__name__]=mod\nexec(compile({text!r},{filename!r},"exec"),mod.__dict__)\n'
loader+='mod.install()\n';raw=marshal.dumps(compile(loader,'_glass_upgrade.py','exec'));addon=('_glass_upgrade',b's',1,len(raw),zlib.compress(raw))
report={'baseline':expected,'source_sha256':hashes}
import argparse
parser=argparse.ArgumentParser(description='Add the v7 UI to a locally supplied, verified v6 executable.')
parser.add_argument('baseline',type=pathlib.Path);parser.add_argument('output',type=pathlib.Path)
args=parser.parse_args()
if sys.version_info[:2]!=(3,12):raise SystemExit('Use Python 3.12 (the target executable runtime).')
data=args.baseline.read_bytes();digest=hashlib.sha256(data).hexdigest()
kind=next((k for k,v in expected.items() if v==digest),None)
if kind is None:raise SystemExit('Baseline hash does not match a supported v6 executable.')
if args.output.resolve()==args.baseline.resolve():raise SystemExit('Choose a separate output path.')
if args.output.exists():raise SystemExit('Output already exists; choose a new filename.')
for _ in [None]:
    at=data.rfind(b'MEI\x0c\x0b\x0a\x0b\x0e');magic,length,to,ts,version,lib=struct.unpack('!8sIIII64s',data[at:at+88]);start=at+88-length;pos=start+to;entries=[]
    while pos<start+to+ts:
        n,off,size,rawsize,flag,typ=struct.unpack('!iIIIBc',data[pos:pos+18]);name=data[pos+18:pos+n].split(b'\0',1)[0].decode();pos+=n
        if name=='main':entries.append(addon)
        entries.append((name,typ,flag,rawsize,data[start+off:start+off+size]))
    payload=[];table=[];off=0
    for name,typ,flag,rawsize,blob in entries:
        encoded=name.encode()+b'\0';n=(18+len(encoded)+15)//16*16
        table.append(struct.pack('!iIIIBc',n,off,len(blob),rawsize,flag,typ)+encoded+b'\0'*(n-18-len(encoded)));payload.append(blob);off+=len(blob)
    table=b''.join(table);output=args.output;output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes(data[:start]+b''.join(payload)+table+struct.pack('!8sIIII64s',magic,off+len(table)+88,off,len(table),version,lib))
    report[kind+'_sha256']=hashlib.sha256(output.read_bytes()).hexdigest();report[kind+'_bytes']=output.stat().st_size
print(json.dumps(report,indent=2))
