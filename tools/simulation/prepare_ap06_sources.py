#!/usr/bin/env python3
"""Fetch/verify public AP-06 source pins; no package install or robot access."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request


def prepare(args):
    repo = Path(__file__).resolve().parents[2]
    lock = json.loads(Path(__file__).with_name('ap06_dependencies.json').read_text())
    cache = args.cache.resolve()
    cache.mkdir(parents=True, exist_ok=True)
    packages = []
    for source in lock['sources']:
        if args.only and source['name'] not in args.only:
            continue
        archive = cache/source['archive']
        if not archive.exists():
            if args.offline:
                raise RuntimeError('missing offline archive: '+str(archive))
            with urllib.request.urlopen(source['url'], timeout=60) as response:
                with archive.with_suffix('.download').open('wb') as output:
                    shutil.copyfileobj(response, output)
            archive.with_suffix('.download').rename(archive)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        if digest != source['sha256']:
            raise RuntimeError('archive SHA256 mismatch: '+str(archive))
        print('verified', source['name'], digest, flush=True)
        if args.verify_only:
            continue
        target = args.destination.resolve()/source['name']
        if target.exists():
            raise RuntimeError('refusing to overwrite existing source: '+str(target))
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='ap06-extract-', dir=target.parent) as staging:
            with tarfile.open(archive) as tar:
                tar.extractall(staging, filter='data')
            roots = list(Path(staging).iterdir())
            if len(roots) != 1 or not roots[0].is_dir():
                raise RuntimeError('unexpected source archive layout')
            roots[0].rename(target)
        if source['name'] == 'slam_toolbox':
            subprocess.run(['git', 'apply', '--unidiff-zero', str(repo/lock['slam_patch'])],
                           cwd=target, check=True)
        packages.extend(str(target/relative) for relative in source['packages'])
    if not args.verify_only:
        manifest = {'source_lock': str(Path(__file__).with_name('ap06_dependencies.json')),
                    'base_paths': packages, 'patched_slam': 'slam_toolbox' in [p.name for p in args.destination.glob('*')]}
        (args.destination/'prepared.json').write_text(json.dumps(manifest, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--only', nargs='+', help='prepare selected dependencies for diagnostics')
    prepare(parser.parse_args())
