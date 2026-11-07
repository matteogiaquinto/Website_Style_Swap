/* Preview-only navigation. This file is not included in exported websites. */
(downloadUrl => {
  const host = document.createElement('div');
  host.setAttribute('data-restyle-preview-controls', '');
  host.style.cssText = 'all:initial!important;position:fixed!important;inset:0!important;z-index:2147483647!important;pointer-events:none!important;';
  const root = host.attachShadow({mode:'open'});
  const style = document.createElement('style');
  style.textContent = `
    :host { all: initial; }
    .action { position: fixed; bottom: max(20px, env(safe-area-inset-bottom)); pointer-events: auto; display: inline-flex; align-items: center; gap: 9px; min-height: 46px; padding: 10px 18px; border-radius: 999px; font: 600 14px/1.2 Inter, system-ui, -apple-system, sans-serif; text-decoration: none; box-sizing: border-box; box-shadow: 0 4px 18px rgba(0,0,0,.16); transition: background .15s, color .15s, border-color .15s; }
    .home { left: max(20px, env(safe-area-inset-left)); background: #fff; color: #1c1c1c; border: 1px solid #e4e1da; }
    .download { right: max(20px, env(safe-area-inset-right)); background: #111; color: #fff; border: 1px solid #111; }
    .action:hover { background: #facc15; color: #1a1500; border-color: #facc15; }
    .action:focus-visible { outline: 3px solid #8b5cf6; outline-offset: 3px; }
    svg { flex: none; width: 17px; height: 17px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
    @media (max-width: 420px) { .action { bottom: max(12px, env(safe-area-inset-bottom)); padding: 10px 14px; font-size: 13px; } .home { left: max(12px, env(safe-area-inset-left)); } .download { right: max(12px, env(safe-area-inset-right)); } }
    @media (prefers-reduced-motion: reduce) { .action { transition: none; } }
  `;
  const home = document.createElement('a');
  home.className = 'action home'; home.href = '/'; home.setAttribute('aria-label', "Return to Restyle home");
  home.innerHTML = '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M19 12H5m0 0 6-6m-6 6 6 6"/></svg><span>Accueil</span>';
  const download = document.createElement('a');
  download.className = 'action download'; download.href = downloadUrl; download.setAttribute('download', ''); download.setAttribute('aria-label', 'Download the final website');
  download.innerHTML = '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M12 3v12m0 0 4-4m-4 4-4-4M5 17v3h14v-3"/></svg><span>Download</span>';
  root.append(style, home, download);
  (document.body || document.documentElement).appendChild(host);
})(__RESTYLE_DOWNLOAD__);
