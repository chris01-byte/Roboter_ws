"""Lossless observer journal; no product input, clock or movement authority."""
import gzip
import hashlib
import json
import shutil
from pathlib import Path


def storage_budget(directory):
    mib = 1024*1024
    # B70 emitted 450 MB raw / 54 MB gzip in 630 s. Reserve 512 MiB
    # compressed trace for the original full deadline and larger task chains.
    # Auxiliary logs, map's temporary files and the product's unchanged save
    # reserve are separate. This is a preflight estimate, never a disk claim.
    budgets = dict(trace=512*mib, auxiliary=64*mib, map_temporary=32*mib,
                   map_save_minimum=512*mib, margin=64*mib)
    free = shutil.disk_usage(directory).free
    return dict(free_bytes=free, required_bytes=sum(budgets.values()),
                budgets=budgets, ready=free >= sum(budgets.values()))


class EventTrace:
    def __init__(self, path):
        self.path = Path(str(path)+'.gz')
        self._stream = gzip.open(self.path, 'wt', encoding='utf-8', newline='', compresslevel=1)
        self._digest = hashlib.sha256()
        self._bytes = 0
        self._closed = False

    def write(self, text):
        size = self._stream.write(text)
        payload = text.encode('utf-8')
        self._digest.update(payload)
        self._bytes += len(payload)
        return size

    def flush(self):
        self._stream.flush()

    def close(self):
        if self._closed:
            return
        self._stream.close()
        metadata = dict(schema=1, path=self.path.name, compression='gzip-level-1',
            uncompressed_bytes=self._bytes, sha256=self._digest.hexdigest(),
            compressed_bytes=self.path.stat().st_size, verified_decompression=False)
        self.path.with_suffix(self.path.suffix+'.meta.json').write_text(json.dumps(metadata, indent=2)+'\n')
        self._closed = True


def verify_trace(path):
    path = Path(path)
    metadata = json.loads(path.with_suffix(path.suffix+'.meta.json').read_text())
    digest = hashlib.sha256()
    size = 0
    with gzip.open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
            size += len(chunk)
    if size != metadata['uncompressed_bytes'] or digest.hexdigest() != metadata['sha256']:
        raise ValueError('trace_identity_mismatch')
    if path.stat().st_size != metadata['compressed_bytes']:
        raise ValueError('trace_compressed_size_mismatch')
    metadata['verified_decompression'] = True
    path.with_suffix(path.suffix+'.verified.json').write_text(json.dumps(metadata, indent=2)+'\n')
    return metadata
