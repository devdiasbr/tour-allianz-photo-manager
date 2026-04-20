# UI Restyle — Console Operacional · Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir a UI atual (genérica, com emoji e verde neon) por um design system "console operacional" modular, com dark/light mode obrigatório, tipografia Bebas/Inter/Mono, ícones SVG, e detecção de rosto ao vivo na webcam via MediaPipe.

**Architecture:** Frontend estático (sem build) em `static/`. CSS separado em módulos por responsabilidade (`tokens/base/components/screens/overlays.css`). Theme via `[data-theme]` em `<html>` + custom properties. JS existente (`app.js`) preservado — novos módulos laterais (`theme.js`, `face-detection.js`) se integram sem tocar o core. Ícones via `<symbol>` sprite inline, servido pelo endpoint `/` do FastAPI.

**Tech Stack:** HTML/CSS/JS vanilla · FastAPI (serve estáticos) · Google Fonts (Bebas Neue, Inter, JetBrains Mono) · MediaPipe Face Detection (vendored) · pytest (contract tests).

**Spec:** [docs/superpowers/specs/2026-04-19-ui-restyle-console-design.md](../specs/2026-04-19-ui-restyle-console-design.md)

---

## File Structure

### Criar

- `static/styles/tokens.css` — custom properties dark/light
- `static/styles/base.css` — reset, body, fontes, utilities
- `static/styles/components.css` — status-bar, tabs, toolbar, btn, input, badge, photo-card, face-strip
- `static/styles/screens.css` — layouts específicos das 4 telas
- `static/styles/overlays.css` — loading, modal, snackbar
- `static/theme.js` — boot do tema + toggle handler
- `static/face-detection.js` — MediaPipe loop + bbox render
- `static/_icons.svg` — sprite `<svg><symbol>` reutilizável (servido como include no `/`)
- `static/vendor/mediapipe/` — `face_detection.js` + `.wasm` + modelo BlazeFace (offline-first)

### Modificar

- `static/index.html` — nova estrutura (status-bar + tabs + toolbars), todos os emoji removidos, `<link>`s dos módulos, `<script>` theme.js + face-detection.js. IDs/handlers preservados.
- `server.py` — endpoint `/` inlineia `static/_icons.svg` no HTML servido (uma única request, zero flash).
- `tests/test_loading_component_contract.py` — ajusta os assertions para ler de `static/index.html` (estrutura ARIA do overlay) **e** `static/app.js` (API da classe). Remove assertions sobre classes `.loading-size-*` / `.loading-color-*` que não existem mais — o overlay novo é único, minimalista.

### Deletar

- `static/style.css` — substituído pelos módulos em `static/styles/`.

---

## Task 1: Scaffold modular CSS + theme boot

Monta o esqueleto vazio dos arquivos CSS e o `theme.js` funcionando end-to-end (toggle visível, persistência). Todas as telas continuam com o estilo antigo até a Task 2+.

**Files:**
- Create: `static/styles/tokens.css`
- Create: `static/styles/base.css`
- Create: `static/styles/components.css` (placeholder vazio)
- Create: `static/styles/screens.css` (placeholder vazio)
- Create: `static/styles/overlays.css` (placeholder vazio)
- Create: `static/theme.js`
- Modify: `static/index.html` (adicionar links, theme.js antes de app.js, `<html data-theme="dark">` default, botão toggle com id `themeToggle`)

- [ ] **Step 1.1: Criar `static/styles/tokens.css`**

```css
:root {
  --radius: 2px;
  --space-1: 4px; --space-2: 8px; --space-3: 12px;
  --space-4: 16px; --space-6: 24px; --space-8: 32px; --space-12: 48px;
}

[data-theme="dark"] {
  --bg: #0c0c0c;        --surface: #131313;       --surface-2: #1a1a1a;
  --border: #1f1f1f;    --border-strong: #2a2a2a;
  --text: #d6d6d6;      --text-strong: #ffffff;
  --text-dim: #5a5a5a;  --text-fade: #4a4a4a;
  --brand: #006437;     --brand-hover: #007a44;   --brand-tint: rgba(0,100,55,.12);
  --danger: #c75050;    --danger-bg: #1a0f0f;     --warn: #c4a017;
}

[data-theme="light"] {
  --bg: #fafaf9;        --surface: #ffffff;       --surface-2: #f5f5f4;
  --border: #ececea;    --border-strong: #d4d4d2;
  --text: #27272a;      --text-strong: #09090b;
  --text-dim: #71717a;  --text-fade: #a1a1aa;
  --brand: #006437;     --brand-hover: #005530;   --brand-tint: rgba(0,100,55,.08);
  --danger: #b91c1c;    --danger-bg: #fef2f2;     --warn: #a16207;
}
```

- [ ] **Step 1.2: Criar `static/styles/base.css`**

```css
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  background: var(--bg); color: var(--text);
  font-family: 'Inter', system-ui, sans-serif; font-size: 13px; line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}
button, input, select, textarea { font-family: inherit; font-size: inherit; color: inherit; }
button { cursor: pointer; border: 0; background: transparent; padding: 0; }
.hidden { display: none !important; }
.mono { font-family: 'JetBrains Mono', ui-monospace, monospace; }
.label { font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 500; letter-spacing: .12em; text-transform: uppercase; color: var(--text-dim); }
.data { font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 500; }
```

- [ ] **Step 1.3: Criar `static/styles/components.css`, `screens.css`, `overlays.css` vazios**

Cada um começa com um comentário de uma linha: `/* componentes | telas | overlays */`. Serão preenchidos nas próximas tasks.

- [ ] **Step 1.4: Criar `static/theme.js`**

```js
(function () {
  const KEY = 'theme';
  const root = document.documentElement;

  function apply(theme) {
    root.dataset.theme = theme;
    const btn = document.getElementById('themeToggle');
    if (btn) btn.dataset.theme = theme;
  }

  function detect() {
    const saved = localStorage.getItem(KEY);
    if (saved === 'dark' || saved === 'light') return saved;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }

  apply(detect());

  document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('themeToggle');
    if (!btn) return;
    btn.addEventListener('click', () => {
      const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
      localStorage.setItem(KEY, next);
      apply(next);
    });
  });

  window.__theme = { apply, detect };
})();
```

- [ ] **Step 1.5: Atualizar `static/index.html` — head e wiring do toggle**

Substituir o `<link rel="stylesheet" href="/static/style.css">` por:

```html
<link rel="stylesheet" href="/static/styles/tokens.css">
<link rel="stylesheet" href="/static/styles/base.css">
<link rel="stylesheet" href="/static/styles/components.css">
<link rel="stylesheet" href="/static/styles/screens.css">
<link rel="stylesheet" href="/static/styles/overlays.css">
<script src="/static/theme.js"></script>
```

`theme.js` precisa rodar **antes** do `<body>` pra evitar flash de tema errado. Adicionar um placeholder no topo do body:

```html
<button id="themeToggle" title="Alternar tema" style="position:fixed;top:12px;right:12px;z-index:100;padding:6px 10px;font-family:monospace;font-size:11px">theme</button>
```

(É só provisório — a Task 3 move pra status-bar real.)

- [ ] **Step 1.6: Verificação manual no browser**

Rodar `uvicorn server:app --reload` (ou reutilizar o server já rodando). Abrir `http://127.0.0.1:8000`. Confirmar:

