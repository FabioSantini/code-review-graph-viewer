import argparse
import os
from pathlib import Path
import uvicorn
from .app import create_app


def main():
    parser=argparse.ArgumentParser(description='Live, read-only navigation for Code Review Graph databases.')
    parser.add_argument('--repo',type=Path,help='Repository indexed by Code Review Graph')
    parser.add_argument('--name',help='Display name for the project')
    parser.add_argument('--port',type=int,default=int(os.environ.get('GRAPHVIEWER_PORT','8120')))
    parser.add_argument('--demo',action='store_true',help='Create and open a synthetic example project')
    args=parser.parse_args()
    projects=None
    if args.demo:
        from .demo import create_demo
        root=create_demo(Path(os.environ.get('GRAPHVIEWER_DATA_DIR',Path.cwd()/'.local'))/'demo')
        projects={'Demo project':root/'.code-review-graph/graph.db'}
    elif args.repo:
        root=args.repo.resolve()
        db=(root/'.code-review-graph/graph.db').resolve()
        if not db.is_file():parser.error('Graph database not found. Build it with Code Review Graph first.')
        projects={args.name or root.name:db}
    app=create_app(projects=projects)
    if projects:
        from .sources import SourceInput, initial_source
        for name,path in projects.items():
            if not any(Path(item.get('database_path','')).resolve()==path.resolve() for item in app.state.source_registry.all()):
                value=initial_source(name,path)
                value.pop('id')
                app.state.source_registry.save(SourceInput(**value))
    uvicorn.run(app,host='127.0.0.1',port=args.port)


if __name__=='__main__':
    main()
