const types = {
  files: ['File', '#2f9b60'], classes: ['Class', '#8452da'],
  functions: ['Function', '#c8772a'], methods: ['Method', '#168fa5'],
  folders: ['Folder', '#a17a31'], languages: ['Language', '#3d72b5'],
  architecture: ['Area', '#8452da'], tests: ['Test', '#b94c7a'],
};

export function nodePresentation(node) {
  const path = (node.path || node.file_path || '').replaceAll('\\', '/');
  const file = node.category === 'files' || node.kind === 'File';
  const rawName = (node.name || '').replaceAll('\\', '/');
  const name = file ? rawName.split('/').at(-1) : rawName;
  let location = file ? path.split('/').slice(0, -1).join('/') : path;
  if (/^(?:[A-Za-z]:\/|\/)/.test(location)) location = location.split('/').slice(-3).join('/');
  const [type, accent] = types[node.category] || ['Element', '#8fa4bb'];
  return { name, location: node.overview ? 'Choose an element to explore' : location || 'Project root', type, accent };
}

export function wrapLabel(text, maxChars) {
  const lines = [];
  let remaining = text;
  while (remaining.length > maxChars) {
    const slice = remaining.slice(0, maxChars);
    const separator = Math.max(slice.lastIndexOf('/'), slice.lastIndexOf('_'), slice.lastIndexOf('-'));
    const end = separator > maxChars / 2 ? separator + 1 : maxChars;
    lines.push(remaining.slice(0, end)); remaining = remaining.slice(end);
  }
  if (remaining) lines.push(remaining);
  return lines.length ? lines : [''];
}

export function orbitPositions(core, left, right, width, height, nodeWidth) {
  const center = { x: width / 2, y: height / 2 + 10 };
  const positions = new Map([[core.key, center]]);
  const radiusX = Math.max(nodeWidth + 20, width / 2 - nodeWidth / 2 - 22);
  const radiusY = Math.max(80, Math.min(height * .36, Math.max(left.length, right.length) * 77));
  for (const [nodes, sign] of [[left, -1], [right, 1]]) {
    nodes.forEach((node, index) => {
      const angle = nodes.length === 1 ? 0 : -1.02 + 2.04 * index / (nodes.length - 1);
      positions.set(node.key, { x: center.x + sign * radiusX * Math.cos(angle),
        y: center.y + radiusY * Math.sin(angle) });
    });
  }
  return positions;
}

