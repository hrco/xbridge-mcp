(() => {
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const API_BASE = 'https://y0xx9n1oz7.execute-api.eu-west-1.amazonaws.com';

  const logEvent = (name, data = {}) => console.log('[event]', name, data);

  function showMsg(el, text, isError = false) {
    if (!el) return;
    el.hidden = false;
    el.textContent = text;
    el.classList.toggle('error', isError);
  }

  function hideMsg(el) {
    if (!el) return;
    el.hidden = true;
    el.textContent = '';
    el.classList.remove('error');
  }

  /* Tabs */
  $$('.tabs').forEach((tabs) => {
    tabs.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-tab]');
      if (!btn) return;
      const scope = tabs.parentElement;
      const id = btn.dataset.tab;
      $$('button', tabs).forEach((b) => {
        b.classList.toggle('active', b === btn);
        b.setAttribute('aria-selected', b === btn ? 'true' : 'false');
      });
      $$('[data-panel]', scope).forEach((p) => p.classList.toggle('active', p.dataset.panel === id));
      logEvent('tab_switch', { id });
    });
  });

  /* Copy buttons */
  $$('.copy-btn').forEach((btn) => btn.addEventListener('click', async () => {
    const target = document.querySelector(btn.dataset.copyTarget || '');
    if (!target) return;
    const original = btn.textContent;
    try {
      await navigator.clipboard.writeText(target.textContent || '');
      btn.textContent = 'Copied!';
      setTimeout(() => { btn.textContent = original; }, 1500);
      logEvent('copy_snippet');
    } catch {
      btn.textContent = 'Copy failed';
      setTimeout(() => { btn.textContent = original; }, 1500);
    }
  }));

  /* Terminal stream */
  const termPre = document.querySelector('#terminalStream pre');
  if (termPre) {
    const logLines = [
      '[boot] xbridge runtime online',
      '[auth] BYOK detected: XAI_API_KEY',
      '[mcp] handshaking transport=stdio',
      '[xai] model=grok-4 status=ready',
      '[tool] grok-chat ready',
      '[tool] grok-web-search ready',
      '[tool] grok-session-chat ready',
      '[tool] grok-web-search latency=132ms',
      '[tool] grok-session-chat latency=89ms',
      '[tool] grok-image-generate latency=2100ms',
      '[ok] pipeline health: green',
    ];
    const MAX_LINES = 10;
    let i = 0;
    let visible = [];
    const termBox = termPre.parentElement;

    function appendLogLine() {
      if (visible.length >= MAX_LINES) visible.shift();
      visible.push(logLines[i++ % logLines.length]);
      termPre.textContent = visible.join('\n');
      termBox.scrollTop = termBox.scrollHeight;
    }

    appendLogLine();
    appendLogLine();
    appendLogLine();
    setInterval(appendLogLine, 1400);
  }

  /* Topbar mobile menu */
  const navToggle = document.getElementById('navToggle');
  const mobileMenu = document.getElementById('mobileMenu');

  if (navToggle && mobileMenu) {
    const closeTopMenu = () => {
      mobileMenu.classList.remove('open');
      navToggle.setAttribute('aria-expanded', 'false');
      mobileMenu.setAttribute('aria-hidden', 'true');
      document.body.style.overflow = '';
    };

    navToggle.addEventListener('click', () => {
      const open = mobileMenu.classList.toggle('open');
      navToggle.setAttribute('aria-expanded', open);
      mobileMenu.setAttribute('aria-hidden', !open);
      document.body.style.overflow = open ? 'hidden' : '';
    });

    $$('.mobile-nav-link', mobileMenu).forEach((link) => {
      link.addEventListener('click', closeTopMenu);
    });
  }

  /* Sidebar mobile toggle */
  const sidebar = document.getElementById('sidebar');
  const mobileToggle = document.getElementById('mobileToggle');
  const backdrop = document.getElementById('backdrop');

  if (sidebar && mobileToggle && backdrop) {
    const closeSidebar = () => {
      sidebar.classList.remove('open');
      mobileToggle.setAttribute('aria-expanded', 'false');
      backdrop.hidden = true;
    };

    mobileToggle.addEventListener('click', () => {
      const isOpen = sidebar.classList.toggle('open');
      mobileToggle.setAttribute('aria-expanded', isOpen);
      backdrop.hidden = !isOpen;
    });

    backdrop.addEventListener('click', closeSidebar);
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeSidebar(); });
    $$('.nav-list a', sidebar).forEach((link) => link.addEventListener('click', closeSidebar));
  }

  /* Scroll-spy */
  const spyTargets = document.querySelectorAll('section[id], h2[id]');
  const navLinks = $$('.nav-list a');
  if (spyTargets.length && navLinks.length) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          navLinks.forEach((l) => l.classList.remove('active'));
          const active = document.querySelector(`.nav-list a[href="#${entry.target.id}"]`);
          if (active) active.classList.add('active');
        }
      });
    }, { threshold: 0.1, rootMargin: '-60px 0px -70% 0px' });
    spyTargets.forEach((s) => observer.observe(s));
  }

  /* Scroll reveal */
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((e) => { if (e.isIntersecting) e.target.classList.add('visible'); });
  }, { threshold: 0.06, rootMargin: '0px 0px -30px 0px' });
  $$('.reveal').forEach((el) => revealObserver.observe(el));

  /* Free key form */
  const freeForm = document.getElementById('free-form');
  const freeMsg = document.getElementById('free-msg');
  const resendHint = document.getElementById('resend-hint');
  const resendLink = document.getElementById('resend-link');

  if (freeForm) {
    freeForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = document.getElementById('free-email')?.value?.trim();
      if (!email) return;
      hideMsg(freeMsg);
      if (resendHint) resendHint.hidden = true;
      showMsg(freeMsg, 'Sending...');
      try {
        const r = await fetch(`${API_BASE}/keys/free`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email }),
        });
        const data = await r.json();
        if (r.ok) {
          showMsg(freeMsg, '✓ Key sent! Check your inbox (and spam folder).');
        } else if (r.status === 409) {
          showMsg(freeMsg, 'That email already has a key. Use the resend link below.');
          if (resendHint) resendHint.hidden = false;
        } else {
          showMsg(freeMsg, data.error || 'Something went wrong. Try again.', true);
        }
      } catch {
        showMsg(freeMsg, 'Request failed. Try again.', true);
      }
    });
  }

  if (resendLink) {
    resendLink.addEventListener('click', async (e) => {
      e.preventDefault();
      const email = document.getElementById('free-email')?.value?.trim();
      if (!email) return;
      showMsg(freeMsg, 'Resending...');
      try {
        await fetch(`${API_BASE}/keys/resend`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email }),
        });
        showMsg(freeMsg, '✓ If that email is registered, your key is on its way.');
        if (resendHint) resendHint.hidden = true;
      } catch {
        showMsg(freeMsg, 'Request failed. Try again.', true);
      }
    });
  }

  /* XBRDG loyalty form */
  const xbrdgForm = document.getElementById('xbrdg-form');
  const xbrdgMsg = document.getElementById('xbrdg-msg');

  if (xbrdgForm) {
    xbrdgForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const wallet = document.getElementById('xbrdg-wallet')?.value?.trim();
      if (!wallet) return;
      showMsg(xbrdgMsg, 'Checking wallet...');
      try {
        const r = await fetch(`${API_BASE}/keys/verify-xbrdg`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ wallet }),
        });
        const data = await r.json();
        if (data.eligible) {
          showMsg(xbrdgMsg, `Eligible! ${data.balance} $XBRDG detected. Your 20% discount code: ${data.coupon}`);
        } else {
          showMsg(xbrdgMsg, `${data.balance} $XBRDG found. Need ≥1,000 to qualify.`);
        }
      } catch {
        showMsg(xbrdgMsg, 'Request failed. Try again.', true);
      }
    });
  }

  /* Test console (usage-examples page) */
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
          'X-XAI-API-Key': key,
        },
        body: JSON.stringify({ test: name }),
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