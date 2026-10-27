"""Small synthetic example; never imports or copies a user's code."""
from pathlib import Path
import sqlite3

FILES={
'app.py':'''from service import OrderService
from repository import OrderRepository

def main():
    return OrderService(OrderRepository()).place("example")
''',
'service.py':'''from repository import OrderRepository
from notification import Notifier

class OrderService:
    def __init__(self, repository):
        self.repository = repository

    def place(self, item):
        record = self.repository.save(item)
        Notifier().send(record)
        return record
''',
'repository.py':'''from storage import Storage

class OrderRepository:
    def save(self, item):
        return Storage().write(item)
''',
'notification.py':'''class Notifier:
    def send(self, message):
        return str(message)
''',
'storage.py':'''class Storage:
    def write(self, item):
        return {"item": item}
''',
'worker.py':'''from service import OrderService

def run(service):
    return service.place("background")
''',
'utility.py':'''def slug(value):
    return value.lower().replace(" ", "-")
''',
'web/client.js':'''export function showOrder(order) {
  return String(order.item);
}
''',
'web/app.js':'''import { showOrder } from "./client.js";
export function start(order) { return showOrder(order); }
''',
}


def create_demo(root:Path):
    root=root.resolve()
    dbpath=root/'.code-review-graph/graph.db'
    if dbpath.exists():return root
    dbpath.parent.mkdir(parents=True,exist_ok=True)
    for name,code in FILES.items():
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(code,encoding='utf-8')
    with sqlite3.connect(dbpath) as db:
        db.executescript('''CREATE TABLE nodes(id INTEGER PRIMARY KEY,kind TEXT,name TEXT,qualified_name TEXT UNIQUE,file_path TEXT,parent_name TEXT,language TEXT,line_start INTEGER,line_end INTEGER);
CREATE TABLE edges(id INTEGER PRIMARY KEY,kind TEXT,source_qualified TEXT,target_qualified TEXT,target_resolution TEXT);''')
        paths={name:(root/name).as_posix() for name in FILES}
        def node(key,kind,name,file,parent=None,start=1,end=None):
            db.execute('INSERT INTO nodes(kind,name,qualified_name,file_path,parent_name,language,line_start,line_end) VALUES(?,?,?,?,?,?,?,?)',(kind,name,key,paths[file],parent,'javascript' if file.endswith('.js') else 'python',start,end or len(FILES[file].splitlines())))
        def edge(a,b,kind='CALLS'):
            db.execute('INSERT INTO edges(kind,source_qualified,target_qualified,target_resolution) VALUES(?,?,?,?)',(kind,a,b,'direct'))
        for file in FILES:node(paths[file],'File',file,file)
        classes=[('OrderService','service.py',4),('OrderRepository','repository.py',3),('Notifier','notification.py',1),('Storage','storage.py',1)]
        keys={}
        for name,file,start in classes:
            key=paths[file]+'::'+name;keys[name]=key;node(key,'Class',name,file,start=start);edge(paths[file],key,'CONTAINS')
        for cls,method,file,start,end in [('OrderService','__init__','service.py',5,6),('OrderService','place','service.py',8,11),('OrderRepository','save','repository.py',4,5),('Notifier','send','notification.py',2,3),('Storage','write','storage.py',2,3)]:
            key=keys[cls]+'.'+method;keys[cls+'.'+method]=key;node(key,'Function',method,file,cls,start,end);edge(keys[cls],key,'CONTAINS')
        for file,name,start in [('app.py','main',4),('worker.py','run',3),('utility.py','slug',1),('web/client.js','showOrder',1),('web/app.js','start',2)]:
            key=paths[file]+'::'+name;keys[name]=key;node(key,'Function',name,file,start=start);edge(paths[file],key,'CONTAINS')
        for a,b in [('main','OrderService.place'),('run','OrderService.place'),('OrderService.place','OrderRepository.save'),('OrderService.place','Notifier.send'),('OrderRepository.save','Storage.write'),('start','showOrder')]:edge(keys[a],keys[b])
        for a,b in [('app.py','service.py'),('app.py','repository.py'),('service.py','repository.py'),('service.py','notification.py'),('repository.py','storage.py'),('worker.py','service.py'),('web/app.js','web/client.js')]:edge(paths[a],paths[b],'IMPORTS_FROM')
    return root
