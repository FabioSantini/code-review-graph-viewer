import test from 'node:test';
import assert from 'node:assert/strict';
import { loadLayout, saveLayout } from '../graphviewer/static/layout-store.js';

test('saved positions survive a new load, remain isolated and adapt to viewport size', () => {
  const values = new Map();
  const storage = { getItem: key => values.get(key), setItem: (key, value) => values.set(key, value) };
  assert.equal(saveLayout(storage, 'source/files/core', new Map([['file', { x: 200, y: 100 }]]), 800, 500), true);
  assert.deepEqual(loadLayout(storage, 'source/files/core', 1600, 1000).get('file'), { x: 400, y: 200 });
  assert.equal(loadLayout(storage, 'other/files/core', 800, 500).size, 0);
});

test('corrupt or inaccessible storage does not break the graph', () => {
  assert.equal(loadLayout({ getItem: () => '{broken' }, 'key', 800, 500).size, 0);
  assert.equal(loadLayout({ getItem: () => '[null,["bad",{}],["good",{"x":0.5,"y":0.5}]]' }, 'key', 800, 500).size, 1);
  assert.equal(saveLayout({ setItem: () => { throw Error('quota'); } }, 'key', new Map(), 800, 500), false);
});
