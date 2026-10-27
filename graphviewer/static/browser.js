import { api, element, labels, icons } from './api.js';

export class Browser {
  constructor(context, onChoose) {
    this.context = context; this.onChoose = onChoose; this.dialog = document.querySelector('#browse-dialog');
    document.querySelector('#browse-prev').onclick = () => { this.offset = Math.max(0, this.offset - 50); this.load(); };
    document.querySelector('#browse-next').onclick = () => { this.offset += 50; this.load(); };
    document.querySelector('#browse-search').oninput = () => {
      clearTimeout(this.timer); this.timer = setTimeout(() => { this.offset = 0; this.load(); }, 200);
    };
  }
  async open(node = null) {
    this.localItems = null; this.node = node; this.offset = 0;
    document.querySelector('#browse-search').value = '';
    document.querySelector('#browse-title').textContent = node ? node.name : 'Choose an element';
    document.querySelector('#browse-context').textContent = node ? 'Contents · ' + (labels[node.category] || node.kind) : this.context().viewLabel;
    this.dialog.showModal(); await this.load();
  }
  async openItems(items, title) {
    this.node = null; this.localItems = items; this.offset = 0;
    document.querySelector('#browse-search').value = '';
    document.querySelector('#browse-title').textContent = title;
    document.querySelector('#browse-context').textContent = 'Hidden elements';
    if (!this.dialog.open) this.dialog.showModal();
    await this.load();
  }
  async load() {
    const state = this.context(), q = document.querySelector('#browse-search').value.trim();
    if (this.localItems) {
      const matches = this.localItems.filter(n => (n.name + ' ' + n.path).toLowerCase().includes(q.toLowerCase()));
      this.render(matches.slice(this.offset, this.offset + 50), { total: matches.length });
      document.querySelector('#browse-note').textContent = 'Choose an element from this hidden group to make it Master. Search covers the entire group.';
      return;
    }
    const query = new URLSearchParams({ ...state.filters, view: state.view, limit: 50, offset: this.offset, q });
    const path = this.node ? `children?${new URLSearchParams({ key: this.node.key, limit: 50, offset: this.offset })}` : `catalog?${query}`;
    const list = document.querySelector('#browse-items'); list.replaceChildren(element('p', 'dialog-note', 'Loading…'));
    const ticket = this.ticket = (this.ticket || 0) + 1;
    try {
      const data = await api(`/api/explore/${state.source}/${path}`);
      if (ticket !== this.ticket) return;
      const items = this.node && q ? data.items.filter(node => (node.name + ' ' + (node.path || '')).toLowerCase().includes(q.toLowerCase())) : data.items;
      this.render(items, data);
    } catch (error) { if (ticket === this.ticket) list.replaceChildren(element('p', 'dialog-note', error.message)); }
  }
  render(items, data) {
    const list = document.querySelector('#browse-items'); list.replaceChildren();
    document.querySelector('#browse-note').textContent = this.node?.category === 'classes'
      ? 'Methods and other members recorded by the index. Properties may not be indexed.'
      : this.node ? 'Choose a contained element to make it the new central node. Search filters this page.'
      : data.partial ? 'Partial catalog supplied by this MCP. A local graph index provides complete browsing.' : 'Choose an element to make it the central node.';
    if (!items.length) list.append(element('p', 'dialog-note', 'No indexed elements match this selection.'));
    for (const node of items) {
      const button = element('button', 'browse-item');
      const text = element('span'); text.append(element('strong', '', node.name), element('small', '', node.path || node.file_path || node.category));
      button.append(element('span', 'item-icon', icons[node.category] || '○'), text, element('span', 'item-arrow', '→'));
      button.onclick = () => { this.dialog.close(); this.onChoose(node); }; list.append(button);
    }
    document.querySelector('#browse-total').textContent = `${this.offset + (items.length ? 1 : 0)}–${this.offset + items.length} of ${data.total}`;
    document.querySelector('#browse-prev').disabled = this.offset === 0;
    document.querySelector('#browse-next').disabled = this.offset + 50 >= data.total;
  }
}
