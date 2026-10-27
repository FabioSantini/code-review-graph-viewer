const prefix = 'graphviewer-layout-v1:';

export function loadLayout(storage, key, width, height) {
  try {
    const entries = JSON.parse(storage.getItem(prefix + key) || '[]');
    return new Map(entries.filter(entry => Array.isArray(entry) && typeof entry[0] === 'string'
      && Number.isFinite(entry[1]?.x) && Number.isFinite(entry[1]?.y))
      .map(([id, point]) => [id, { x: point.x * width, y: point.y * height }]));
  } catch { return new Map(); }
}

export function saveLayout(storage, key, positions, width, height) {
  try {
    storage.setItem(prefix + key, JSON.stringify([...positions].map(([id, point]) =>
      [id, { x: point.x / width, y: point.y / height }])));
    return true;
  } catch { return false; }
}
