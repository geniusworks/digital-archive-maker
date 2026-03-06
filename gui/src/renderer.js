/* renderer.js — UI logic for Digital Archive Maker */

// ── Navigation ────────────────────────────────────────────────────────────

function showView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const view = document.getElementById(`view-${name}`);
  if (view) view.classList.add('active');
  const nav = document.querySelector(`.nav-item[data-view="${name}"]`);
  if (nav) nav.classList.add('active');
}

document.querySelectorAll('.nav-item[data-view]').forEach(el => {
  el.addEventListener('click', () => showView(el.dataset.view));
});

document.querySelectorAll('.workflow-card[data-view]').forEach(el => {
  el.addEventListener('click', () => showView(el.dataset.view));
});

document.querySelectorAll('.alert-action[data-view]').forEach(el => {
  el.addEventListener('click', () => showView(el.dataset.view));
});

// ── Console panel ─────────────────────────────────────────────────────────

const consolePanel  = document.getElementById('console-panel');
const consoleOutput = document.getElementById('console-output');
const consoleToggle = document.getElementById('btn-toggle-console');
const consoleHeader = document.getElementById('console-header');
const btnKill       = document.getElementById('btn-kill');
const btnClear      = document.getElementById('btn-clear');
let   consoleCollapsed = false;

function toggleConsole() {
  consoleCollapsed = !consoleCollapsed;
  consolePanel.classList.toggle('collapsed', consoleCollapsed);
  consoleToggle.textContent = consoleCollapsed ? '▼' : '▲';
}

consoleHeader.addEventListener('click', (e) => {
  if (e.target.closest('button')) return;
  toggleConsole();
});
consoleToggle.addEventListener('click', (e) => {
  e.stopPropagation();
  toggleConsole();
});

btnClear.addEventListener('click', () => { consoleOutput.innerHTML = ''; });

btnKill.addEventListener('click', async () => {
  await window.dam.kill();
  appendOutput({ type: 'warning', text: '\nProcess stopped by user.\n' });
});

function appendOutput({ type, text }) {
  if (consoleCollapsed) toggleConsole();
  const span = document.createElement('span');
  span.textContent = text;
  if (type === 'command') span.className = 'out-command';
  else if (type === 'error' || type === 'stderr') span.className = 'out-error';
  else if (type === 'warning') span.className = 'out-warning';
  consoleOutput.appendChild(span);
  consoleOutput.scrollTop = consoleOutput.scrollHeight;
}

window.dam.onOutput(appendOutput);

window.dam.onProcessStart(() => {
  btnKill.classList.remove('hidden');
  setAllButtonsDisabled(true);
});

window.dam.onProcessEnd(({ code }) => {
  btnKill.classList.add('hidden');
  setAllButtonsDisabled(false);
  const msg = code === 0
    ? '\n✓ Completed successfully.\n'
    : `\n✗ Exited with code ${code}.\n`;
  appendOutput({ type: code === 0 ? 'success' : 'error', text: msg });
});

// ── Run a dam command ─────────────────────────────────────────────────────

async function runDam(args) {
  try {
    await window.dam.run(args);
  } catch (_) {
    // Errors already streamed to console
  }
}

// ── Disable/enable all action buttons while a process runs ────────────────

function setAllButtonsDisabled(disabled) {
  document.querySelectorAll('.btn-primary, .btn-sm').forEach(b => {
    b.disabled = disabled;
  });
}

// ── System status (sidebar pills) ─────────────────────────────────────────

async function refreshStatus() {
  const info = await window.dam.checkVenv();
  const venvPill = document.getElementById('status-venv');
  const envPill  = document.getElementById('status-env');
  const alert    = document.getElementById('setup-alert');
  const alertMsg = document.getElementById('setup-alert-msg');

  venvPill.className = `status-pill ${info.venvExists && info.damExists ? 'status-ok' : 'status-error'}`;
  envPill.className  = `status-pill ${info.envExists ? 'status-ok' : 'status-warn'}`;

  const issues = [];
  if (!info.venvExists || !info.damExists) {
    issues.push('Python venv or dam command not found — run: make install-deps && pip install -e .');
  }
  if (!info.envExists) {
    issues.push('.env config missing — run: cp .env.sample .env');
  }
  if (issues.length > 0) {
    alertMsg.textContent = ' ' + issues.join('  ·  ');
    alert.classList.remove('hidden');
  } else {
    alert.classList.add('hidden');
  }
}

// ── Settings: load & save ─────────────────────────────────────────────────

