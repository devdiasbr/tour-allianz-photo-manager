# UI Restyle — Console Operacional

**Data:** 2026-04-19
**Escopo:** Reestilização completa da interface do Tour Allianz Photo Manager (HTML/CSS/JS estático em `static/`), substituindo a aparência genérica atual por um design system "console operacional" com suporte obrigatório a dark/light mode.

## Motivação

A UI atual passa a sensação de protótipo gerado por IA: emoji como ícone (📂📷⚽), verde neon que não corresponde à marca Palmeiras, botões Material-Design com gradiente, stepper de pílulas, cards sem hierarquia, tipografia genérica (Segoe UI sem variação). O operador (fotógrafo no back-office com mouse + teclado) precisa de uma ferramenta densa, profissional, que pareça produto de trabalho — não dashboard de demonstração.

## Direção visual

**Console operacional**: estética inspirada em Bloomberg Terminal e Linear. Densidade de informação primeiro, dados em mono, foto como sub-componente do dado. Cor única (verde Palmeiras) usada apenas para status com significado (match, ativo, sucesso, foco). Sem gradientes, sem glow, sem decoração.

## Fundações

### Tokens de cor — semânticos, idênticos em estrutura nos dois modos

```css
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

**Regras:**
- Verde de marca (`--brand`) é o mesmo nos dois temas — nunca muda.
- Verde aparece exclusivamente em: status de match, item ativo (tab/foco), badge de sucesso, borda de foco.
- Vermelho aparece só em: ação destrutiva (limpar, remover) e estado de erro.
- Componentes nunca codificam cor literal — sempre via custom property.

### Theme switching

- Toggle único na status bar (canto direito) — botão 28×28 com ícone que mostra o destino: sol no dark (clique → light), lua no light (clique → dark).
- Boot lê `prefers-color-scheme` na primeira visita; depois respeita escolha salva em `localStorage["theme"]`.
- Implementação: `document.documentElement.dataset.theme = "dark" | "light"`.

### Tipografia

| Token   | Família           | Tamanho | Peso | Uso                                   |
|---------|-------------------|---------|------|---------------------------------------|
| BRAND   | Bebas Neue        | 18px    | —    | Wordmark "TOUR ALLIANZ" — única ocorrência |
| H1      | Inter             | 22px    | 600  | Título de tela                        |
| H2      | Inter             | 16px    | 600  | Cabeçalho de seção                    |
| BODY    | Inter             | 13px    | 400  | Texto de leitura                      |
| SMALL   | Inter             | 11px    | 400  | Status, hints                         |
| LABEL   | JetBrains Mono    | 10px    | 500  | Labels uppercase, letter-spacing .12em |
| DATA    | JetBrains Mono    | 12px    | 500  | Arquivos, hashes, distâncias, %, timestamps |

Carregadas via Google Fonts. Bebas Neue é usado **exclusivamente** no wordmark — em nenhum outro lugar. Mono é usado para qualquer coisa que pareça "dado técnico" (arquivo, número, comando, status code).

### Espaçamento

Escala de 4px: `4 / 8 / 12 / 16 / 24 / 32 / 48`. Border radius: `0` por padrão, `2px` em tiles/cards/inputs/botões. Nunca usa `box-shadow` para elevação — separação é via `border 1px sólida`.

### Iconografia

Ícones SVG estilo Lucide, `stroke-width: 1.5`, `fill: none`, `stroke: currentColor` (herdam cor do contexto). Definidos em um `<svg style="display:none">` no topo do `index.html` como `<symbol>` reutilizável via `<use href="#i-name">`.

Inventário inicial: `camera`, `search`, `folder`, `add`, `check`, `close`, `print`, `save`, `arrow-left`, `arrow-right`, `trash`, `upload`, `sun`, `moon`, `rotate`.

**Zero emoji** na UI — nem no header, nem em botões, nem em status. Emojis vão embora completamente.

## Componentes

### Botões

4 variantes, 3 tamanhos. Padding base `9px 14px`, font 12px, border-radius 2px.

| Variante  | Background     | Color           | Border          | Uso                     |
|-----------|----------------|-----------------|-----------------|-------------------------|
| primary   | `--brand`      | `#fff`          | —               | 1 por tela (ação principal) |
| secondary | transparent    | `--text`        | `--border-strong` | Ações secundárias       |
| ghost     | transparent    | `--text-dim`    | —               | Voltar, ações terciárias |
| danger    | transparent    | `--danger`      | `#3a1f1f` / `--border-strong` | Limpar, remover         |

Tamanhos: `sm (6×10 padding, 11px)`, `md (default)`, `lg (12×18 padding, 13px)`. Variante `btn-icon-only` com padding `8px` quadrado.

Regra: 1 primary por tela (a ação principal). Ícone sempre à esquerda do label. Estado disabled = opacity .35.

### Inputs

```css
font-family: 'JetBrains Mono';     /* path/file inputs */
font-size: 12px;
background: var(--bg);
border: 1px solid var(--border-strong);
padding: 9px 12px;
border-radius: 2px;
```

