"""Read indexed source code inside the configured repository only."""
from pathlib import Path

from fastapi import HTTPException


def read_code(source, node):
    if node.get('category') not in ('files', 'classes', 'functions', 'methods', 'tests'):
        raise HTTPException(400, 'This element has no source code')
    if not source.get('repo_root'):
        raise HTTPException(409, 'Configure a local repository root to view source code')
    root = Path(source['repo_root']).resolve()
    path = Path(node.get('file_path') or node.get('path') or '')
    path = (path if path.is_absolute() else root / path).resolve()
    if not path.is_relative_to(root):
        raise HTTPException(403, 'Source file is outside the configured repository')
    try:
        with path.open('rb') as stream:
            raw = stream.read(2_000_001)
    except OSError as exc:
        raise HTTPException(404, 'Source file is not available locally') from exc
    if len(raw) > 2_000_000:
        raise HTTPException(413, 'Source file exceeds the 2 MB viewer limit')
    if b'\0' in raw:
        raise HTTPException(415, 'Binary files cannot be displayed')
    text = raw.decode('utf-8-sig', errors='replace')
    lines = text.splitlines()
    symbol = node.get('category') != 'files'
    start = max(1, int(node.get('line_start') or 1)) if symbol else 1
    end = max(start, int(node.get('line_end') or len(lines) or 1)) if symbol else len(lines)
    return {'name': node['name'], 'path': path.relative_to(root).as_posix(),
            'language': node.get('language', ''), 'start_line': start, 'end_line': min(end, len(lines)),
            'code': '\n'.join(lines[start - 1:end]),
            'notice': 'Line ranges come from the graph index; refresh the index if the source has changed.' if symbol else ''}
