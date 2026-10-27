import { api, element } from './api.js';

let request = 0;
export async function openCode(source, node) {
  const sequence = ++request;
  const dialog = document.querySelector('#code-dialog');
  const body = document.querySelector('#code-body');
  const meta = document.querySelector('#code-meta');
  document.querySelector('#code-title').textContent = node.name;
  meta.textContent = 'Loading source…'; body.replaceChildren();
  document.querySelector('#code-notice').textContent = '';
  if (!dialog.open) dialog.showModal();
  try {
    const data = await api(`/api/explore/${encodeURIComponent(source)}/code?${new URLSearchParams({key: node.key})}`);
    if (sequence !== request) return;
    meta.textContent = `${data.path} · ${data.language} · Lines ${data.start_line}–${data.end_line}`;
    for (const [index, line] of data.code.split('\n').entries()) {
      const row = element('div', 'code-line');
      const number = element('span', 'code-number', String(data.start_line + index));
      number.setAttribute('aria-hidden', 'true');
      row.append(number, element('code', '', line || ' ')); body.append(row);
    }
    document.querySelector('#code-notice').textContent = data.notice;
  } catch (error) {
    if (sequence !== request) return;
    meta.textContent = error.message;
  }
}