const envFieldMap = {
  'cfg-library-root':    'LIBRARY_ROOT',
  'cfg-lang-audio':      'HANDBRAKE_AUDIO_LANG',
  'cfg-lang-subtitles':  'HANDBRAKE_SUBTITLE_LANG',
  'cfg-acoustid':        'ACOUSTID_API_KEY',
  'cfg-genius':          'GENIUS_API_TOKEN',
  'cfg-spotify-id':      'SPOTIFY_CLIENT_ID',
  'cfg-spotify-secret':  'SPOTIFY_CLIENT_SECRET',
  'cfg-tmdb':            'TMDB_API_KEY',
  'cfg-omdb':            'OMDB_API_KEY',
};

async function loadSettings() {
  const env = await window.dam.readEnv();
  for (const [id, key] of Object.entries(envFieldMap)) {
    const el = document.getElementById(id);
    if (el && env[key] !== undefined) {
      const placeholder = key.includes('_KEY') || key.includes('_TOKEN') || key.includes('_SECRET');
      if (placeholder && env[key] && !env[key].includes('your_')) {
        el.value = env[key];
      } else if (!placeholder) {
        el.value = env[key] || '';
      }
    }
  }
}

document.getElementById('settings-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const updates = {};
  for (const [id, key] of Object.entries(envFieldMap)) {
    const el = document.getElementById(id);
    if (el && el.value.trim()) updates[key] = el.value.trim();
  }
  await window.dam.writeEnv(updates);
  const msg = document.getElementById('settings-saved-msg');
  msg.classList.remove('hidden');
  setTimeout(() => msg.classList.add('hidden'), 2500);
  await refreshStatus();
});

// ── Folder pickers ─────────────────────────────────────────────────────────

document.getElementById('btn-pick-library').addEventListener('click', async () => {
  const folder = await window.dam.pickFolder();
  if (folder) document.getElementById('cfg-library-root').value = folder;
});

document.getElementById('btn-pick-tag-path').addEventListener('click', async () => {
  const folder = await window.dam.pickFolder();
  if (folder) document.getElementById('tag-path').value = folder;
});

// ── API key signup links ──────────────────────────────────────────────────

document.querySelectorAll('[data-url]').forEach(el => {
  el.addEventListener('click', (e) => {
    e.preventDefault();
    window.dam.openUrl(el.dataset.url);
  });
});

// ── Rip: Video ────────────────────────────────────────────────────────────

document.getElementById('btn-rip-video').addEventListener('click', () => {
  const args = ['rip', 'video'];
  const title = document.getElementById('rip-title').value.trim();
  const year  = document.getElementById('rip-year').value.trim();
  const burn  = document.getElementById('rip-burn-subs').checked;
  if (title) args.push('--title', title);
  if (year)  args.push('--year', year);
  if (burn)  args.push('--burn-subs');
  runDam(args);
});

// ── Rip: CD button (uses data-command attr) ──────────────────────────────

document.querySelectorAll('[data-command]').forEach(btn => {
  try {
    const args = JSON.parse(btn.dataset.command);
    btn.addEventListener('click', () => runDam(args));
  } catch (_) {}
});

// ── Tag actions ───────────────────────────────────────────────────────────

document.querySelectorAll('[data-tag-command]').forEach(btn => {
  btn.addEventListener('click', () => {
    const sub = btn.dataset.tagCommand;
    const path = document.getElementById('tag-path').value.trim();
    const args = ['tag', sub];
    if (path) args.push(path);
    if (sub === 'explicit') {
      if (document.getElementById('tag-explicit-dry').checked) args.push('--dry-run');
    }
    if (sub === 'lyrics') {
      if (document.getElementById('tag-lyrics-recursive').checked) args.push('--recursive');
    }
    runDam(args);
  });
});

// ── Sync ──────────────────────────────────────────────────────────────────

document.getElementById('btn-sync').addEventListener('click', () => {
  const args = ['sync'];
  if (document.getElementById('sync-dry-run').checked) args.push('--dry-run');
  if (document.getElementById('sync-quiet').checked)   args.push('--quiet');
  runDam(args);
});

document.getElementById('btn-sync-dry').addEventListener('click', () => {
  runDam(['sync', '--dry-run']);
});

// ── System Check ──────────────────────────────────────────────────────────

document.getElementById('btn-check').addEventListener('click', () => {
  const scope = document.getElementById('check-scope').value;
  const args  = ['check'];
  if (scope) args.push(scope);
  runDam(args);
});

document.getElementById('btn-check-install').addEventListener('click', () => {
  const scope = document.getElementById('check-scope').value;
  const args  = ['check', '--install'];
  if (scope) args.push(scope);
  runDam(args);
});

// ── Init ──────────────────────────────────────────────────────────────────

(async () => {
  await refreshStatus();
  await loadSettings();
})();
