import urllib.request,json,ssl,tarfile,pathlib,hashlib,os
context=ssl.create_default_context(cafile='/etc/ssl/certs/ca-certificates.crt')
def get(url,token=None):
    return urllib.request.urlopen(urllib.request.Request(url,headers={'Authorization':'Bearer '+token} if token else {}),context=context,timeout=90)
repo='ros-navigation/navigation2'
token=json.load(get('https://ghcr.io/token?service=ghcr.io&scope=repository:'+repo+':pull'))['token']
manifest=json.load(open('/workspace/scratch/ap03-nav2-manifest.json'))
root=pathlib.Path('/workspace/scratch/ap03-nav2-rootfs');root.mkdir(exist_ok=True)
for i,layer in enumerate(manifest['layers']):
    digest=layer['digest'];file=pathlib.Path('/workspace/scratch/ap03-layer.tar.gz');h=hashlib.sha256()
    print(i,digest,layer['size'],flush=True)
    with get('https://ghcr.io/v2/'+repo+'/blobs/'+digest,token) as stream,file.open('wb') as out:
        while data:=stream.read(1024*1024):out.write(data);h.update(data)
    assert h.hexdigest()==digest.split(':')[1]
    with tarfile.open(file,'r:gz') as archive:
        for m in archive:
            name=m.name.lstrip('./');path=root/name
            if '..' in pathlib.PurePosixPath(name).parts:raise ValueError(name)
            if any(name.startswith(p) for p in ('opt/overlay_ws/build/','opt/overlay_ws/src/','opt/overlay_ws/log/','opt/underlay_ws/build/','opt/underlay_ws/src/','opt/underlay_ws/log/','var/cache/apt/archives/','var/lib/apt/lists/')):continue
            if pathlib.PurePosixPath(name).name.startswith('.wh.'):
                import shutil
                target=path.parent/path.name[4:]
                if target.exists():
                    if target.is_dir() and not target.is_symlink():shutil.rmtree(target)
                    else:target.unlink()
                continue
            m.name=name
            archive.extract(m,root,filter='fully_trusted')
    file.unlink()
print('complete',flush=True)
