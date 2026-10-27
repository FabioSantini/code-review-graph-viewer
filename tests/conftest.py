import sqlite3

import pytest


@pytest.fixture
def graph(tmp_path):
    path = tmp_path / "graph.db"
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE nodes (
                id INTEGER PRIMARY KEY, kind TEXT, name TEXT,
                qualified_name TEXT, file_path TEXT, parent_name TEXT,
                language TEXT, line_start INTEGER, line_end INTEGER
            );
            CREATE TABLE edges (
                id INTEGER PRIMARY KEY, kind TEXT, source_qualified TEXT,
                target_qualified TEXT, target_resolution TEXT
            );
            INSERT INTO nodes VALUES (1,'File','app.py','app.py','app.py',NULL,'python',1,50);
            INSERT INTO nodes VALUES (2,'Class','Engine','app.py::Engine','app.py',NULL,'python',2,20);
            INSERT INTO nodes VALUES (3,'Function','run','app.py::Engine.run','app.py','Engine','python',3,6);
            INSERT INTO nodes VALUES (4,'Function','main','app.py::main','app.py',NULL,'python',22,25);
            INSERT INTO edges VALUES (1,'CONTAINS','app.py','app.py::Engine','direct');
            INSERT INTO edges VALUES (2,'CONTAINS','app.py::Engine','app.py::Engine.run','direct');
            INSERT INTO edges VALUES (3,'CONTAINS','app.py','app.py::main','direct');
            INSERT INTO edges VALUES (4,'CALLS','app.py::main','app.py::Engine.run','direct');
        """)
    return path

