import { element, labels } from './api.js';

function row(container, name, value) {
  if (value === undefined || value === null || value === '') return;
  const dl = element('dl', 'info-row');
  dl.append(element('dt', '', name), element('dd', '', String(value)));
  container.append(dl);
}

export function inspect(node, graph, makeCore, explore, openCode) {
  const target = document.querySelector('#node-info'); target.replaceChildren();
  target.append(element('span', 'kind-pill', labels[node.category] || node.kind || 'Project'));
  target.append(element('h3', '', node.name));
  if (node.overview) {
    target.append(element('p', '', 'Choose an element in the graph, or browse the complete list.'));
    return;
  }
  const location = element('div', 'info-section'); location.append(element('h4', '', 'Location'));
  row(location, 'File or area', node.path || node.file_path);
  row(location, 'Full path', node.file_path && node.file_path !== node.path ? node.file_path : null);
  row(location, 'Language', node.language);
  row(location, 'Lines', node.line_start ? `${node.line_start}–${node.line_end || node.line_start}` : '');
  row(location, 'Containing class / element', node.parent_name);
  row(location, 'Files in this area', node.member_count);
  target.append(location);
  const signature = element('div', 'info-section'); signature.append(element('h4', '', 'Definition'));
  row(signature, 'Signature', node.signature || node.params);
  row(signature, 'Returns', node.return_type); row(signature, 'Description', node.docstring);
  if (signature.children.length > 1) target.append(signature);
  if (graph && !graph.overview) {
    const edges = graph.edges.filter(edge => edge.source === node.key || edge.target === node.key);
    const section = element('div', 'info-section'); section.append(element('h4', '', 'Visible connections'));
    row(section, 'Dependencies', new Set(edges.filter(edge => edge.source === node.key).map(edge => edge.target)).size);
    row(section, 'Used by', new Set(edges.filter(edge => edge.target === node.key).map(edge => edge.source)).size);
    row(section, 'Relation types', [...new Set(edges.map(edge => edge.kind))].join(', ')); target.append(section);
  }
  const actions = element('div', 'info-section');
  if (['files', 'classes', 'functions', 'methods', 'tests'].includes(node.category)) {
    const open = element('button', 'button primary', 'Open');
    open.onclick = () => openCode(node); actions.append(open);
  }
  const center = element('button', 'button primary', 'Make central node'); center.onclick = () => makeCore(node);
  const contents = element('button', 'button', ['files', 'classes', 'folders', 'architecture', 'languages'].includes(node.category) ? 'Explore contents' : 'Explore calls');
  contents.onclick = () => explore(node); actions.append(center, contents); target.append(actions);
  if (node.category === 'classes') target.append(element('p', '', 'Properties are shown only if the graph index contains them.'));
}