`:focus` muda border para `var(--brand)`. Inputs de path são monospace; texto livre é Inter. Inputs com ícone à esquerda usam `position: absolute` no `<svg>` + `padding-left: 30px`.

### Status bar (topo da app)

`grid-template-columns: auto 1fr auto auto`. À esquerda: wordmark "TOUR ALLIANZ" em Bebas (com barra verde 3×18 antes). No meio: metadata mono (sessão, scan progress, contadores) — `live` em verde com bullet `●`. À direita: versão + theme toggle.

### Tabs (substitui o stepper de pílulas)

Linha horizontal abaixo da status bar. Cada tab = `<n> LABEL` em Inter 11px uppercase letter-spacing .12em. Número em JetBrains Mono verde. Ativa: texto branco + sublinhado branco 1px no bottom. Concluída: número some, ✓ verde antes do label. Clicável.

### Toolbar (ações por tela)

Linha abaixo das tabs. Padrão: `[← Voltar] | [ações secundárias] [spacer] [contador] [ação primária]`. Separador é `<div class="sep">` 1×16 com cor `--border`. Contador em mono pequeno, valor em verde.

### Photo card (step 2)

Estados: default / match / selected.

- **Default**: surface bg, border 1px sutil. Hover muda border para `--border-strong`.
- **Match**: borda esquerda 2px verde + chip "MATCH" 9px mono no top-left da imagem.
- **Selected**: outline `--brand` + `box-shadow: inset 0 0 0 1px var(--brand)` + checkbox preenchido verde no top-right.

Layout: `aspect-ratio: 4/3` na imagem, meta abaixo com filename à esquerda + % à direita (mono 11px). % verde em match cards. Grid responsivo 3-4 colunas (`repeat(auto-fill, minmax(220px, 1fr))`).

### Badges

Outline padrão (border 1px + currentColor + bg transparent), 10px mono uppercase letter-spacing. Variantes: `match` (verde), `warn` (amarelo `--warn`), `danger` (vermelho), `info` (cinza). Variante `solid` para destaque forte (% no carousel).

### Face strip (rostos capturados, step 1)

Grid `repeat(4, 1fr)` em painel lateral. Cada chip: 1:1 aspect-ratio, sem rounded, border `--border-strong`. X de remover aparece no hover (canto top-right, círculo 14px vermelho).

## Layouts das telas

Todas as telas têm a mesma estrutura:
```
[ status bar ]
[ tabs ]
[ toolbar (opcional) ]
[ conteúdo da tela ]
```

### Step 0 · Folder picker

Container max-width 720px, padding 36×60. H1 "Pasta da sessão" + subtítulo curto. Linha de input + botões `[Procurar]` + `[Confirmar]`. Abaixo, lista "RECENTES" em painel monoespaçado: `path | count fotos | when`. Hover destaca linha. Sem dropzone gigante, sem ilustração — direto ao ponto.

### Step 1 · Captura webcam

Layout 2-colunas: `1fr 280px`.

**Coluna esquerda**: preview da webcam em 4:3 (era 4:3 fixo em 640×480, vira responsivo). Acima do botão de captura: bounding box ao vivo (ver "Detecção de rosto"). Abaixo da preview: linha de ações `[Capturar rosto (primary)] [Enviar foto] [Trocar câmera]`.

**Coluna direita** (panel surface): cabeçalho "ROSTOS DE REFERÊNCIA · {n}", grid 4-colunas com face chips, separador, então cabeçalho "AÇÕES" com `[Buscar fotos (primary lg)]` + `[Limpar todos (danger)]`.

### Step 2 · Grid de fotos

Toolbar: `[Voltar] | [Selecionar todas] [Inverter] [spacer] selecionadas X/Y [Compor e imprimir]`.

Conteúdo: scan-bar inline mostrando progresso quando ativo (`scanning N/T [bar 2px] match X`). Substitui o overlay de loading que bloqueava interação. Grid de photo cards 3-4 colunas adaptativo. Card click abre modal-carousel; click na checkbox toggle seleciona.

### Step 3 · Preview / impressão

Toolbar: `[Voltar] | [Salvar todas] [Nova busca] [spacer] N compostas [Imprimir todas]`.

Grid 2-colunas (cards maiores, `aspect-ratio: 3/2`). Card click abre carousel mostrando composição. Meta mono: `filename | dimensões · DPI`.

## Overlays

### Loading

Substituiu o painel grande com gradiente. Agora: backdrop preto translúcido + spinner pequeno (24×24, 1px border, top-color `--brand`) + texto mono 11px. `compondo {n}/{total} · {currentFile}` — informação concreta, não "Processando...".

### Modal / carousel

Background `#000`. Setas chevron finas em botão circular 36px (border `--border-strong`, transparent bg). Imagem central com max-height. Caption no rodapé: `<b>{i} / {total}</b> · {filename}<span>{conf}% match</span>` em mono. Botão close circular 28px no canto superior direito.

### Snackbar

Move do bottom-center pra **bottom-right**. Pílula horizontal: surface bg, border 1px, **borda esquerda 2px com cor da severidade** (`--brand` success, `--warn` warning, `--danger` error). Mono 11px. Empilha verticalmente quando há múltiplos.

