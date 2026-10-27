import pytest
from fastapi import HTTPException
from graphviewer.code_view import read_code


def test_file_and_symbol_ranges(tmp_path):
    (tmp_path / 'example.py').write_text('class Demo:\n    def run(self):\n        return 1\n', encoding='utf-8')
    source = {'repo_root': str(tmp_path)}
    node = {'name': 'run', 'file_path': 'example.py', 'category': 'methods', 'line_start': 2, 'line_end': 3}
    result = read_code(source, node)
    assert result['start_line'] == 2
    assert result['code'] == '    def run(self):\n        return 1'
    assert read_code(source, {**node, 'category': 'files'})['code'].startswith('class Demo:')


def test_outside_repository_and_unavailable_files(tmp_path):
    source = {'repo_root': str(tmp_path)}
    for path, expected in [('../outside.py', 403), ('missing.py', 404)]:
        with pytest.raises(HTTPException) as error:
            read_code(source, {'name': 'x', 'category': 'files', 'file_path': path})
        assert error.value.status_code == expected


def test_binary_and_large_files(tmp_path):
    path = tmp_path / 'example'
    node = {'name': 'x', 'category': 'files', 'file_path': str(path)}
    for content, expected in [(b'\0binary', 415), (b'a' * 2_000_001, 413)]:
        path.write_bytes(content)
        with pytest.raises(HTTPException) as error:
            read_code({'repo_root': str(tmp_path)}, node)
        assert error.value.status_code == expected
