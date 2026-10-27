const NS = 'http://www.w3.org/2000/svg';
function svgNode(tag, attrs = {}, text = '') {
  const node = document.createElementNS(NS, tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  node.textContent = text;
  return node;
}
function short(text, length = 27) { return text.length > length ? text.slice(0, length - 1) + '…' : text; }

export class Graph {
  constructor(svg, onSelect, onExplore) {
    this.svg = svg; this.layer = svg.querySelector('#graph-layer');
    this.onSelect = onSelect; this.onExplore = onExplore;
    this.events = new AbortController();
    this.listen = (name, handler, options = {}) => this.svg.addEventListener(name, handler, { ...options, signal: this.events.signal });
    this.scale = 1; this.pan = { x: 0, y: 0 };
    this.listen('wheel', event => { event.preventDefault(); this.zoom(event.deltaY > 0 ? -.12 : .12); }, { passive: false });
    this.listen('pointerdown', event => this.startPan(event));
    this.listen('pointermove', event => this.movePan(event));
    this.listen('pointerup', () => this.endDrag());
    this.listen('pointercancel', () => this.endDrag());
    this.listen('lostpointercapture', () => this.endDrag());
    this.resizeObserver = new ResizeObserver(() => { if (this.data) this.render(this.data, false); });
    this.resizeObserver.observe(svg.parentElement);
  }
  startPan(event) {
    if (event.button !== 0 || this.drag) return;
    if (event.target.closest('.graph-node')) return;
    this.drag = { x: event.clientX, y: event.clientY, px: this.pan.x, py: this.pan.y };
    this.svg.setPointerCapture(event.pointerId);
  }
  movePan(event) {
    if (!this.drag) return;
    if (this.drag.node) {
      const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(this.layer.getScreenCTM().inverse());
      if (!this.drag.moved && Math.hypot(event.clientX - this.drag.x, event.clientY - this.drag.y) < 5) return;
      this.drag.moved = true;
      const position = { x: point.x - this.drag.offset.x, y: point.y - this.drag.offset.y };
      this.positions.set(this.drag.node.key, position);
      this.savedPositions.set(this.drag.node.key, position);
      this.drag.group.setAttribute('transform', `translate(${position.x},${position.y})`);
      this.edgeLayer.replaceChildren();
      this.drawEdges(this.data.edges, this.positions);
      return;
    }
    this.pan = { x: this.drag.px + event.clientX - this.drag.x, y: this.drag.py + event.clientY - this.drag.y };
    this.transform();
  }
  startNodeDrag(event, node, group) {
    if (event.button !== 0 || this.drag) return;
    event.stopPropagation(); event.preventDefault();
    const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(this.layer.getScreenCTM().inverse());
    const position = this.positions.get(node.key);
    this.drag = { node, group, x: event.clientX, y: event.clientY, offset: { x: point.x - position.x, y: point.y - position.y }, moved: false };
    group.classList.add('dragging');
    // Keep click and double-click targeted at the node while capturing its drag.
    group.setPointerCapture(event.pointerId);
  }
  endDrag() {
    if (this.drag?.node) {
      this.drag.group.classList.remove('dragging');
      if (this.drag.moved) {
        this.suppressClickUntil = performance.now() + 350;
        const saved = saveLayout(localStorage, this.data.layoutKey, this.savedPositions, this.width, this.height);
        if (!saved) this.onSaveError?.();
      }
    }
    this.drag = null;
  }
  zoom(delta) { this.scale = Math.max(.4, Math.min(2.3, this.scale + delta)); this.transform(); }
  fit() { this.scale = 1; this.pan = { x: 0, y: 0 }; this.transform(); }
  clear() { this.data = null; this.layer.replaceChildren(); }
  transform() {
    const x = this.width / 2, y = this.height / 2;
    this.layer.setAttribute('transform', `translate(${this.pan.x + x * (1 - this.scale)},${this.pan.y + y * (1 - this.scale)}) scale(${this.scale})`);
    this.onViewportChange?.();
  }
  render(data, reset = true) {
    this.data = data; this.layer.replaceChildren();
    this.width = this.svg.clientWidth || 800; this.height = this.svg.clientHeight || 500;
    this.svg.setAttribute('viewBox', `0 0 ${this.width} ${this.height}`);
    const capacity = Math.max(1, Math.min(5, Math.floor((this.height - 90) / 135)));
    const outgoing = [...new Map(data.outgoing.map(node => [node.key, node])).values()].slice(0, capacity);
    const outgoingKeys = new Set(outgoing.map(node => node.key));
    const incoming = [...new Map(data.incoming.filter(node => !outgoingKeys.has(node.key)).map(node => [node.key, node])).values()].slice(0, capacity);
    this.visibleCount = outgoing.length + incoming.length;
    this.nodeWidth = Math.max(150, Math.min(250, (this.width - 78) / 3));
    const positions = orbitPositions(data.core, outgoing, incoming, this.width, this.height, this.nodeWidth);
    this.savedPositions = loadLayout(localStorage, data.layoutKey, this.width, this.height);
    for (const [key, position] of this.savedPositions) if (positions.has(key)) positions.set(key, position);
    this.positions = positions;
    this.drawLabels(data.overview, outgoing.length, incoming.length);
    this.edgeLayer = svgNode('g'); this.layer.append(this.edgeLayer);
    this.drawEdges(data.edges, positions);
    for (const node of [data.core, ...outgoing, ...incoming]) this.drawNode(node, positions.get(node.key), node.key === data.core.key);
    if (reset) this.fit(); else this.transform();
  }
  drawLabels(overview, left, right) {
    const y = 30;
    if (left) this.layer.append(svgNode('text', { x: this.width * .19, y, class: 'column-label', 'text-anchor': 'middle' }, overview ? 'Explore' : 'Depends on'));
    if (right) this.layer.append(svgNode('text', { x: this.width * .81, y, class: 'column-label', 'text-anchor': 'middle' }, overview ? 'Explore' : 'Used by'));
  }
  drawEdges(edges, positions) {
    const seen = new Set();
    for (const edge of edges) {
      const a = positions.get(edge.source), b = positions.get(edge.target), key = edge.source + '>' + edge.target;
      if (!a || !b || seen.has(key)) continue;
      seen.add(key);
      const direction = b.x > a.x ? 1 : -1, start = a.x + direction * this.nodeWidth / 2, end = b.x - direction * this.nodeWidth / 2;
      const bend = (start + end) / 2;
      const path = svgNode('path', { d: `M${start},${a.y} C${bend},${a.y} ${bend},${b.y} ${end},${b.y}`, class: 'graph-edge' });
      path.append(svgNode('title', {}, `${edge.kind} · ${edge.count || 1} relation(s)`));
      this.edgeLayer.append(path);
    }
  }
  drawNode(node, position, core) {
    if (!position) return;
    const display = nodePresentation(node), lines = wrapLabel(display.name, Math.floor((this.nodeWidth - 22) / 8));
    const height = Math.max(94, 68 + lines.length * 19);
    const group = svgNode('g', { class: 'graph-node' + (core ? ' core' : ''), transform: `translate(${position.x},${position.y})`, tabindex: '0', role: 'button', 'aria-label': `${display.name}, ${display.type}. Enter for details, right arrow to explore.`, style: `--node-accent:${display.accent}` });
    group.dataset.key = node.key;
    this.drawBody(group, display, lines, height, core);
    group.addEventListener('pointerdown', event => this.startNodeDrag(event, node, group));
    group.addEventListener('click', () => { if (performance.now() >= (this.suppressClickUntil || 0)) this.select(node); });
    group.addEventListener('dblclick', event => { event.stopPropagation(); if (performance.now() >= (this.suppressClickUntil || 0)) this.onExplore(node); });
    group.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); this.select(node); }
      if (event.key === 'ArrowRight') { event.preventDefault(); this.onExplore(node); }
    });
    this.layer.append(group);
  }
  drawBody(group, display, lines, height, core) {
    const x = -this.nodeWidth / 2, y = -height / 2;
    group.append(svgNode('rect', { class: 'node-shell', x, y, width: this.nodeWidth, height, rx: 7 }));
    const header = `M${x + 7},${y} H${x + this.nodeWidth - 7} Q${x + this.nodeWidth},${y} ${x + this.nodeWidth},${y + 7} V${y + 24} H${x} V${y + 7} Q${x},${y} ${x + 7},${y} Z`;
    group.append(svgNode('path', { d: header, class: 'node-header' }));
    group.append(svgNode('text', { x: x + 11, y: y + 16, class: 'node-type' }, display.type));
    if (core) group.append(svgNode('text', { x: x + this.nodeWidth - 10, y: y + 16, 'text-anchor': 'end', class: 'node-core-label' }, 'Core'));
    lines.forEach((line, i) => group.append(svgNode('text', { x: x + 11, y: y + 46 + i * 19, class: 'node-title' }, line)));
    const path = short(display.location, Math.floor((this.nodeWidth - 22) / 5.4));
    group.append(svgNode('text', { x: x + 11, y: y + height - 13, class: 'node-subtitle' }, path));
    group.append(svgNode('circle', { cx: x, cy: 0, r: 3.5, class: 'node-port' }));
    group.append(svgNode('circle', { cx: x + this.nodeWidth, cy: 0, r: 3.5, class: 'node-port' }));
    group.append(svgNode('title', {}, `${display.name}\n${display.location}`));
  }
  select(node) {
    for (const item of this.layer.querySelectorAll('.graph-node')) item.classList.toggle('selected', item.dataset.key === node.key);
    this.onSelect(node);
  }
}
import { nodePresentation, orbitPositions, wrapLabel } from './presentation.js';
import { loadLayout, saveLayout } from './layout-store.js';