## Detecção de rosto ao vivo (webcam)

**Biblioteca**: MediaPipe Face Detection (Google) — mais leve (~150KB lib + ~200KB modelo) e atual que face-api.js, melhor performance em CPU.

**Carregamento**: vendored em `static/vendor/mediapipe/` (não CDN — kiosk pode operar offline). Modelo BlazeFace short-range (otimizado pra rostos próximos da câmera).

**Loop**: `requestAnimationFrame` throttled a ~12 FPS (suficiente pra UX, economiza CPU). Roda apenas quando a tab Captura está ativa — pausa em outras telas.

**Visual**:
- Bounding box `border: 1.5px solid var(--brand)` envolvendo o rosto detectado.
- 4 cantos quadrados de 12×12px reforçando o bbox.
- Label superior `FACE {confidence}%` em mono 9px, fundo verde sólido.
- Pulse animado (`scale 1 → 1.04 + opacity .5 → 0` em 1.6s) na borda externa pra dar vida.
- Badge "● DETECTANDO" no canto superior direito da preview, bullet pulsante.

**Comportamento**:
- Múltiplos rostos: marca apenas o maior (área do bbox).
- Sem rosto detectado: badge muda para "● PROCURANDO" (amarelo), botão "Capturar rosto" fica disabled.
- Confidence < 0.6: bbox em amarelo, label "FACE BAIXA QUALIDADE".

**Captura**: continua sendo `getUserMedia` + canvas snapshot. A detecção é só visual — a imagem capturada vai pro servidor pra ser processada pelo `face_recognition` (Python) como hoje. Não substitui o pipeline existente.

## Mudanças funcionais (além de visual)

1. **Status bar fixa** carrega contexto da sessão (pasta, scan progress, match count) — operador não precisa "voltar" pra ver onde está.
2. **Scan inline** (step 2) substitui o overlay de loading que bloqueava interação durante o scan — barra de progresso fica embutida no toolbar. (Resultados continuam aparecendo no fim do scan; streaming incremental fica fora desse spec — depende do endpoint atual ser one-shot.)
3. **Snackbar bottom-right** não tampa o botão primário do toolbar.
4. **Tabs clicáveis** servem de breadcrumb + navegação direta (já existia, mas estética agora suporta).
5. **Theme toggle** persiste por usuário (localStorage).
6. **Botão "Capturar rosto" gateado** pela detecção (só ativa com rosto válido na frame).

## Estrutura de arquivos

A app é estática (sem build step). Vou separar pra dar manutenibilidade — atualmente `style.css` tem 485 linhas tudo junto e `app.js` tem 712.

```
static/
├── index.html              (estrutura, refs aos componentes via classes)
├── app.js                  (lógica principal — sem mudança de estrutura)
├── theme.js                (NOVO: boot do tema + toggle handler)
├── face-detection.js       (NOVO: MediaPipe loop + bbox render)
├── _icons.html             (NOVO: <symbol> sprite — server-side include no index.html, sem fetch async)
├── styles/
│   ├── tokens.css          (NOVO: custom properties dark/light)
│   ├── base.css            (NOVO: reset + body + tipografia + utilities)
│   ├── components.css      (NOVO: status-bar, tabs, toolbar, btn, input, badge, etc)
│   ├── screens.css         (NOVO: layouts específicos das 4 telas)
│   └── overlays.css        (NOVO: loading, modal, snackbar)
└── vendor/
    └── mediapipe/          (NOVO: face_detection wasm + model)
```

`style.css` antigo é deletado (ou mantido vazio em cima dos novos imports temporariamente). `index.html` muda só o `<link>` e os `class=` — estrutura de IDs e handlers em JS continua intacta pra `app.js` não quebrar.

## Não-objetivos (fora de escopo)

- Mudanças no pipeline server-side (`server.py`, `app/services/*`) — restyle é só frontend.
- Mudança no template de impressão (`footer_template/template_allianz.jpg`) — composição final mantém o footer atual.
- Internacionalização (continua PT-BR).
- Mobile / responsividade pra touch — operador usa desktop.
- Atalhos de teclado — pode entrar num futuro plano, fora desse spec.

## Critérios de aceitação

1. Todos os emojis (📂📷⚽🗑🔍🖨💾🔄✓←) substituídos por SVG inline ou removidos.
2. Toggle dark/light funciona em todas as 4 telas + 3 overlays — sem texto ilegível ou bordas sumindo em nenhum dos modos.
3. Webcam mostra bounding box que segue o rosto a ≥ 10 FPS sem travar a UI.
4. Botão "Capturar rosto" fica disabled quando não há rosto detectado.
5. Status bar mostra metadata da sessão atualizada em tempo real durante o scan.
6. Scan da step 2 não bloqueia mais a tela com overlay — cards aparecem incrementalmente.
7. Snackbar aparece no canto inferior direito sem cobrir botões da toolbar.
8. CSS está modularizado em arquivos por responsabilidade (tokens / base / components / screens / overlays).
9. Tema escolhido persiste ao recarregar a página.
10. Aparência geral não tem mais "cara de IA" — testar pedindo a um terceiro pra olhar e dar veredicto.
