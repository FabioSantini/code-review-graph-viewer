export async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { 'Content-Type': 'application/json', ...options.headers } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail || response.statusText);
    throw new Error(detail);
  }
  return response.status === 204 ? null : response.json();
}

export function element(tag, className = '', text = '') {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
}

export const labels = { files: 'Files', classes: 'Classes', functions: 'Functions', methods: 'Methods',
  folders: 'Folders', languages: 'Languages', architecture: 'Architecture', tests: 'Tests' };
export const icons = { files: '▤', classes: '▣', functions: 'ƒ', methods: '⌘', folders: '▱', languages: '〈〉', architecture: '◈', tests: '✓' };
