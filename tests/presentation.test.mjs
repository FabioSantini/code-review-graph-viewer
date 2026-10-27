import test from 'node:test';
import assert from 'node:assert/strict';
import { nodePresentation, orbitPositions, wrapLabel } from '../graphviewer/static/presentation.js';

test('file label is the basename and subtitle is a relative directory', () => {
  const node = { kind: 'File', category: 'files', name: 'C:\\repo\\flowgw\\context\\harness.py', path: 'flowgw/context/harness.py' };
  const result = nodePresentation(node);
  assert.equal(result.name, 'harness.py');
  assert.equal(result.location, 'flowgw/context');
  assert.equal(result.type, 'File');
});

test('long file names wrap without losing any characters', () => {
  const name = 'a_very_long_workflow_configuration_file.py';
  assert.equal(wrapLabel(name, 15).join(''), name);
  assert.ok(wrapLabel(name, 15).every(line => line.length <= 15));
});

test('core and neighbors use deterministic arcs rather than fixed columns', () => {
  const core = { key: 'core' }, left = [{ key: 'a' }, { key: 'b' }, { key: 'c' }];
  const first = orbitPositions(core, left, [{ key: 'd' }], 1000, 650, 230);
  const second = orbitPositions(core, left, [{ key: 'd' }], 1000, 650, 230);
  assert.deepEqual(first, second);
  assert.equal(first.get('core').x, 500);
  assert.ok(first.get('a').x < 500);
  assert.notEqual(first.get('a').x, first.get('b').x);
  assert.ok(first.get('d').x > 500);
});
