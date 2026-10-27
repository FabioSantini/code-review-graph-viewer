import { api, element } from './api.js';

export class Sources {
  constructor(onChange) {
    this.onChange = onChange; this.dialog = document.querySelector('#sources-dialog');
    document.querySelector('#manage-sources').onclick = () => this.open();
    document.querySelector('#new-source').onclick = () => this.fill(null);
    document.querySelector('#endpoint-transport').onchange = () => {
      document.querySelector('#endpoint-database').value = ''; this.fields();
    };
    document.querySelector('#source-form').onsubmit = event => { event.preventDefault(); this.save(); };
    document.querySelector('#test-source').onclick = () => this.test();
  }
  async reload() { this.items = await api('/api/sources'); this.render(); return this.items; }
  open() { this.render(); this.fill(this.items.find(item => item.id === document.querySelector('#source-select').value)); this.dialog.showModal(); }
  fields() {
    const value = document.querySelector('#endpoint-transport').value;
    document.querySelector('#http-fields').hidden = value !== 'http';
    document.querySelector('#stdio-fields').hidden = value !== 'stdio';
    document.querySelector('#index-details').open = value === 'local';
  }
  fill(source) {
    const pairs = { 'edit-source-id': source?.id, 'endpoint-name': source?.name,
      'endpoint-transport': source?.transport || 'local', 'endpoint-url': source?.url,
      'endpoint-command': source?.command, 'endpoint-args': JSON.stringify(source?.args || [], null, 2),
      'endpoint-repo': source?.repo_root, 'endpoint-database': source?.database_path };
    for (const [id, value] of Object.entries(pairs)) document.getElementById(id).value = value || '';
    this.feedback(''); this.fields(); this.render();
  }
  render() {
    const list = document.querySelector('#source-list'); list.replaceChildren();
    for (const source of this.items || []) {
      const row = element('div', 'source-row');
      row.classList.toggle('active', source.id === document.querySelector('#edit-source-id').value);
      const name = element('button', 'source-name', source.name);
      name.append(element('small', '', source.transport === 'http' ? source.url : source.transport === 'stdio' ? 'Local MCP · stdio' : 'Local index'));
      name.onclick = () => this.fill(source);
      const remove = element('button', 'source-delete', '×'); remove.title = `Remove ${source.name}`;
      remove.onclick = () => this.remove(source);
      row.append(name, remove); list.append(row);
    }
  }
  payload() {
    const get = id => document.getElementById(id).value.trim();
    let args;
    try { args = JSON.parse(get('endpoint-args') || '[]'); } catch { throw new Error('Arguments must be a JSON array of strings.'); }
    if (!Array.isArray(args) || args.some(value => typeof value !== 'string')) throw new Error('Arguments must be a JSON array of strings.');
    return { name: get('endpoint-name'), transport: get('endpoint-transport'), url: get('endpoint-url'),
      command: get('endpoint-command'), args, repo_root: get('endpoint-repo'), database_path: get('endpoint-database') };
  }
  async save(announce = true) {
    try {
      const id = document.querySelector('#edit-source-id').value;
      const saved = await api('/api/sources' + (id ? '/' + id : ''), { method: id ? 'PUT' : 'POST', body: JSON.stringify(this.payload()) });
      await this.reload(); this.fill(saved); await this.onChange(saved.id);
      if (announce) this.feedback('Source saved. Select it from the graph source menu.');
      return saved;
    } catch (error) { this.feedback(error.message, true); return null; }
  }
  async test() {
    const button = document.querySelector('#test-source'); button.disabled = true;
    try {
      const saved = await this.save(false); if (!saved) return;
      this.feedback('Connecting to MCP… The first start can take up to 100 seconds.');
      const result = await api(`/api/sources/${saved.id}/connect`, { method: 'POST' });
      this.feedback(result.mode === 'mcp' ? `Connected. ${result.tools.length} MCP tools available.` : 'Local graph index is available.');
    } catch (error) { this.feedback(error.message, true); }
    finally { button.disabled = false; }
  }
  async remove(source) {
    if (!confirm(`Remove the connection “${source.name}”? Its graph database will not be deleted.`)) return;
    try {
      await api(`/api/sources/${source.id}`, { method: 'DELETE' });
      await this.reload(); this.fill(null); await this.onChange();
    } catch (error) { this.feedback(error.message, true); }
  }
  feedback(message, error = false) {
    const target = document.querySelector('#source-feedback'); target.textContent = message; target.classList.toggle('error', error);
  }
}
