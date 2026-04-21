        // State
        let currentStep = 0;
        let sessionPath = null;
        let webcamStream = null;
        let capturedCount = 0;
        let sessionPhotoCount = 0;
        let matchResults = [];
        let selectedPhotos = new Set();
        let orientations = {};
        let composedFiles = [];
        let loadingManager = null;

        class LoadingComponent {
            constructor(elementId = 'loading', textId = 'loadingText') {
                this.el = document.getElementById(elementId);
                this.textEl = document.getElementById(textId);
                this.pending = new Set();
                this.startedAt = 0;
                this.hideTimer = null;
                this.options = { text: 'Processando...', fadeInMs: 400, fadeOutMs: 250, minVisibleMs: 240 };
            }

            setOptions(partial) {
                this.options = { ...this.options, ...partial };
                if (partial.text) this.setText(partial.text);
            }

            setText(text) {
                if (this.textEl) this.textEl.textContent = text || '';
            }

            show(text, opts = {}) {
                this.setOptions(opts);
                if (text) this.setText(text);
                const token = Symbol('loading');
                this.pending.add(token);
                if (this.pending.size === 1) {
                    this.startedAt = Date.now();
                    clearTimeout(this.hideTimer);
                    this.el.classList.add('is-visible');
                    this.el.setAttribute('aria-hidden', 'false');
                    this.el.setAttribute('aria-busy', 'true');
                }
                return token;
            }

            hide(token = null) {
                if (token) this.pending.delete(token);
                else this.pending.clear();
                if (this.pending.size > 0) return;
                const wait = Math.max(0, (this.options.minVisibleMs || 0) - (Date.now() - this.startedAt));
                clearTimeout(this.hideTimer);
                this.hideTimer = setTimeout(() => {
                    this.el.classList.remove('is-visible');
                    this.el.setAttribute('aria-hidden', 'true');
                    this.el.setAttribute('aria-busy', 'false');
                }, wait);
            }

            async withLoading(promiseFactory, opts = {}) {
                const token = this.show(opts.text, opts);
                try { return await promiseFactory(); } finally { this.hide(token); }
            }

            async fetchJson(url, options = {}, loadingOpts = {}) {
                return this.withLoading(async () => {
                    const r = await fetch(url, options);
                    if (!r.ok) throw new Error(`HTTP ${r.status}`);
                    return r.json();
                }, loadingOpts);
            }
        }

        // === NAVIGATION ===
        async function _applyStep(step) {
            document.querySelectorAll('.content').forEach(el => el.classList.add('hidden'));
            document.getElementById(`step${step}`).classList.remove('hidden');
            currentStep = step;
            if (step === 1) startWebcam(); else stopWebcam();
            if (window.__faceDetect) {
                if (step === 1) {
                    try { await window.__faceDetect.start(); }
                    catch (e) { console.warn('[face-detect] init failed', e); }
                } else {
                    window.__faceDetect.stop();
                }
            }
            document.querySelectorAll('.tab').forEach(t => {
                const n = Number(t.dataset.step);
                t.classList.toggle('active', n === step);
                t.classList.toggle('done', n < step);
            });
        }

        const STEP_LABELS = ['Sessão', 'Captura', 'Fotos', 'Imprimir'];

        async function goToStep(step) {
            if (step > currentStep) return; // Can't skip ahead
            if (step === currentStep) return;
            if (currentStep > 0) {
                const ok = await showConfirm({
                    title: `Voltar para ${STEP_LABELS[step]}?`,
                    body: 'Todo o progresso da sessão atual será perdido.',
                    okText: 'Voltar',
                    cancelText: 'Cancelar'
                });
                if (!ok) return;
            }
            if (currentStep === 1) stopWebcam();
            await _applyStep(step);
        }

        async function goToStepForce(step) {
            if (currentStep === 1) stopWebcam();
            await _applyStep(step);
        }

        // === FOLDER PICKER ===
        const RECENT_KEY = 'recentFolders';
        const MAX_RECENT = 5;

        function loadRecent() {
            try { return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]'); }
            catch { return []; }
        }

        function saveRecent(path, count) {
            let recents = loadRecent().filter(r => r.path !== path);
            recents.unshift({ path, count });
            recents = recents.slice(0, MAX_RECENT);
            localStorage.setItem(RECENT_KEY, JSON.stringify(recents));
            renderRecent();
        }

        function renderRecent() {
            const recents = loadRecent();
            const section = document.getElementById('recentSection');
            const list = document.getElementById('recentList');
            if (recents.length === 0) { section.classList.add('hidden'); return; }
            section.classList.remove('hidden');
            list.innerHTML = '';
            recents.forEach(r => {
                const item = document.createElement('div');
                item.className = 'recent-row';
                const name = r.path.split(/[\\\/]/).pop() || r.path;
                item.innerHTML = `
                    <span class="r-path" title="${r.path}">${name}</span>
                    <span class="r-count">${r.count} fotos</span>
                    <span class="r-when"></span>
                `;
                item.onclick = () => {
                    document.getElementById('pathInput').value = r.path;
                    confirmFolder();
                };
                list.appendChild(item);
            });
        }

        async function browseFolder() {
            const btn = document.getElementById('btnBrowse');
            btn.disabled = true;
            btn.textContent = 'Abrindo...';
            try {
                const res = await fetch('/api/browse-folder');
                const data = await res.json();
                if (data.ok && data.path) {
                    document.getElementById('pathInput').value = data.path;
                    await confirmFolder();
                }
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<svg><use href="#i-folder"/></svg>Procurar';
            }
        }

        async function confirmFolder() {
            const path = document.getElementById('pathInput').value.trim();
            const info = document.getElementById('pathInfo');
            if (!path) { info.className = 'path-info err'; info.textContent = 'Digite o caminho da pasta.'; return; }

            const data = await requestJson('/api/session/select', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({path})
            }, {
                text: 'Selecionando sessão...'
            });

            if (!data.ok) {
                info.className = 'path-info err';
                info.textContent = data.message;
                return;
            }

            info.className = 'path-info ok';
            info.textContent = `${data.count} foto(s) encontrada(s) em: ${data.path}`;
            saveRecent(data.path, data.count);

            sessionPath = data.path;
            sessionPhotoCount = Number(data.count || 0);
            updateStatusBar({ session: sessionPath.split(/[\\/]/).pop(), photos: sessionPhotoCount });
            capturedCount = 0;
            matchResults = [];
            selectedPhotos.clear();
            document.getElementById('capturedFaces').innerHTML = '';
            document.getElementById('faceCount').textContent = '0';
            document.getElementById('btnSearch').disabled = true;

            setTimeout(() => goToStepForce(1), 800);
        }

        function initFolderPicker() {
            renderRecent();
        }

        // === WEBCAM ===
        async function startWebcam() {
            try {
                webcamStream = await navigator.mediaDevices.getUserMedia({
                    video: { width: 640, height: 480, facingMode: 'user' }
                });
                document.getElementById('webcam').srcObject = webcamStream;
            } catch (err) {
                showSnackbar('Erro ao acessar webcam: ' + err.message);
            }
        }

        function stopWebcam() {
            if (webcamStream) {
                webcamStream.getTracks().forEach(t => t.stop());
                webcamStream = null;
            }
        }

        async function captureFrame() {
            const video = document.getElementById('webcam');
            const canvas = document.getElementById('captureCanvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0);

            // Convert to blob and send
            const blob = await new Promise(r => canvas.toBlob(r, 'image/jpeg', 0.9));
            const formData = new FormData();
            formData.append('file', blob, 'capture.jpg');

            let loadingToken = null;
            try {
                loadingToken = showLoading('Capturando e processando rosto...');
                const res = await fetch('/api/face/capture', { method: 'POST', body: formData });
                const data = await res.json();

                if (data.ok) {
                    capturedCount = data.total_references;
                    document.getElementById('faceCount').textContent = capturedCount;
                    document.getElementById('btnSearch').disabled = false;

                    // Add face thumbnail
                    const thumbUrl = canvas.toDataURL('image/jpeg', 0.7);
                    addFaceChip(thumbUrl);
                    showSnackbar(`${data.faces_count} rosto(s) capturado(s)!`);
                } else {
                    showSnackbar(data.message || 'Nenhum rosto detectado');
                }
            } catch (err) {
                showSnackbar('Erro: ' + err.message);
            } finally {
                hideLoading(loadingToken);
            }
        }

        function removeFaceChip(index) {
            const chip = document.querySelector(`.face-chip[data-idx="${index}"]`);
            if (chip) chip.remove();
        }
        window.removeFaceChip = removeFaceChip;

        function addFaceChip(imgSrc) {
            const container = document.getElementById('capturedFaces');
            const idx = container.children.length;
            const chip = document.createElement('div');
            chip.className = 'face-chip';
            chip.dataset.idx = idx;
            chip.innerHTML = `<img src="${imgSrc}" alt=""><button class="rm" onclick="removeFaceChip(${idx})" title="Remover">×</button>`;
            container.appendChild(chip);
        }

        async function uploadPhotos(files) {
            if (!files || files.length === 0) return;

            let loadingToken = null;
            try {
                loadingToken = showLoading('Enviando foto e detectando rostos...');
                for (let i = 0; i < files.length; i++) {
                    const file = files[i];
                    const formData = new FormData();
                    formData.append('file', file, file.name);
                    if (loadingManager) {
                        loadingManager.setText(`Enviando foto ${i + 1}/${files.length} e detectando rostos...`);
                    }

                    try {
                        const res = await fetch('/api/face/capture', { method: 'POST', body: formData });
                        const data = await res.json();

                        if (data.ok) {
                            capturedCount = data.total_references;
                            document.getElementById('faceCount').textContent = capturedCount;
                            document.getElementById('btnSearch').disabled = false;

                            // Create thumbnail from uploaded file
                            const reader = new FileReader();
                            reader.onload = (e) => addFaceChip(e.target.result);
                            reader.readAsDataURL(file);

                            showSnackbar(`${data.faces_count} rosto(s) detectado(s) na foto!`);
                        } else {
                            showSnackbar(data.message || 'Nenhum rosto detectado na foto');
                        }
                    } catch (err) {
                        showSnackbar('Erro ao enviar foto: ' + err.message);
                    }
                }
            } finally {
                hideLoading(loadingToken);
            }

            // Reset file input so same file can be re-selected
            document.getElementById('fileUpload').value = '';
        }

        async function clearFaces() {
            await requestJson('/api/face/clear', { method: 'POST' }, { text: 'Limpando rostos...' });
            capturedCount = 0;
            document.getElementById('faceCount').textContent = '0';
            document.getElementById('capturedFaces').innerHTML = '';
            document.getElementById('btnSearch').disabled = true;
            showSnackbar('Rostos limpos');
        }

        // === SCAN ===
        const SCAN_POLL_MS = 500;

        function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

        async function startSearch() {
            stopWebcam();
            goToStepForce(2);

            const progress = document.getElementById('scanProgress');
            const fill = document.getElementById('scanFill');
            const text = document.getElementById('scanText');
            const grid = document.getElementById('photoGrid');

            const fallbackTotal = Math.max(0, Number(sessionPhotoCount) || 0);
            const progressText = (done, total, percent) => {
                if (total > 0) {
                    const remaining = Math.max(0, total - done);
                    return `Analisando fotos... ${percent}% • ${done}/${total} processadas • ${remaining} restantes`;
                }
                return `Analisando fotos... ${percent}%`;
            };

            progress.classList.add('hidden');
            fill.style.width = '0%';
            text.textContent = progressText(0, fallbackTotal, 0);
            grid.innerHTML = '';
            document.getElementById('gridStatus').textContent = fallbackTotal > 0
                ? `Buscando... 0/${fallbackTotal} processadas`
                : `Buscando...`;

            const loadingToken = showLoading(progressText(0, fallbackTotal, 0));

            try {
                const startRes = await fetch('/api/scan', { method: 'POST' });
                const startData = await startRes.json();
                if (!startData.ok) {
                    showSnackbar(startData.message || 'Erro ao iniciar scan');
                    return;
                }
                progress.classList.remove('hidden');
                const jobId = startData.job_id;

                while (true) {
                    await sleep(SCAN_POLL_MS);
                    const r = await fetch(`/api/scan/${encodeURIComponent(jobId)}`);
                    const j = await r.json();
                    if (!j.ok) {
                        showSnackbar(j.message || 'Erro durante scan');
                        return;
                    }

                    const total = j.total > 0 ? j.total : fallbackTotal;
                    const done = Math.min(j.progress || 0, total || j.progress || 0);
                    const percent = total > 0 ? Math.floor((done * 100) / total) : 0;
                    fill.style.width = percent + '%';
                    text.textContent = `${done}/${total > 0 ? total : '?'}`;
                    const txt = progressText(done, total, percent);
                    if (loadingManager) loadingManager.setText(txt);
                    if (total > 0) {
                        document.getElementById('gridStatus').textContent =
                            `Buscando... ${done}/${total} processadas • ${Math.max(0, total - done)} restantes`;
                    }

                    if (j.status === 'done') {
                        fill.style.width = '100%';
                        text.textContent = `${total}/${total}`;
                        const finalText = total > 0
                            ? `Concluido! • ${total}/${total} processadas • 0 restantes`
                            : `Concluido!`;
                        if (loadingManager) loadingManager.setText(finalText);

                        matchResults = j.matches || [];
                        selectedPhotos = new Set(matchResults.map(m => m.file_path));
                        matchResults.forEach(m => { orientations[m.file_path] = 'landscape'; });
                        const matchesEl = document.getElementById('scanMatches');
                        if (matchesEl) matchesEl.textContent = matchResults.length;
                        updateStatusBar({ matches: matchResults.length });
                        renderPhotoGrid();
                        document.getElementById('gridStatus').textContent =
                            `${matchResults.length} fotos encontradas, ${matchResults.length} selecionadas`;
                        return;
                    }
                    if (j.status === 'error') {
                        showSnackbar(j.message || 'Erro durante scan');
                        return;
                    }
                }
            } catch (err) {
                showSnackbar('Erro no scan: ' + err.message);
            } finally {
                hideLoading(loadingToken);
            }
        }

        function photoCardHtml(photo, idx) {
            const rawConf = photo.confidence || 0;
            const isMatch = rawConf >= 50;
            const isSelected = selectedPhotos.has(photo.file_path);
            const pct = isMatch ? `${rawConf}%` : '—';
            const classes = ['photo-card', isMatch ? 'match' : '', isSelected ? 'selected' : ''].filter(Boolean).join(' ');
            const escapedPath = (photo.file_path || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
            return `
              <div class="${classes}" data-idx="${idx}" data-path="${(photo.file_path || '').replace(/"/g, '&quot;')}" onclick="handlePhotoClick(${idx}, '${escapedPath}', event)">
                <div class="img-wrap">
                  <img src="${photo.thumbnail_url || photo.url || ''}" alt="" loading="lazy">
                  <div class="check"></div>
                </div>
                <div class="meta">
                  <span class="fname">${photo.filename || ''}</span>
                  <span class="pct">${pct}</span>
                </div>
              </div>
            `;
        }

        function handlePhotoClick(idx, filePath, event) {
            if (event.target.closest('.check')) {
                event.stopPropagation();
                if (selectedPhotos.has(filePath)) selectedPhotos.delete(filePath);
                else selectedPhotos.add(filePath);
                const card = document.querySelector(`.photo-card[data-idx="${idx}"]`);
                if (card) card.classList.toggle('selected', selectedPhotos.has(filePath));
                const countEl = document.getElementById('selectionCount');
                if (countEl) countEl.textContent = selectedPhotos.size;
                return;
            }
            showModal(idx);
        }
        window.handlePhotoClick = handlePhotoClick;

        function renderPhotoGrid() {
            const grid = document.getElementById('photoGrid');
            grid.innerHTML = '';

            const countEl = document.getElementById('selectionCount');
            if (countEl) countEl.textContent = selectedPhotos.size;

            if (matchResults.length === 0) {
                grid.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-dim);width:100%">Nenhuma foto encontrada</div>';
                return;
            }

            grid.innerHTML = matchResults.map((m, idx) => photoCardHtml(m, idx)).join('');
        }

        function toggleSelectAll() {
            const allSelected = selectedPhotos.size === matchResults.length;
            if (allSelected) {
                selectedPhotos.clear();
            } else {
                matchResults.forEach(m => selectedPhotos.add(m.file_path));
            }
            renderPhotoGrid();
            const countEl = document.getElementById('selectionCount');
            if (countEl) countEl.textContent = selectedPhotos.size;
            document.getElementById('gridStatus').textContent =
                `${matchResults.length} fotos encontradas, ${selectedPhotos.size} selecionadas`;
        }

        // === COMPOSE ===
        async function composeSelected() {
            if (selectedPhotos.size === 0) {
                showSnackbar('Selecione pelo menos uma foto');
                return;
            }

            try {
                const data = await requestJson('/api/compose', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        selected: Array.from(selectedPhotos),
                        orientations: orientations
                    })
                }, { text: 'Compondo imagens...' });

                if (data.ok) {
                    composedFiles = data.files;
                    goToStepForce(3);
                    renderPreview();
                }
            } catch (err) {
                showSnackbar('Erro: ' + err.message);
            }
        }

        function encodeOutputPath(filename) {
            // Each path segment encoded individually so subfolders survive routing.
            return filename.split('/').map(encodeURIComponent).join('/');
        }

        function renderPreview() {
            const grid = document.getElementById('previewGrid');
            grid.innerHTML = '';
            document.getElementById('previewStatus').textContent =
                `${composedFiles.length} imagens compostas e prontas`;

            const composedCountEl = document.getElementById('composedCount');
            if (composedCountEl) composedCountEl.textContent = composedFiles.length;

            composedFiles.forEach((f, idx) => {
                const url = `/api/output/${encodeOutputPath(f.filename)}`;
                const label = f.filename.split('/').pop();
                const card = document.createElement('div');
                card.className = 'photo-card';
                card.innerHTML = `
                    <div class="img-wrap" onclick="showModal(${idx}, 'composed')" style="cursor:pointer">
                        <img src="${url}" loading="lazy" alt="">
                    </div>
                    <div class="meta">
                        <span class="fname">${label}</span>
                    </div>
                `;
                grid.appendChild(card);
            });
        }

        // === PRINT ===
        async function printAll() {
            try {
                const data = await requestJson('/api/print', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({files: composedFiles})
                }, { text: 'Enviando para impressão...' });
                showSnackbar(`${data.printed} imagem(ns) abertas — clique em Imprimir no visualizador para escolher a impressora`);
            } catch (err) {
                showSnackbar('Erro: ' + err.message);
            }
        }

        function saveAll() {
            showSnackbar(`${composedFiles.length} imagens já salvas na pasta output/`);
        }

        // === UI HELPERS ===
        function showSnack(text, severity = 'info', ms = 3500) {
            const stack = document.getElementById('snackStack');
            if (!stack) return;
            const el = document.createElement('div');
            el.className = `snack snack-${severity}`;
            el.textContent = text;
            stack.appendChild(el);
            setTimeout(() => { if (el.parentNode) el.remove(); }, ms);
        }
        window.showSnack = showSnack;

        function showSnackbar(msg) {
            showSnack(msg, 'info');
        }

        function showLoading(text, options = {}) {
            return loadingManager.show(text, options);
        }

        function hideLoading(token = null) {
            loadingManager.hide(token);
        }

        async function requestJson(url, options = {}, loadingOptions = {}) {
            return loadingManager.fetchJson(url, options, loadingOptions);
        }

        // === CAROUSEL ===
        let carouselIndex = 0;
        // 'matches' shows /api/photo originals from matchResults (gallery step).
        // 'composed' shows /api/output composites from composedFiles (print step).
        let carouselSource = 'matches';

        function carouselItems() {
            return carouselSource === 'composed' ? composedFiles : matchResults;
        }

        function showModal(index, source = 'matches') {
            carouselSource = source;
            carouselIndex = index;
            updateCarousel();
            document.getElementById('imageModal').classList.add('is-visible');
            document.addEventListener('keydown', carouselKeyHandler);
        }

        function closeModal() {
            document.getElementById('imageModal').classList.remove('is-visible');
            document.removeEventListener('keydown', carouselKeyHandler);
        }

        function handleModalClick(event) {
            // Close only when clicking the dark overlay, not buttons/image
            if (event.target === document.getElementById('imageModal')) {
                closeModal();
            }
        }

        function updateCarousel() {
            const items = carouselItems();
            const m = items[carouselIndex];
            if (!m) return;
            const img = document.getElementById('modalImage');
            img.onerror = null;
            if (carouselSource === 'composed') {
                img.src = `/api/output/${encodeOutputPath(m.filename)}`;
                const label = m.filename.split('/').pop();
                document.getElementById('carouselInfo').innerHTML =
                    `<strong>${carouselIndex + 1}</strong> / ${items.length} — ${label}`;
            } else {
                const fullUrl = `/api/photo?filename=${encodeURIComponent(m.filename)}`;
                img.onerror = () => {
                    img.onerror = null;
                    if (m.thumbnail_url) img.src = m.thumbnail_url;
                };
                img.src = fullUrl;
                document.getElementById('carouselInfo').innerHTML =
                    `<strong>${carouselIndex + 1}</strong> / ${items.length} — ${m.filename} — Confiança: ${m.confidence}%`;
            }
            document.getElementById('carouselPrev').disabled = carouselIndex === 0;
            document.getElementById('carouselNext').disabled = carouselIndex === items.length - 1;
        }

        function carouselNav(dir) {
            const items = carouselItems();
            const newIdx = carouselIndex + dir;
            if (newIdx >= 0 && newIdx < items.length) {
                carouselIndex = newIdx;
                updateCarousel();
            }
        }

        function carouselKeyHandler(e) {
            if (e.key === 'ArrowLeft') carouselNav(-1);
            else if (e.key === 'ArrowRight') carouselNav(1);
            else if (e.key === 'Escape') closeModal();
        }

        // === STATUS BAR ===
        function updateStatusBar({ session, photos, scanCur, scanTot, matches } = {}) {
            const el = id => document.getElementById(id);
            if (session !== undefined) { const s = el('metaSession'); if (s) s.textContent = session || '—'; }
            if (photos !== undefined) { const p = el('metaPhotos'); if (p) p.textContent = photos; }
            if (matches !== undefined) { const m = el('metaMatches'); if (m) m.textContent = matches; }
            const scan = el('metaScan');
            if (scan) {
                if (scanCur !== undefined && scanTot !== undefined && scanTot > 0) {
                    const v = el('metaScanVal'); if (v) v.textContent = `${scanCur}/${scanTot}`;
                    scan.classList.remove('hidden');
                } else if (scanCur === null) {
                    scan.classList.add('hidden');
                }
            }
        }
        window.updateStatusBar = updateStatusBar;

        function showConfirm({ title, body, okText = 'Confirmar', cancelText = 'Cancelar' } = {}) {
            return new Promise(resolve => {
                const dlg = document.getElementById('confirmDialog');
                const okBtn = document.getElementById('confirmOk');
                const cancelBtn = document.getElementById('confirmCancel');
                if (title) document.getElementById('confirmTitle').textContent = title;
                if (body) document.getElementById('confirmBody').textContent = body;
                okBtn.textContent = okText;
                cancelBtn.textContent = cancelText;
                dlg.classList.add('is-visible');
                dlg.setAttribute('aria-hidden', 'false');

                const cleanup = (result) => {
                    dlg.classList.remove('is-visible');
                    dlg.setAttribute('aria-hidden', 'true');
                    okBtn.removeEventListener('click', onOk);
                    cancelBtn.removeEventListener('click', onCancel);
                    dlg.removeEventListener('click', onBackdrop);
                    document.removeEventListener('keydown', onKey);
                    resolve(result);
                };
                const onOk = () => cleanup(true);
                const onCancel = () => cleanup(false);
                const onBackdrop = (e) => { if (e.target === dlg) cleanup(false); };
                const onKey = (e) => {
                    if (e.key === 'Escape') cleanup(false);
                    else if (e.key === 'Enter') cleanup(true);
                };
                okBtn.addEventListener('click', onOk);
                cancelBtn.addEventListener('click', onCancel);
                dlg.addEventListener('click', onBackdrop);
                document.addEventListener('keydown', onKey);
                setTimeout(() => okBtn.focus(), 50);
            });
        }
        window.showConfirm = showConfirm;

        window.goHome = () => goToStep(0);

        // === INIT ===
        loadingManager = new LoadingComponent();
        initFolderPicker();