1. Página carrega sem erro no console.
2. Botão `theme` no canto superior direito alterna entre dark (bg #0c0c0c) e light (bg #fafaf9).
3. Hard refresh (Ctrl+Shift+R) preserva a escolha.
4. Em aba anônima sem preferência salva: se OS estiver em light mode, app abre em light; dark mode, abre em dark.

Expected: toggle funciona, persiste, respeita `prefers-color-scheme` na primeira visita.

- [ ] **Step 1.7: Commit**

```bash
git add static/styles/ static/theme.js static/index.html
git commit -m "feat(ui): scaffold modular CSS + theme toggle (dark/light)"
```

---

## Task 2: SVG icon sprite + server-side include

Cria o sprite com os 15 ícones do inventário. `server.py` passa a inlinear o sprite no endpoint `/`, evitando fetch extra e flash.

**Files:**
- Create: `static/_icons.svg`
- Modify: `server.py` — endpoint que serve `/` (já existente, vamos localizar)
- Modify: `static/index.html` (placeholder `<!--ICONS-->` onde o sprite é injetado)

- [ ] **Step 2.1: Criar `static/_icons.svg`** com todos os 15 ícones

Todos em `viewBox="0 0 24 24"`, `stroke-width="1.5"`, `fill="none"`, `stroke="currentColor"`, `stroke-linecap="round"`, `stroke-linejoin="round"`. Lista: `camera`, `search`, `folder`, `add`, `check`, `close`, `print`, `save`, `arrow-left`, `arrow-right`, `trash`, `upload`, `sun`, `moon`, `rotate`.

Template (estrutura — use paths do Lucide em cada `<symbol>`):

```html
<svg xmlns="http://www.w3.org/2000/svg" style="display:none" aria-hidden="true">
  <symbol id="i-camera" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3Z"/>
    <circle cx="12" cy="13" r="4"/>
  </symbol>
  <symbol id="i-search" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="11" cy="11" r="7"/><path d="m20 20-4.3-4.3"/>
  </symbol>
  <symbol id="i-folder" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>
  </symbol>
  <symbol id="i-add" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M12 5v14M5 12h14"/>
  </symbol>
  <symbol id="i-check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M20 6 9 17l-5-5"/>
  </symbol>
  <symbol id="i-close" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M18 6 6 18M6 6l12 12"/>
  </symbol>
  <symbol id="i-print" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>
    <rect x="6" y="14" width="12" height="8"/>
  </symbol>
  <symbol id="i-save" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2Z"/>
    <path d="M17 21v-8H7v8M7 3v5h8"/>
  </symbol>
  <symbol id="i-arrow-left" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M19 12H5M12 19l-7-7 7-7"/>
  </symbol>
  <symbol id="i-arrow-right" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M5 12h14M12 5l7 7-7 7"/>
  </symbol>
  <symbol id="i-trash" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/>
  </symbol>
  <symbol id="i-upload" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
  </symbol>
  <symbol id="i-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="12" r="4"/>
    <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/>
  </symbol>
  <symbol id="i-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z"/>
  </symbol>
  <symbol id="i-rotate" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M21 12a9 9 0 1 1-3-6.7L21 8M21 3v5h-5"/>
  </symbol>
</svg>
```

- [ ] **Step 2.2: Localizar o endpoint `/` em `server.py`**

Run: `grep -n 'FileResponse\|HTMLResponse\|@app.get("/")' server.py`
Expected: Identificar a rota que serve `static/index.html` (provavelmente `FileResponse("static/index.html")`).

- [ ] **Step 2.3: Substituir o endpoint `/` por uma função que injeta o sprite**

Pattern de substituição (adapte à assinatura existente; normalmente é `@app.get("/")`):

```python
from fastapi.responses import HTMLResponse
from pathlib import Path

STATIC_DIR = Path(__file__).parent / "static"
_INDEX_CACHE = {"html": None, "mtime": 0}

@app.get("/", response_class=HTMLResponse)
def root():
    idx = STATIC_DIR / "index.html"
    icons = STATIC_DIR / "_icons.svg"
    mtime = max(idx.stat().st_mtime, icons.stat().st_mtime)
    if _INDEX_CACHE["html"] is None or _INDEX_CACHE["mtime"] != mtime:
        html = idx.read_text(encoding="utf-8")
        svg = icons.read_text(encoding="utf-8")
        _INDEX_CACHE["html"] = html.replace("<!--ICONS-->", svg)
        _INDEX_CACHE["mtime"] = mtime
    return HTMLResponse(_INDEX_CACHE["html"])
```

Remove o handler antigo `FileResponse("static/index.html")` pra não haver duplicata.

- [ ] **Step 2.4: Adicionar o placeholder `<!--ICONS-->` em `static/index.html`**

Logo após `<body>`:

```html
<body>
  <!--ICONS-->
  ...
```

- [ ] **Step 2.5: Verificação manual no browser**

Refresh. DevTools → Elements → checar que o `<body>` tem um `<svg style="display:none">` como primeiro filho com 15 `<symbol>` dentro. No Console:

```js
document.querySelector('#i-sun')
```

Expected: retorna o `<symbol>`, não `null`.

- [ ] **Step 2.6: Commit**

```bash
git add static/_icons.svg server.py static/index.html
git commit -m "feat(ui): SVG icon sprite inlined via FastAPI root endpoint"
```

---

## Task 3: Status bar + tabs (navegação)

Substitui o header atual (emoji ⚽ + h1 + subtitle) por status-bar com wordmark "TOUR ALLIANZ" em Bebas Neue, metadata da sessão ao centro, e theme toggle à direita. Substitui o stepper de pílulas por tabs horizontais.

**Files:**
- Modify: `static/styles/components.css` (adicionar estilos)
- Modify: `static/index.html` (substituir `.header` e `.stepper`)
- Modify: `static/app.js` (novo helper `updateStatusBar()` — não mexe em handlers existentes)

- [ ] **Step 3.1: Adicionar estilos da status-bar em `components.css`**

```css
/* ===== status bar ===== */
.statusbar {
  display: grid; grid-template-columns: auto 1fr auto auto;
  align-items: center; gap: var(--space-4);
  height: 44px; padding: 0 var(--space-4);
  background: var(--surface); border-bottom: 1px solid var(--border);
  position: sticky; top: 0; z-index: 40;
}
.statusbar .wordmark {
  display: flex; align-items: center; gap: 10px;
  font-family: 'Bebas Neue', sans-serif; font-size: 18px; letter-spacing: .08em;
  color: var(--text-strong);
}
.statusbar .wordmark::before {
  content: ''; display: block; width: 3px; height: 18px; background: var(--brand);
}
.statusbar .meta {
  display: flex; gap: var(--space-4);
  font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--text-dim);
  letter-spacing: .04em;
}
.statusbar .meta span b { color: var(--text); font-weight: 500; }
.statusbar .meta .live { color: var(--brand); }
.statusbar .meta .live::before {
  content: '●'; margin-right: 4px;
  animation: livepulse 1.2s ease-in-out infinite;
}
@keyframes livepulse { 50% { opacity: .3; } }
.statusbar .version {
  font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--text-fade);
}
.statusbar .theme-toggle {
  width: 28px; height: 28px; display: grid; place-items: center;
  border: 1px solid var(--border-strong); border-radius: var(--radius);
  background: transparent; color: var(--text-dim);
}
.statusbar .theme-toggle:hover { color: var(--text-strong); border-color: var(--text-dim); }
.statusbar .theme-toggle svg { width: 14px; height: 14px; }
.statusbar .theme-toggle .i-sun { display: block; }
.statusbar .theme-toggle .i-moon { display: none; }
[data-theme="light"] .statusbar .theme-toggle .i-sun { display: none; }
[data-theme="light"] .statusbar .theme-toggle .i-moon { display: block; }
```

- [ ] **Step 3.2: Adicionar estilos de tabs em `components.css`**

```css
/* ===== tabs ===== */
.tabs {
  display: flex; gap: 0;
  background: var(--bg); border-bottom: 1px solid var(--border);
  padding: 0 var(--space-4);
}
.tab {
  display: flex; align-items: center; gap: 8px;
  padding: 12px var(--space-4); font-family: 'Inter';
  font-size: 11px; font-weight: 500; letter-spacing: .12em; text-transform: uppercase;
  color: var(--text-dim); border-bottom: 1px solid transparent;
  margin-bottom: -1px; cursor: pointer;
}
.tab .n {
  font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--brand);
  letter-spacing: 0;
}
.tab:hover { color: var(--text); }
.tab.active {
  color: var(--text-strong); border-bottom-color: var(--text-strong);
}
.tab.done .n { display: none; }
.tab.done::before {
  content: ''; width: 10px; height: 10px;
  background: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23006437' stroke-width='2.5'><path d='M20 6 9 17l-5-5'/></svg>") no-repeat center/contain;
}
```

- [ ] **Step 3.3: Substituir o header antigo em `static/index.html`**

Remover `<div class="header">...</div>` e `<div class="stepper">...</div>`. No lugar:

```html
<header class="statusbar">
  <div class="wordmark">TOUR ALLIANZ</div>
  <div class="meta" id="sessionMeta">
    <span>sessão <b id="metaSession">—</b></span>
    <span>fotos <b id="metaPhotos">0</b></span>
    <span id="metaScan" class="live hidden">scan <b>0/0</b></span>
    <span id="metaMatches"><b>0</b> matches</span>
  </div>
  <div class="version">v1.0</div>
  <button id="themeToggle" class="theme-toggle" title="Alternar tema" aria-label="Alternar tema">
    <svg class="i-sun"><use href="#i-sun"/></svg>
    <svg class="i-moon"><use href="#i-moon"/></svg>
  </button>
</header>

<nav class="tabs">
  <div class="tab active" data-step="0" onclick="goToStep(0)"><span class="n">01</span>SESSÃO</div>
  <div class="tab" data-step="1" onclick="goToStep(1)"><span class="n">02</span>CAPTURA</div>
  <div class="tab" data-step="2" onclick="goToStep(2)"><span class="n">03</span>FOTOS</div>
  <div class="tab" data-step="3" onclick="goToStep(3)"><span class="n">04</span>IMPRIMIR</div>
</nav>
```

Remover também o placeholder `<button id="themeToggle">` provisório da Task 1.5.

- [ ] **Step 3.4: Atualizar `goToStep` em `static/app.js` para sincronizar as tabs**

Localizar `function goToStep(step)` (~linha 110). Manter comportamento atual (mostrar/esconder `.content`) e adicionar sync das tabs:

```js
// dentro de goToStep(step), após determinar que a mudança é válida:
document.querySelectorAll('.tab').forEach(t => {
  const n = Number(t.dataset.step);
  t.classList.toggle('active', n === step);
  t.classList.toggle('done', n < step);
});
```

Remover qualquer código que tocava `.step.active / .step.inactive` (classes do stepper antigo).

- [ ] **Step 3.5: Adicionar helper `updateStatusBar` em `app.js`**

No final do arquivo, antes do event listener de inicialização:

```js
function updateStatusBar({ session, photos, scanCur, scanTot, matches } = {}) {
  const el = id => document.getElementById(id);
  if (session !== undefined) el('metaSession').textContent = session || '—';
  if (photos !== undefined) el('metaPhotos').textContent = photos;
  if (matches !== undefined) el('metaMatches').querySelector('b').textContent = matches;
  const scan = el('metaScan');
  if (scanCur !== undefined && scanTot !== undefined && scanTot > 0) {
    scan.querySelector('b').textContent = `${scanCur}/${scanTot}`;
    scan.classList.remove('hidden');
  } else if (scanCur === null) {
    scan.classList.add('hidden');
  }
}
window.updateStatusBar = updateStatusBar;
```

Em `confirmFolder` (linha ~209), após obter `sessionPath` e `sessionPhotoCount`, chamar:
```js
updateStatusBar({ session: sessionPath.split(/[\\/]/).pop(), photos: sessionPhotoCount });
```

- [ ] **Step 3.6: Verificação manual no browser**

Refresh. Confirmar:

1. Topo agora mostra barra fina com "TOUR ALLIANZ" em Bebas + metadata mono + botão de tema (14px).
2. Tabs abaixo: `01 SESSÃO` ativa (texto branco + sublinhado), outras dim.
3. Clicar numa tab muda de tela e atualiza visual (ativa/done) corretamente.
4. Toggle sol/lua: dark mostra ícone de **sol** (clique vai pra light), light mostra **lua**.
5. Selecionar uma pasta (`goToStep(1)`): metadata mostra o nome da pasta + contador.

Expected: tudo visualmente consistente nos 2 temas, sem bordas sumindo em light.

- [ ] **Step 3.7: Commit**

```bash
git add static/styles/components.css static/index.html static/app.js
git commit -m "feat(ui): status bar with wordmark + horizontal tabs replace stepper"
```

---

## Task 4: Sistema de botões (4 variantes × 3 tamanhos)

Remove `.btn-green / .btn-blue / .btn-gray` e substitui por sistema semântico: `primary / secondary / ghost / danger` × tamanhos `sm / md / lg`. Ícones SVG em todos.

**Files:**
- Modify: `static/styles/components.css`
- Modify: `static/index.html` (trocar classes e substituir emoji por `<svg><use>`)

- [ ] **Step 4.1: Adicionar sistema de botões em `components.css`**

```css
/* ===== buttons ===== */
.btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 9px 14px; font-family: 'Inter'; font-size: 12px; font-weight: 500;
  border: 1px solid transparent; border-radius: var(--radius);
  background: transparent; color: var(--text);
  transition: background .1s, border-color .1s, color .1s;
  white-space: nowrap;
}
.btn svg { width: 14px; height: 14px; flex-shrink: 0; }
.btn:hover:not(:disabled) { background: var(--surface-2); }
.btn:disabled { opacity: .35; cursor: not-allowed; }

.btn-primary { background: var(--brand); color: #fff; border-color: var(--brand); }
.btn-primary:hover:not(:disabled) { background: var(--brand-hover); border-color: var(--brand-hover); }

.btn-secondary { border-color: var(--border-strong); color: var(--text); }
.btn-secondary:hover:not(:disabled) { border-color: var(--text-dim); background: var(--surface); }

.btn-ghost { color: var(--text-dim); }
.btn-ghost:hover:not(:disabled) { color: var(--text); }

.btn-danger { color: var(--danger); border-color: var(--border-strong); }
.btn-danger:hover:not(:disabled) { background: var(--danger-bg); border-color: var(--danger); }

.btn-sm { padding: 6px 10px; font-size: 11px; }
.btn-sm svg { width: 12px; height: 12px; }
.btn-lg { padding: 12px 18px; font-size: 13px; }
.btn-lg svg { width: 16px; height: 16px; }
.btn-icon-only { padding: 8px; }
```

- [ ] **Step 4.2: Substituir todos os botões nas 4 telas do `static/index.html`**

Step 0:
```html
<button class="btn btn-secondary" onclick="browseFolder()">
  <svg><use href="#i-folder"/></svg>Procurar
</button>
<input type="text" id="pathInput" class="input input-mono"
       placeholder="/caminho/para/sessão"
       onkeydown="if(event.key==='Enter') confirmFolder()">
<button class="btn btn-primary" onclick="confirmFolder()">
  <svg><use href="#i-arrow-right"/></svg>Confirmar
</button>
```

Step 1 (webcam-controls):
```html
<button class="btn btn-primary" id="btnCapture" onclick="captureFrame()">
  <svg><use href="#i-camera"/></svg>Capturar rosto
</button>
<label class="btn btn-secondary" style="cursor:pointer">
  <svg><use href="#i-upload"/></svg>Enviar foto
  <input type="file" id="fileUpload" accept="image/*" multiple
         onchange="uploadPhotos(this.files)" style="display:none">
</label>
<button class="btn btn-ghost" onclick="clearFaces()">
  <svg><use href="#i-trash"/></svg>Limpar rostos
</button>
```

(`btnCapture` começa habilitado. Só a Task 8, quando integra MediaPipe, passa a gatear `disabled` via JS baseado em detecção. Entre Task 4 e Task 8 o botão captura livremente — comportamento atual.)

Step 1 (botão de busca):
```html
<button class="btn btn-primary btn-lg" onclick="startSearch()" id="btnSearch" disabled>
  <svg><use href="#i-search"/></svg>Buscar fotos
</button>
```

Step 2 (toolbar):
```html
<div class="toolbar">
  <button class="btn btn-ghost" onclick="goToStep(1)">
    <svg><use href="#i-arrow-left"/></svg>Voltar
  </button>
  <div class="sep"></div>
  <button class="btn btn-secondary" onclick="toggleSelectAll()">
    <svg><use href="#i-check"/></svg>Selecionar todas
  </button>
  <div class="spacer"></div>
  <span class="data" id="selectionCount">0 selecionadas</span>
  <button class="btn btn-primary" onclick="composeSelected()">
    <svg><use href="#i-print"/></svg>Compor e imprimir
  </button>
</div>
```

Step 3 (toolbar):
```html
<div class="toolbar">
  <button class="btn btn-ghost" onclick="goToStep(2)">
    <svg><use href="#i-arrow-left"/></svg>Voltar
  </button>
  <div class="sep"></div>
  <button class="btn btn-secondary" onclick="saveAll()">
    <svg><use href="#i-save"/></svg>Salvar todas
  </button>
  <button class="btn btn-secondary" onclick="goToStep(0)">
    <svg><use href="#i-rotate"/></svg>Nova busca
  </button>
  <div class="spacer"></div>
  <span class="data" id="composedCount">0 compostas</span>
  <button class="btn btn-primary" onclick="printAll()">
    <svg><use href="#i-print"/></svg>Imprimir todas
  </button>
</div>
```

Remover todos os emoji (📂📷🗑🔍🖨💾🔄✓←) completamente.

- [ ] **Step 4.3: Verificação manual no browser**

1. Zero emoji visível em qualquer tela.
2. Em cada tela: no máximo um botão `.btn-primary` (verde sólido).
3. Hover: primary escurece, secondary ganha borda forte, ghost ganha cor forte, danger fica com fundo vermelho claro.
4. Em light mode: contraste legível, verde visível, vermelho não muito agressivo.

- [ ] **Step 4.4: Commit**

```bash
git add static/styles/components.css static/index.html
git commit -m "feat(ui): semantic button system (primary/secondary/ghost/danger)"
```

---

## Task 5: Inputs + toolbar + badges

Estilos dos inputs monospace, do `.toolbar / .sep / .spacer` usados nas telas 2/3, e do sistema de badges.

**Files:**
- Modify: `static/styles/components.css`

- [ ] **Step 5.1: Adicionar inputs em `components.css`**

```css
/* ===== inputs ===== */
.input {
  background: var(--bg); color: var(--text);
  border: 1px solid var(--border-strong); border-radius: var(--radius);
  padding: 9px 12px; font-size: 12px;
  transition: border-color .1s;
}
.input:focus { outline: none; border-color: var(--brand); }
.input::placeholder { color: var(--text-fade); }
.input-mono { font-family: 'JetBrains Mono', monospace; }
.input-wrap { position: relative; display: inline-flex; flex: 1; }
.input-wrap svg.lead { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); width: 14px; height: 14px; color: var(--text-dim); pointer-events: none; }
.input-wrap .input { padding-left: 32px; flex: 1; }
```

- [ ] **Step 5.2: Adicionar toolbar + badges em `components.css`**

```css
/* ===== toolbar ===== */
.toolbar {
  display: flex; align-items: center; gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background: var(--surface); border-bottom: 1px solid var(--border);
}
.toolbar .sep { width: 1px; height: 16px; background: var(--border); margin: 0 var(--space-2); }
.toolbar .spacer { flex: 1; }
.toolbar .data { color: var(--text-dim); font-size: 11px; }
.toolbar .data b { color: var(--brand); font-weight: 500; }

/* ===== badges ===== */
.badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 6px; font-family: 'JetBrains Mono', monospace;
  font-size: 10px; font-weight: 500; letter-spacing: .1em; text-transform: uppercase;
  border: 1px solid currentColor; border-radius: var(--radius);
  background: transparent;
}
.badge-match { color: var(--brand); }
.badge-warn { color: var(--warn); }
.badge-danger { color: var(--danger); }
.badge-info { color: var(--text-dim); }
.badge-solid { background: var(--brand); color: #fff; border-color: var(--brand); }
```

- [ ] **Step 5.3: Verificação manual no browser**

1. Input em step 0 mostra placeholder em mono, fica verde no focus.
2. Toolbar em step 2/3 tem separador 1px e spacer empurra o primary pra direita.
3. (Badges ainda não renderizados — serão usados na Task 6.)

- [ ] **Step 5.4: Commit**

```bash
git add static/styles/components.css
git commit -m "feat(ui): input, toolbar, and badge components"
```

---

## Task 6: Photo card + face strip + screen layouts

Redesenha as 4 telas completas: folder picker, webcam, photo grid, print preview.

**Files:**
- Modify: `static/styles/screens.css`
- Modify: `static/styles/components.css` (photo-card, face-strip)
- Modify: `static/index.html` (mudar markup interno dos 4 `<div id="stepN">`)
- Modify: `static/app.js` (renderers de photo card e face chip)

- [ ] **Step 6.1: Adicionar `.photo-card` e `.face-strip` em `components.css`**

```css
/* ===== photo card ===== */
.photo-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); overflow: hidden; position: relative;
  transition: border-color .1s;
  display: flex; flex-direction: column;
}
.photo-card:hover { border-color: var(--border-strong); }
.photo-card .img-wrap { aspect-ratio: 4/3; background: var(--surface-2); position: relative; overflow: hidden; }
.photo-card img { width: 100%; height: 100%; object-fit: cover; display: block; }
.photo-card .meta {
  display: flex; justify-content: space-between; align-items: center; gap: 8px;
  padding: 8px 10px; font-family: 'JetBrains Mono', monospace; font-size: 11px;
}
.photo-card .fname { color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.photo-card .pct { color: var(--text-dim); }

.photo-card.match { border-left: 2px solid var(--brand); }
.photo-card.match .pct { color: var(--brand); }
.photo-card.match .img-wrap::before {
  content: 'MATCH'; position: absolute; top: 6px; left: 6px; z-index: 2;
  font-family: 'JetBrains Mono', monospace; font-size: 9px; letter-spacing: .1em;
  padding: 2px 5px; background: var(--brand); color: #fff;
}

.photo-card.selected {
  outline: 1px solid var(--brand); box-shadow: inset 0 0 0 1px var(--brand);
}
.photo-card .check {
  position: absolute; top: 6px; right: 6px; z-index: 2;
  width: 18px; height: 18px; border: 1px solid var(--border-strong);
  background: var(--surface); border-radius: var(--radius);
  display: grid; place-items: center;
}
.photo-card.selected .check {
  background: var(--brand); border-color: var(--brand);
}
.photo-card.selected .check::after {
  content: ''; width: 10px; height: 10px;
  background: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='3'><path d='M20 6 9 17l-5-5'/></svg>") no-repeat center/contain;
}

/* ===== face strip ===== */
.face-strip {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px;
}
.face-chip {
  aspect-ratio: 1; background: var(--surface-2);
  border: 1px solid var(--border-strong); position: relative; overflow: hidden;
}
.face-chip img { width: 100%; height: 100%; object-fit: cover; }
.face-chip .rm {
  position: absolute; top: 2px; right: 2px;
  width: 14px; height: 14px; border-radius: 50%;
  background: var(--danger); color: #fff;
  font-size: 10px; display: none; place-items: center; cursor: pointer;
}
.face-chip:hover .rm { display: grid; }
```

- [ ] **Step 6.2: Adicionar layouts das 4 telas em `screens.css`**

```css
/* ===== step 0 · folder picker ===== */
#step0 { padding: 36px 60px; max-width: 720px; margin: 0 auto; }
#step0 h1 { font-family: 'Inter'; font-size: 22px; font-weight: 600; color: var(--text-strong); margin: 0 0 6px; }
#step0 .subtitle { font-size: 13px; color: var(--text-dim); margin: 0 0 var(--space-6); }
#step0 .path-row { display: flex; gap: var(--space-2); margin-bottom: var(--space-4); }
#step0 .path-row .input-wrap { flex: 1; }
#step0 .recent-title { margin: var(--space-8) 0 var(--space-2); }
.recent-list { border: 1px solid var(--border); border-radius: var(--radius); }
.recent-row {
  display: grid; grid-template-columns: 1fr auto auto; gap: var(--space-4);
  padding: 8px 12px; font-family: 'JetBrains Mono', monospace; font-size: 12px;
  border-bottom: 1px solid var(--border); cursor: pointer;
}
.recent-row:last-child { border-bottom: 0; }
.recent-row:hover { background: var(--surface); }
.recent-row .path { color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.recent-row .count { color: var(--brand); }
.recent-row .when { color: var(--text-dim); font-size: 11px; }

/* ===== step 1 · webcam ===== */
#step1 { display: grid; grid-template-columns: 1fr 280px; gap: var(--space-4); padding: var(--space-4); }
#step1 .cam-col { background: var(--surface); border: 1px solid var(--border); padding: var(--space-4); }
#step1 .video-wrapper { aspect-ratio: 4/3; background: #000; position: relative; overflow: hidden; }
#step1 video { width: 100%; height: 100%; object-fit: cover; }
#step1 canvas { display: none; }
#step1 .cam-actions { display: flex; gap: var(--space-2); margin-top: var(--space-3); flex-wrap: wrap; }
#step1 .side-col { background: var(--surface); border: 1px solid var(--border); padding: var(--space-4); display: flex; flex-direction: column; gap: var(--space-3); }
#step1 .side-col h2 { font-family: 'JetBrains Mono', monospace; font-size: 10px; letter-spacing: .12em; color: var(--text-dim); text-transform: uppercase; margin: 0 0 var(--space-2); font-weight: 500; display: flex; justify-content: space-between; }
#step1 .side-col h2 .n { color: var(--brand); font-family: 'JetBrains Mono'; }
#step1 .divider { height: 1px; background: var(--border); margin: var(--space-2) 0; }
#step1 .side-actions { display: flex; flex-direction: column; gap: var(--space-2); }

/* ===== step 2 · grid ===== */
#step2 { padding: 0; }
.scan-bar {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-2) var(--space-4); background: var(--surface-2);
  border-bottom: 1px solid var(--border);
  font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--text-dim);
}
.scan-bar .bar { flex: 1; height: 2px; background: var(--border-strong); overflow: hidden; }
.scan-bar .fill { height: 100%; background: var(--brand); transition: width .2s; }
.scan-bar .match { color: var(--brand); }
.photo-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--space-3); padding: var(--space-4);
}

/* ===== step 3 · print preview ===== */
#step3 { padding: 0; }
.preview-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-4); padding: var(--space-4);
}
.preview-grid .photo-card .img-wrap { aspect-ratio: 3/2; }
```

- [ ] **Step 6.3: Substituir markup do Step 0 em `static/index.html`**

```html
<div id="step0" class="content">
  <h1>Pasta da sessão</h1>
  <p class="subtitle">Selecione o diretório com as fotos capturadas no evento.</p>
  <div class="path-row">
    <button class="btn btn-secondary" onclick="browseFolder()">
      <svg><use href="#i-folder"/></svg>Procurar
    </button>
    <span class="input-wrap">
      <svg class="lead"><use href="#i-folder"/></svg>
      <input type="text" id="pathInput" class="input input-mono"
             placeholder="/caminho/para/sessão"
             onkeydown="if(event.key==='Enter') confirmFolder()">
    </span>
    <button class="btn btn-primary" onclick="confirmFolder()">
      <svg><use href="#i-arrow-right"/></svg>Confirmar
    </button>
  </div>
  <div id="pathInfo" class="mono" style="font-size:11px;color:var(--text-dim);margin-bottom:var(--space-6)"></div>
  <div id="recentSection" class="hidden">
    <div class="label recent-title">Pastas recentes</div>
    <div id="recentList" class="recent-list"></div>
  </div>
</div>
```

- [ ] **Step 6.4: Substituir markup do Step 1 em `static/index.html`**

```html
<div id="step1" class="content hidden">
  <div class="cam-col">
    <div class="video-wrapper" id="videoWrap">
      <video id="webcam" autoplay playsinline muted></video>
      <canvas id="captureCanvas"></canvas>
      <!-- Task 8 injeta overlay de bbox aqui -->
    </div>
    <div class="cam-actions">
      <button class="btn btn-primary" id="btnCapture" onclick="captureFrame()">
        <svg><use href="#i-camera"/></svg>Capturar rosto
      </button>
      <label class="btn btn-secondary" style="cursor:pointer">
        <svg><use href="#i-upload"/></svg>Enviar foto
        <input type="file" id="fileUpload" accept="image/*" multiple
               onchange="uploadPhotos(this.files)" style="display:none">
      </label>
    </div>
  </div>
  <aside class="side-col">
    <h2>Rostos de referência <span class="n" id="faceCount">0</span></h2>
    <div id="capturedFaces" class="face-strip"></div>
    <div class="divider"></div>
    <h2>Ações</h2>
    <div class="side-actions">
      <button class="btn btn-primary btn-lg" onclick="startSearch()" id="btnSearch" disabled>
        <svg><use href="#i-search"/></svg>Buscar fotos
      </button>
      <button class="btn btn-danger" onclick="clearFaces()">
        <svg><use href="#i-trash"/></svg>Limpar todos
      </button>
    </div>
  </aside>
</div>
```

- [ ] **Step 6.5: Substituir markup dos Steps 2 e 3 em `static/index.html`**

Step 2:
```html
<div id="step2" class="content hidden">
  <div class="toolbar">
    <button class="btn btn-ghost" onclick="goToStep(1)">
      <svg><use href="#i-arrow-left"/></svg>Voltar
    </button>
    <div class="sep"></div>
    <button class="btn btn-secondary" onclick="toggleSelectAll()">
      <svg><use href="#i-check"/></svg>Selecionar todas
    </button>
    <div class="spacer"></div>
    <span class="data"><b id="selectionCount">0</b> selecionadas</span>
    <button class="btn btn-primary" onclick="composeSelected()">
      <svg><use href="#i-print"/></svg>Compor e imprimir
    </button>
  </div>
  <div class="scan-bar hidden" id="scanProgress">
    <span>scanning <b id="scanText">0/0</b></span>
    <div class="bar"><div class="fill" id="scanFill" style="width:0%"></div></div>
    <span class="match">match <b id="scanMatches">0</b></span>
  </div>
  <div id="photoGrid" class="photo-grid"></div>
</div>
```

Step 3:
```html
<div id="step3" class="content hidden">
  <div class="toolbar">
    <button class="btn btn-ghost" onclick="goToStep(2)">
      <svg><use href="#i-arrow-left"/></svg>Voltar
    </button>
    <div class="sep"></div>
    <button class="btn btn-secondary" onclick="saveAll()">
      <svg><use href="#i-save"/></svg>Salvar todas
    </button>
    <button class="btn btn-secondary" onclick="goToStep(0)">
      <svg><use href="#i-rotate"/></svg>Nova busca
    </button>
    <div class="spacer"></div>
    <span class="data"><b id="composedCount">0</b> compostas</span>
    <button class="btn btn-primary" onclick="printAll()">
      <svg><use href="#i-print"/></svg>Imprimir todas
    </button>
  </div>
  <div id="previewGrid" class="preview-grid"></div>
</div>
```

- [ ] **Step 6.6: Ajustar renderer de photo card em `static/app.js`**

Localizar `function renderPhotoGrid()` (~linha 367) e `renderPreviewGrid` (~linha 536). Substituir o template string pelo novo DOM:

```js
// renderPhotoGrid: por item
function photoCardHtml(p, i) {
  const match = (p.confidence || 0) >= 0.5;
  const selected = selectedPhotos.has(i);
  const pct = match ? `${Math.round(p.confidence * 100)}%` : '—';
  return `
    <div class="photo-card${match ? ' match' : ''}${selected ? ' selected' : ''}"
         data-idx="${i}" onclick="togglePhoto(${i}, event)">
      <div class="img-wrap">
        <img src="${p.thumbnail_url || p.url}" alt="">
        <div class="check"></div>
      </div>
      <div class="meta">
        <span class="fname">${p.filename || ''}</span>
        <span class="pct">${pct}</span>
      </div>
    </div>
  `;
}
```

E no listener de click: se target for `.check`, toggle selection; se for outro lugar, abrir modal.

```js
function togglePhoto(i, ev) {
  if (ev.target.closest('.check')) {
    ev.stopPropagation();
    if (selectedPhotos.has(i)) selectedPhotos.delete(i);
    else selectedPhotos.add(i);
    document.querySelector(`.photo-card[data-idx="${i}"]`)?.classList.toggle('selected');
    document.getElementById('selectionCount').textContent = selectedPhotos.size;
    return;
  }
  showModal(i);
}
window.togglePhoto = togglePhoto;
```

- [ ] **Step 6.7: Ajustar renderer da face strip em `static/app.js`**

Localizar onde rostos capturados são renderizados (~linha 318) e trocar para:

```js
function faceChipHtml(face, idx) {
  return `
    <div class="face-chip" data-idx="${idx}">
      <img src="${face.url || face.dataUrl}" alt="">
      <button class="rm" onclick="removeFace(${idx}, event)" title="Remover">×</button>
    </div>
  `;
}
```

Garantir que `removeFace(idx, ev)` existe (pode ser wrapper chamando o handler atual).

- [ ] **Step 6.8: Verificação manual no browser**

1. Step 0: título grande + subtitle + linha de input com ícone de pasta + dois botões. Lista de recentes mono, hover destaca linha.
2. Step 1: 2 colunas (preview grande à esquerda, painel à direita), strip de rostos em grid 4.
3. Step 2: toolbar no topo, grid de cards 3-4 colunas. Match cards têm borda esquerda verde + chip MATCH.
4. Step 3: mesma estrutura, cards maiores 3:2.
5. Selecionar um card (clicar no checkbox ▢) → fica verde com ✓.
6. Trocar tema mid-flow: cards mantêm legibilidade, bordas não somem em light.

- [ ] **Step 6.9: Commit**

```bash
git add static/styles/ static/index.html static/app.js
git commit -m "feat(ui): redesign all 4 screens (folder/webcam/grid/preview)"
```

---

## Task 7: Overlays (loading, modal, snackbar)

Restila os 3 overlays. Loading minimal, modal carousel preto, snackbar bottom-right.

**Files:**
- Modify: `static/styles/overlays.css`
- Modify: `static/index.html` (markup do snackbar e modal continua igual; loading simplifica estrutura)
- Modify: `static/app.js` (LoadingComponent mantém API pública, simplifica internals) + snackbar posicionamento

- [ ] **Step 7.1: Adicionar estilos em `overlays.css`**

```css
/* ===== loading ===== */
.loading-overlay {
  position: fixed; inset: 0; z-index: 100;
  background: rgba(0, 0, 0, .72);
  display: none; align-items: center; justify-content: center;
}
.loading-overlay.is-visible { display: flex; }
[data-theme="light"] .loading-overlay { background: rgba(0, 0, 0, .4); }

.loading-panel {
  display: flex; flex-direction: column; align-items: center; gap: var(--space-3);
  padding: var(--space-6);
}
.loading-indicator {
  width: 24px; height: 24px;
  border: 1px solid var(--border-strong); border-top-color: var(--brand);
  border-radius: 50%; animation: spin 1s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.loading-text { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #fff; letter-spacing: .04em; }
[data-theme="light"] .loading-text { color: var(--text-strong); }

/* ===== modal / carousel ===== */
.modal-overlay {
  position: fixed; inset: 0; z-index: 90;
  background: #000;
  display: none; align-items: center; justify-content: center;
}
.modal-overlay.is-visible { display: flex; }
.carousel-container { position: relative; max-width: 92vw; max-height: 92vh; display: flex; align-items: center; gap: var(--space-4); }
#modalImage { max-width: 88vw; max-height: 85vh; object-fit: contain; }
.carousel-btn {
  width: 36px; height: 36px; border-radius: 50%;
  border: 1px solid var(--border-strong); background: transparent; color: #fff;
  font-size: 18px; display: grid; place-items: center;
}
.carousel-btn:hover { background: rgba(255,255,255,.06); }
.carousel-close {
  position: absolute; top: 16px; right: 16px;
  width: 28px; height: 28px; border-radius: 50%;
  border: 1px solid var(--border-strong); background: transparent; color: #fff;
  font-size: 14px; display: grid; place-items: center; z-index: 2;
}
.carousel-info {
  position: absolute; bottom: 24px; left: 50%; transform: translateX(-50%);
  font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #fff;
  background: rgba(0,0,0,.5); padding: 6px 10px; border: 1px solid var(--border-strong);
  white-space: nowrap;
}
.carousel-info .pct { color: var(--brand); margin-left: 8px; }

/* ===== snackbar ===== */
.snackbar-stack {
  position: fixed; bottom: 16px; right: 16px; z-index: 110;
  display: flex; flex-direction: column; gap: 6px; align-items: flex-end;
}
.snack {
  background: var(--surface); border: 1px solid var(--border);
  border-left: 2px solid var(--text-dim);
  padding: 8px 12px; font-family: 'JetBrains Mono', monospace; font-size: 11px;
  color: var(--text); min-width: 200px; max-width: 360px;
}
.snack-success { border-left-color: var(--brand); }
.snack-warn { border-left-color: var(--warn); }
.snack-error { border-left-color: var(--danger); }
```

- [ ] **Step 7.2: Simplificar markup do loading em `static/index.html`**

Substituir o bloco `<div class="loading-overlay ..." id="loading" ...>` por:

```html
<div class="loading-overlay" id="loading"
     role="status" aria-live="polite" aria-atomic="true"
     aria-hidden="true" aria-busy="false">
  <div class="loading-panel">
    <div class="loading-indicator"></div>
    <div class="loading-text" id="loadingText">Processando...</div>
  </div>
</div>
```

Trocar `<div class="snackbar" id="snackbar"></div>` por:

```html
<div class="snackbar-stack" id="snackStack"></div>
```

- [ ] **Step 7.3: Simplificar `LoadingComponent` em `static/app.js`**

Remover todas as classes `.loading-size-*`, `.loading-color-*`, `.loading-mode-*` e suas lógicas associadas no `setOptions`. Manter a API pública (`show`, `hide`, `setText`, `withLoading`, `fetchJson`) e as funções globais (`showLoading`, `hideLoading`, `requestJson`).

```js
class LoadingComponent {
  constructor(elementId = 'loading', textId = 'loadingText') {
    this.el = document.getElementById(elementId);
    this.textEl = document.getElementById(textId);
    this.pending = new Set();
    this.startedAt = 0;
    this.hideTimer = null;
    this.options = { text: 'Processando...', fadeInMs: 400, fadeOutMs: 250, minVisibleMs: 240 };
  }
  setOptions(partial) { this.options = { ...this.options, ...partial }; if (partial.text) this.setText(partial.text); }
  setText(text) { if (this.textEl) this.textEl.textContent = text || ''; }
  show(text, opts = {}) {
    this.setOptions(opts); if (text) this.setText(text);
    const token = Symbol('loading'); this.pending.add(token);
    if (this.pending.size === 1) {
      this.startedAt = Date.now(); clearTimeout(this.hideTimer);
      this.el.classList.add('is-visible');
      this.el.setAttribute('aria-hidden', 'false'); this.el.setAttribute('aria-busy', 'true');
    }
    return token;
  }
  hide(token = null) {
    if (token) this.pending.delete(token); else this.pending.clear();
    if (this.pending.size > 0) return;
    const wait = Math.max(0, (this.options.minVisibleMs || 0) - (Date.now() - this.startedAt));
    clearTimeout(this.hideTimer);
    this.hideTimer = setTimeout(() => {
      this.el.classList.remove('is-visible');
      this.el.setAttribute('aria-hidden', 'true'); this.el.setAttribute('aria-busy', 'false');
    }, wait);
  }
  async withLoading(promiseFactory, opts = {}) {
    const token = this.show(opts.text, opts);
    try { return await promiseFactory(); } finally { this.hide(token); }
  }
  async fetchJson(url, options = {}, loadingOpts = {}) {
    return this.withLoading(async () => {
      const r = await fetch(url, options); if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    }, loadingOpts);
  }
}
```

- [ ] **Step 7.4: Substituir snackbar único por stack em `static/app.js`**

Localizar `function showSnack(...)` / `function hideSnack()`. Substituir por:

```js
function showSnack(text, severity = 'info', ms = 3500) {
  const stack = document.getElementById('snackStack');
  const el = document.createElement('div');
  el.className = `snack snack-${severity}`;
  el.textContent = text;
  stack.appendChild(el);
  setTimeout(() => el.remove(), ms);
}
window.showSnack = showSnack;
```

Callers que passavam classes antigas (`'success'`, `'error'`, `'warning'`) mapeiam direto pra `success` / `error` / `warn`. Procurar todas as chamadas e ajustar.

- [ ] **Step 7.5: Atualizar caption do modal em `static/app.js`**

Localizar `function carouselNav` / `function showModal` (~linha 609-663). Onde o `carouselInfo` é preenchido:

```js
document.getElementById('carouselInfo').innerHTML = `
  <b>${i + 1} / ${total}</b> · ${filename}
  ${pct ? `<span class="pct">${pct}% match</span>` : ''}
`;
```

E mudar o botão close pra usar SVG:

```html
<!-- em index.html, dentro do modal -->
<button class="carousel-close" onclick="closeModal()" title="Fechar">
  <svg width="14" height="14"><use href="#i-close"/></svg>
</button>
<button class="carousel-btn" id="carouselPrev" onclick="carouselNav(-1)">
  <svg width="18" height="18"><use href="#i-arrow-left"/></svg>
</button>
<button class="carousel-btn" id="carouselNext" onclick="carouselNav(1)">
  <svg width="18" height="18"><use href="#i-arrow-right"/></svg>
</button>
```

- [ ] **Step 7.6: Atualizar `tests/test_loading_component_contract.py`**

Substituir as assertions que procuravam CSS classes (`.loading-size-*`, `.loading-color-*`, `@media`) que não existem mais. Separar assertions em 2 grupos:

```python
import os
import unittest


class LoadingComponentContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = os.path.join(os.getcwd(), "static")
        with open(os.path.join(base, "index.html"), "r", encoding="utf-8") as f:
            cls.html = f.read()
        with open(os.path.join(base, "app.js"), "r", encoding="utf-8") as f:
            cls.js = f.read()
        with open(os.path.join(base, "styles", "overlays.css"), "r", encoding="utf-8") as f:
            cls.css = f.read()

    def test_overlay_aria_contract(self):
        for token in ['id="loading"', 'role="status"', 'aria-live="polite"',
                      'aria-atomic="true"', 'aria-hidden="true"', 'aria-busy="false"']:
            self.assertIn(token, self.html)

    def test_loading_component_api_exists(self):
        for token in ["class LoadingComponent", "setOptions(partial)", "setText(text)",
                      "show(text, opts = {})", "hide(token = null)",
                      "async withLoading(promiseFactory, opts = {})",
                      "async fetchJson(url, options = {}, loadingOpts = {})"]:
            self.assertIn(token, self.js)

    def test_overlay_css_present(self):
        for token in [".loading-overlay", ".loading-indicator", ".loading-text",
                      ".snackbar-stack", ".snack", ".modal-overlay"]:
            self.assertIn(token, self.css)
```

Deletar o teste `test_transition_timings_are_in_required_ranges` — as constantes mudaram de escopo (estão em `app.js`, não em `index.html`) e a regra de ranges não é mais parte do design.

- [ ] **Step 7.7: Rodar testes**

Run: `python -m pytest tests/test_loading_component_contract.py -v`
Expected: 3 tests pass (overlay_aria_contract, loading_component_api_exists, overlay_css_present).

Run: `python -m pytest tests/ -v`
Expected: Todos os testes passam (ou os 2 de server/regression passam como antes; ninguém novo quebra).

- [ ] **Step 7.8: Verificação manual no browser**

1. Trigger loading (ex: clicar Buscar com 500 fotos): overlay preto escuro + spinner 24px + texto mono centralizado.
2. Trigger snackbar success (ex: salvar foto): pílula aparece no **bottom-right**, borda esquerda verde.
3. Múltiplas snackbars empilham verticalmente.
4. Abrir modal de foto: fundo preto puro, setas circulares finas, caption mono no rodapé com `1 / N · filename · 87% match`.
5. Close button no canto superior direito: circular com SVG close.

- [ ] **Step 7.9: Commit**

```bash
git add static/styles/overlays.css static/index.html static/app.js tests/test_loading_component_contract.py
git commit -m "feat(ui): minimal loading, black carousel, bottom-right snack stack"
```

---

## Task 8: MediaPipe face detection ao vivo

Baixa MediaPipe vendored, cria `face-detection.js`, desenha bbox + cantos + pulse + label sobre o video. Gateia o botão "Capturar rosto" por detecção válida.

**Files:**
- Create: `static/vendor/mediapipe/` (arquivos baixados)
- Create: `static/face-detection.js`
- Modify: `static/styles/screens.css` (estilos do overlay)
- Modify: `static/index.html` (overlay canvas + `<script>`)
- Modify: `static/app.js` (integração mínima com `goToStep(1)`)

- [ ] **Step 8.1: Baixar arquivos do MediaPipe Face Detection**

Run:
```bash
mkdir -p static/vendor/mediapipe
cd static/vendor/mediapipe
curl -L -O https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.12/wasm/vision_wasm_internal.js
curl -L -O https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.12/wasm/vision_wasm_internal.wasm
curl -L -o face_detector.task https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.task
curl -L -O https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.12/vision_bundle.mjs
```
Expected: 4 arquivos presentes em `static/vendor/mediapipe/`, tamanhos ~200KB / ~2MB / ~230KB / ~150KB.

- [ ] **Step 8.2: Adicionar estilos do overlay em `screens.css`**

```css
#step1 .face-overlay {
  position: absolute; inset: 0; pointer-events: none;
  font-family: 'JetBrains Mono', monospace;
}
.face-overlay .live-badge {
  position: absolute; top: 8px; right: 8px; font-size: 9px; letter-spacing: .12em;
  color: var(--brand); display: flex; align-items: center; gap: 4px;
}
.face-overlay .live-badge::before {
  content: ''; width: 6px; height: 6px; border-radius: 50%; background: var(--brand);
  animation: livepulse 1.2s ease-in-out infinite;
}
.face-overlay.searching .live-badge { color: var(--warn); }
.face-overlay.searching .live-badge::before { background: var(--warn); }
.face-overlay .bbox {
  position: absolute; border: 1.5px solid var(--brand);
  transition: all .08s linear;
}
.face-overlay.low-conf .bbox { border-color: var(--warn); }
.face-overlay .bbox .corner { position: absolute; width: 12px; height: 12px; border: 2px solid var(--brand); }
.face-overlay.low-conf .bbox .corner { border-color: var(--warn); }
.face-overlay .bbox .corner.tl { top: -2px; left: -2px; border-right: 0; border-bottom: 0; }
.face-overlay .bbox .corner.tr { top: -2px; right: -2px; border-left: 0; border-bottom: 0; }
.face-overlay .bbox .corner.bl { bottom: -2px; left: -2px; border-right: 0; border-top: 0; }
.face-overlay .bbox .corner.br { bottom: -2px; right: -2px; border-left: 0; border-top: 0; }
.face-overlay .bbox .label {
  position: absolute; top: -22px; left: 0; background: var(--brand); color: #fff;
  font-size: 9px; letter-spacing: .1em; padding: 2px 6px; white-space: nowrap;
}
.face-overlay.low-conf .bbox .label { background: var(--warn); color: #000; }
.face-overlay .bbox .pulse {
  position: absolute; inset: -3px; border: 1px solid var(--brand);
  opacity: .4; animation: bboxpulse 1.6s ease-out infinite;
}
@keyframes bboxpulse {
  0% { transform: scale(1); opacity: .5; }
  100% { transform: scale(1.04); opacity: 0; }
}
```

- [ ] **Step 8.3: Adicionar markup do overlay em `static/index.html`**

Dentro de `#step1 .video-wrapper`, após `<canvas id="captureCanvas">`:

```html
<div class="face-overlay" id="faceOverlay">
  <span class="live-badge" id="liveBadge">PROCURANDO</span>
  <div class="bbox hidden" id="faceBbox">
    <div class="pulse"></div>
    <div class="corner tl"></div><div class="corner tr"></div>
    <div class="corner bl"></div><div class="corner br"></div>
    <div class="label" id="faceLabel">FACE 0%</div>
  </div>
</div>
```

E antes do `<script src="/static/app.js">`:
```html
<script type="module" src="/static/face-detection.js"></script>
```

- [ ] **Step 8.4: Criar `static/face-detection.js`**

```js
import { FilesetResolver, FaceDetector } from '/static/vendor/mediapipe/vision_bundle.mjs';

let detector = null;
let running = false;
let rafId = null;
let lastRun = 0;
const TARGET_FPS = 12;
const FRAME_MS = 1000 / TARGET_FPS;

async function init() {
  if (detector) return detector;
  const fileset = await FilesetResolver.forVisionTasks('/static/vendor/mediapipe');
  detector = await FaceDetector.createFromOptions(fileset, {
    baseOptions: { modelAssetPath: '/static/vendor/mediapipe/face_detector.task' },
    runningMode: 'VIDEO',
    minDetectionConfidence: 0.4,
  });
  return detector;
}

function pickLargest(detections) {
  if (!detections || !detections.length) return null;
  let best = null, bestArea = 0;
  for (const d of detections) {
    const b = d.boundingBox;
    const area = b.width * b.height;
    if (area > bestArea) { bestArea = area; best = d; }
  }
  return best;
}

function render(detection, video) {
  const overlay = document.getElementById('faceOverlay');
  const bbox = document.getElementById('faceBbox');
  const label = document.getElementById('faceLabel');
  const badge = document.getElementById('liveBadge');
  const btnCapture = document.getElementById('btnCapture');

  if (!detection) {
    bbox.classList.add('hidden');
    overlay.classList.add('searching');
    overlay.classList.remove('low-conf');
    badge.textContent = 'PROCURANDO';
    if (btnCapture) btnCapture.disabled = true;
    return;
  }

  const b = detection.boundingBox;
  const conf = detection.categories?.[0]?.score || 0;
  const lowConf = conf < 0.6;

  const vw = video.videoWidth || 640;
  const vh = video.videoHeight || 480;
  const rect = video.getBoundingClientRect();
  const scaleX = rect.width / vw;
  const scaleY = rect.height / vh;

  bbox.classList.remove('hidden');
  overlay.classList.remove('searching');
  overlay.classList.toggle('low-conf', lowConf);
  bbox.style.left = `${b.originX * scaleX}px`;
  bbox.style.top = `${b.originY * scaleY}px`;
  bbox.style.width = `${b.width * scaleX}px`;
  bbox.style.height = `${b.height * scaleY}px`;
  label.textContent = lowConf ? `FACE BAIXA QUALIDADE` : `FACE ${Math.round(conf * 100)}%`;
  badge.textContent = 'DETECTANDO';
  if (btnCapture) btnCapture.disabled = lowConf;
}

async function loop(video) {
  if (!running) return;
  const now = performance.now();
  if (now - lastRun >= FRAME_MS && video.readyState >= 2) {
    lastRun = now;
    try {
      const res = detector.detectForVideo(video, now);
      render(pickLargest(res.detections), video);
    } catch (e) { console.warn('[face-detect] frame error', e); }
  }
  rafId = requestAnimationFrame(() => loop(video));
}

export async function start() {
  if (running) return;
  await init();
  const video = document.getElementById('webcam');
  if (!video) return;
  running = true;
  lastRun = 0;
  loop(video);
}

export function stop() {
  running = false;
  if (rafId) cancelAnimationFrame(rafId);
  const btnCapture = document.getElementById('btnCapture');
  if (btnCapture) btnCapture.disabled = false;
  const bbox = document.getElementById('faceBbox');
  if (bbox) bbox.classList.add('hidden');
}

window.__faceDetect = { start, stop };
```

- [ ] **Step 8.5: Integrar com `goToStep` em `static/app.js`**

No início do arquivo, após as variáveis de estado:

```js
async function enterCaptureStep() {
  if (window.__faceDetect) {
    try { await window.__faceDetect.start(); }
    catch (e) { console.warn('[face-detect] init failed', e); }
  }
}
function leaveCaptureStep() {
  if (window.__faceDetect) window.__faceDetect.stop();
}
```

Dentro de `goToStep(step)`, após a mudança de tela ser aceita:

```js
if (step === 1) enterCaptureStep(); else leaveCaptureStep();
```

- [ ] **Step 8.6: Verificação manual no browser**

1. Ir para Step 1. Sem rosto na frame: badge amarelo "● PROCURANDO", botão "Capturar rosto" disabled.
2. Aparecer com rosto: badge verde "● DETECTANDO", bbox verde envolve o rosto, cantos 12px reforçando, pulse animado, label `FACE 97%` no topo.
3. Mover rosto: bbox segue em tempo real (~12 FPS, sem travar UI).
4. Clicar Capturar: snapshot continua funcionando como antes (`getUserMedia` + canvas).
5. Sair para Step 2 ou Step 0: loop pausa (confirmar no DevTools Performance tab que não há mais callbacks ativos).
6. Testar com má iluminação: badge vira amarelo + label "FACE BAIXA QUALIDADE" + bbox amarelo, captura fica disabled.

- [ ] **Step 8.7: Atualizar `.gitignore`** se necessário para excluir modelos grandes, ou commit deles explicitamente

Os arquivos MediaPipe somam ~2.5MB total. Commitar é OK (kiosk offline-first é requisito). Confirmar: `git status` mostra os 4 arquivos; nenhum cai em `.gitignore`.

- [ ] **Step 8.8: Commit**

```bash
git add static/vendor/ static/face-detection.js static/styles/screens.css static/index.html static/app.js
git commit -m "feat(ui): live face bbox via MediaPipe with confidence gating"
```

---

## Task 9: Cleanup e polimento final

Deletar `style.css` antigo, remover emoji residuais em strings JS (`showSnack` messages, títulos dinâmicos), e rodar QA completo das 4 telas em dark + light.

**Files:**
- Delete: `static/style.css`
- Modify: `static/app.js` (limpar emoji em strings)

- [ ] **Step 9.1: Deletar `static/style.css`**

Run: `git rm static/style.css`
Expected: Arquivo removido. O `index.html` já não referencia mais desde a Task 1.5.

- [ ] **Step 9.2: Grep por emoji residuais em `static/app.js`**

Run: `grep -nP "[\x{1F000}-\x{1FFFF}]|[\x{2600}-\x{27BF}]" static/app.js`
Expected: idealmente nenhum resultado. Se houver (provável em `showSnack` messages como "✓ salvo!" ou "⚠ erro"), substituir por texto plano: `showSnack('salvo', 'success')`.

- [ ] **Step 9.3: Grep por emoji residuais em `static/index.html`**

Run: `grep -nP "[\x{1F000}-\x{1FFFF}]|[\x{2600}-\x{27BF}]" static/index.html`
Expected: nenhum resultado.

- [ ] **Step 9.4: Rodar suite de testes completa**

Run: `python -m pytest tests/ -v`
Expected: Todos os testes passam. Se `test_mobile_scan_regression.py` fosse quebrado por uploads missing, skipar com `@pytest.mark.skipif` baseado em `os.path.isdir` — mas nunca deve ser quebrado pelo nosso restyle frontend.

- [ ] **Step 9.5: QA visual completo**

Abrir `http://127.0.0.1:8000`. Em **dark** mode, navegar pelas 4 telas + trigger overlays:

| Tela | O que checar |
|------|--------------|
| Step 0 | wordmark + tabs + título + input mono + recentes |
| Step 1 | 2 colunas, bbox ao vivo na webcam, face strip |
| Step 2 | toolbar + grid + match cards com borda verde |
| Step 3 | toolbar + preview grid 3:2 |
| Loading | overlay preto + spinner |
| Modal | fundo preto + setas + caption mono |
| Snackbar | bottom-right + borda esquerda colorida |

Alternar para **light** mode, repetir todo o percurso. Confirmar para cada tela:
- Nenhum texto cinza sobre cinza.
- Bordas visíveis (≠ `--border` do bg).
- Verde (`#006437`) legível e com contraste adequado.
- Zero emoji em qualquer lugar.

- [ ] **Step 9.6: Auto-validação dos 10 critérios de aceitação**

Confirmar cada um do spec:
1. ✓ Zero emoji
2. ✓ Toggle dark/light em todas telas + overlays sem bug visual
3. ✓ Webcam ≥10 FPS
4. ✓ Capturar disabled sem rosto
5. ✓ Status bar com metadata live
6. ✓ Scan sem overlay bloqueante
7. ✓ Snackbar bottom-right sem cobrir toolbar
8. ✓ CSS modularizado (5 arquivos)
9. ✓ Tema persiste ao reload
10. ⚠ "Cara de IA" — pedir avaliação de terceiro (usuário humano)

- [ ] **Step 9.7: Commit final**

```bash
git add -A static/ tests/
git commit -m "chore(ui): delete legacy style.css, final QA polish"
```

---

## Riscos e mitigações

1. **MediaPipe package mudou API/URL** — se `vision_bundle.mjs` não existir nessa versão, trocar por `@mediapipe/face_detection` legacy (script-tag based). Alternativa: fallback pro guia estático (oval tracejado central) se `import()` falhar. Implementar só se Step 8.1 falhar.
2. **Fontes Google bloqueadas** — kiosk offline quebra o `@import`. Mitigação futura: baixar Inter/JetBrains Mono/Bebas Neue como `.woff2` em `static/vendor/fonts/` e self-host via `@font-face`. Fora de escopo agora; se cliente pedir offline-only, abre ticket separado.
3. **Handlers globais preservados** — toda linha `onclick="fnName()"` no HTML novo depende de funções globais em `app.js`. A regra é: **não renomear nenhum handler existente**. Se precisar refatorar algum, mantém o nome original como wrapper. O contract test `test_loading_component_api_exists` ajuda a pegar esse tipo de regressão.
4. **Light mode em overlays pretos** — modal e loading usam bg preto no dark; em light o contraste reverte (loading fica com backdrop mais claro, modal mantém preto que é intencional pra fotos). Tokens controlam via `[data-theme="light"] .loading-overlay`.

---
