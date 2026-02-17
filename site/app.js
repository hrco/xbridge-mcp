(() => {
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const logEvent = (name, data = {}) => console.log('[event]', name, data);

  $$('.tabs').forEach((tabs) => {
    tabs.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-tab]');
      if (!btn) return;
      const scope = tabs.parentElement;
      const id = btn.dataset.tab;
      $$('button', tabs).forEach((b) => b.classList.toggle('active', b === btn));
      $$('[data-panel]', scope).forEach((p) => p.classList.toggle('active', p.dataset.panel === id));
      logEvent('tab_switch', { id });
    });
  });

  $$('.copy-btn').forEach((btn) => btn.addEventListener('click', async () => {
    const target = document.querySelector(btn.dataset.copyTarget || '');
    if (!target) return;
    await navigator.clipboard.writeText(target.textContent || '');
    btn.textContent = 'Copied';
    setTimeout(() => (btn.textContent = 'Copy Active Snippet'), 1000);
    logEvent('copy_snippet');
  }));

  const term = document.querySelector('#terminalStream pre');
  if (term) {
    const lines = [
      '[mcp] handshaking transport=stdio',
      '[xai] model=grok-3-mini status=ready',
      '[tool] grok-web-search latency=132ms',
      '[tool] grok-session-chat latency=89ms',
      '[ok] pipeline health: green'
    ];
    let i = 0;
    setInterval(() => {
      term.textContent += '\n' + lines[i++ % lines.length];
      term.scrollTop = term.scrollHeight;
    }, 1400);
  }

  const tbody = document.querySelector('#testResults');
  const tlog = document.querySelector('#testLog code');
  const runMode = document.querySelector('#runMode');
  const apiKeyInput = document.querySelector('#apiKeyInput');

  const appendResult = (name, pass, latency, mode) => {
    if (tbody) {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${name}</td><td class="${pass ? 'ok' : 'bad'}">${pass ? 'PASS' : 'FAIL'}</td><td>${latency}ms</td><td>${mode}</td><td>${new Date().toLocaleTimeString()}</td>`;
      tbody.prepend(tr);
    }
    if (tlog) tlog.textContent += `\n[${pass ? 'pass' : 'fail'}] ${name} (${latency}ms) mode=${mode}`;
  };

  const runMock = async (name) => {
    const latency = 60 + Math.floor(Math.random() * 220);
    const pass = Math.random() > 0.1;
    await new Promise((r) => setTimeout(r, 250));
    appendResult(name, pass, latency, 'mock');
    logEvent('run_test', { name, pass, latency, mode: 'mock' });
  };

  const runLive = async (name) => {
    const key = (apiKeyInput?.value || '').trim();
    if (!key) {
      alert('Live mode requires your xAI API key.');
      return;
    }
    const t0 = performance.now();
    try {
      const res = await fetch('/api/demo/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-XAI-API-Key': key
        },
        body: JSON.stringify({ test: name })
      });
      const data = await res.json().catch(() => ({}));
      const latency = Math.round(performance.now() - t0);
      const pass = Boolean(res.ok && data?.ok !== false);
      appendResult(name, pass, latency, 'live');
      if (tlog) tlog.textContent += `\n[live] response=${JSON.stringify(data).slice(0, 160)}`;
      logEvent('run_test', { name, pass, latency, mode: 'live' });
    } catch (err) {
      const latency = Math.round(performance.now() - t0);
      appendResult(name, false, latency, 'live');
      if (tlog) tlog.textContent += `\n[live-error] ${String(err)}`;
    }
  };

  const run = async (name) => {
    const mode = runMode?.value || 'mock';
    if (mode === 'live') return runLive(name);
    return runMock(name);
  };

  $$('button[data-test]').forEach((btn) => btn.addEventListener('click', () => run(btn.dataset.test)));
  document.querySelector('#runAll')?.addEventListener('click', async () => {
    for (const name of ['smoke', 'search', 'session']) await run(name);
  });
})();
