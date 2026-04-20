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
                this.options = {
                    size: 'medium',
                    color: 'primary',
                    customColor: '#4caf50',
                    speed: 1,
                    mode: 'circular',
                    text: 'Processando...',
                    fadeInMs: 400,
                    fadeOutMs: 250,
                    minVisibleMs: 240
                };
                this.setOptions({});
            }

            setOptions(partial) {
                this.options = { ...this.options, ...partial };
                const safeSize = ['small', 'medium', 'large'].includes(this.options.size) ? this.options.size : 'medium';
                const safeColor = ['primary', 'secondary', 'custom'].includes(this.options.color) ? this.options.color : 'primary';
                const safeMode = ['circular', 'linear'].includes(this.options.mode) ? this.options.mode : 'circular';
                this.el.classList.remove('loading-size-small', 'loading-size-medium', 'loading-size-large');
                this.el.classList.remove('loading-color-primary', 'loading-color-secondary', 'loading-color-custom');
                this.el.classList.remove('loading-mode-circular', 'loading-mode-linear');
                this.el.classList.add(`loading-size-${safeSize}`, `loading-color-${safeColor}`, `loading-mode-${safeMode}`);
                this.el.style.setProperty('--loading-custom', this.options.customColor || '#4caf50');
                this.el.style.setProperty('--loading-speed', `${Math.max(0.2, Number(this.options.speed) || 1)}s`);
                this.el.style.setProperty('--loading-fade-in', `${Math.max(300, Math.min(500, Number(this.options.fadeInMs) || 400))}ms`);
                this.el.style.setProperty('--loading-fade-out', `${Math.max(200, Math.min(300, Number(this.options.fadeOutMs) || 250))}ms`);
                if (this.options.text) this.setText(this.options.text);
            }

            setText(text) {
                this.textEl.textContent = text || '';
            }

            show(text, opts = {}) {
                this.setOptions(opts);
                if (text) this.setText(text);
                const token = Symbol('loading');
                this.pending.add(token);
                if (this.pending.size === 1) {
                    this.startedAt = Date.now();
                    clearTimeout(this.hideTimer);
                    this.el.classList.remove('is-hiding');
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
                const minVisibleMs = Math.max(0, Number(this.options.minVisibleMs) || 0);
                const wait = Math.max(0, minVisibleMs - (Date.now() - this.startedAt));
                clearTimeout(this.hideTimer);
                this.hideTimer = setTimeout(() => {
                    this.el.classList.remove('is-visible');
                    this.el.classList.add('is-hiding');
                    this.el.setAttribute('aria-busy', 'false');
                    const fadeOutMs = Math.max(200, Math.min(300, Number(this.options.fadeOutMs) || 250));
                    setTimeout(() => {
                        if (this.pending.size === 0) {
                            this.el.classList.remove('is-hiding');
                            this.el.setAttribute('aria-hidden', 'true');
                        }
                    }, fadeOutMs);
                }, wait);
            }

            async withLoading(promiseFactory, opts = {}) {
                const token = this.show(opts.text, opts);
                try {
                    return await promiseFactory();
                } finally {
                    this.hide(token);
                }
            }

            async fetchJson(url, options = {}, loadingOpts = {}) {
                return this.withLoading(async () => {
                    const res = await fetch(url, options);
                    const data = await res.json();
                    return { res, data };
                }, loadingOpts);
            }
        }

        // === NAVIGATION ===
        function goToStep(step) {
            if (step > currentStep) return; // Can't skip ahead

            // Leave current step
            if (currentStep === 1) stopWebcam();

            document.querySelectorAll('.content').forEach(el => el.classList.add('hidden'));
            document.getElementById(`step${step}`).classList.remove('hidden');

            document.querySelectorAll('.step').forEach(el => {
                const s = parseInt(el.dataset.step);
                el.className = `step ${s < step ? 'completed' : s === step ? 'active' : 'inactive'}`;
            });

            currentStep = step;

            // Enter new step
            if (step === 1) startWebcam();
        }

        function advanceTo(step) {
            currentStep = step - 1; // Allow advancing
            goToStepForce(step);
        }

        function goToStepForce(step) {
            if (step === 1) stopWebcam();
            document.querySelectorAll('.content').forEach(el => el.classList.add('hidden'));
            document.getElementById(`step${step}`).classList.remove('hidden');

            document.querySelectorAll('.step').forEach(el => {
                const s = parseInt(el.dataset.step);
                el.className = `step ${s < step ? 'completed' : s === step ? 'active' : 'inactive'}`;
            });

            currentStep = step;
            if (step === 1) startWebcam();
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
            if (recents.length === 0) { section.style.display = 'none'; return; }
            section.style.display = 'block';
            list.innerHTML = '';
            recents.forEach(r => {
                const item = document.createElement('div');
                item.className = 'recent-item';
                const name = r.path.split(/[\\\/]/).pop() || r.path;
                item.innerHTML = `
                    <div>
                        <div style="font-weight:600">📁 ${name}</div>
                        <div class="recent-path">${r.path}</div>
                    </div>
                    <div class="recent-count">📷 ${r.count} fotos</div>
                `;
                item.onclick = () => {
                    document.getElementById('pathInput').value = r.path;
                    confirmFolder();
                };
                list.appendChild(item);
            });
        }

        async function browseFolder() {
            const btn = document.querySelector('#step0 .btn-green');
            btn.disabled = true;
            btn.textContent = '⏳ Abrindo...';
            try {
                const res = await fetch('/api/browse-folder');
                const data = await res.json();
                if (data.ok && data.path) {
                    document.getElementById('pathInput').value = data.path;
                    await confirmFolder();
                }
            } finally {
                btn.disabled = false;
                btn.textContent = '📂 Procurar...';
            }
        }

        async function confirmFolder() {
            const path = document.getElementById('pathInput').value.trim();
            const info = document.getElementById('pathInfo');
            if (!path) { info.className = 'path-info err'; info.textContent = '⚠ Digite o caminho da pasta.'; return; }

            const { data } = await requestJson('/api/session/select', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({path})
            }, {
                text: 'Selecionando sessão...'
            });

            if (!data.ok) {
                info.className = 'path-info err';
                info.textContent = `❌ ${data.message}`;
                return;
            }

            info.className = 'path-info ok';
            info.textContent = `✅ ${data.count} foto(s) encontrada(s) em: ${data.path}`;
            saveRecent(data.path, data.count);

            sessionPath = data.path;
            sessionPhotoCount = Number(data.count || 0);
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
                loadingToken = showLoading('Capturando e processando rosto...', {
                    size: 'medium',
                    color: 'primary',
                    mode: 'circular',
                    speed: 0.95
                });
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

        function addFaceChip(imgSrc) {
            const container = document.getElementById('capturedFaces');
            const chip = document.createElement('div');
            chip.className = 'face-chip';
            chip.innerHTML = `<img src="${imgSrc}"><button class="remove" onclick="this.parentElement.remove()">×</button>`;
            container.appendChild(chip);
        }

        async function uploadPhotos(files) {
            if (!files || files.length === 0) return;

            let loadingToken = null;
            try {
                loadingToken = showLoading('Enviando foto e detectando rostos...', {
                    size: 'medium',
                    color: 'primary',
                    mode: 'linear',
                    speed: 0.9
                });
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

            progress.style.display = 'none';
            fill.style.width = '0%';
            text.textContent = progressText(0, fallbackTotal, 0);
            grid.innerHTML = '';
            document.getElementById('gridStatus').textContent = fallbackTotal > 0
                ? `Buscando... 0/${fallbackTotal} processadas`
                : `Buscando...`;

            const loadingToken = showLoading(progressText(0, fallbackTotal, 0), {
                size: 'medium',
                color: 'primary',
                mode: 'linear',
                speed: 0.9
            });

            try {
                const startRes = await fetch('/api/scan', { method: 'POST' });
                const startData = await startRes.json();
                if (!startData.ok) {
                    showSnackbar(startData.message || 'Erro ao iniciar scan');
                    return;
                }
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
                    const txt = progressText(done, total, percent);
                    text.textContent = txt;
                    if (loadingManager) loadingManager.setText(txt);
                    if (total > 0) {
                        document.getElementById('gridStatus').textContent =
                            `Buscando... ${done}/${total} processadas • ${Math.max(0, total - done)} restantes`;
                    }

                    if (j.status === 'done') {
                        fill.style.width = '100%';
                        const finalText = total > 0
                            ? `Concluído! • ${total}/${total} processadas • 0 restantes`
                            : `Concluído!`;
                        text.textContent = finalText;
                        if (loadingManager) loadingManager.setText(finalText);

                        matchResults = j.matches || [];
                        selectedPhotos = new Set(matchResults.map(m => m.file_path));
                        matchResults.forEach(m => { orientations[m.file_path] = 'landscape'; });
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

        function renderPhotoGrid() {
            const grid = document.getElementById('photoGrid');
            grid.innerHTML = '';

            if (matchResults.length === 0) {
                grid.innerHTML = '<div style="text-align:center;padding:40px;color:#666;width:100%">🔍 Nenhuma foto encontrada</div>';
                return;
            }

            matchResults.forEach((m, idx) => {
                const isSelected = selectedPhotos.has(m.file_path);
                const confClass = m.confidence >= 70 ? 'conf-high' : m.confidence >= 50 ? 'conf-med' : 'conf-low';

                const card = document.createElement('div');
                card.className = `photo-card ${isSelected ? 'selected' : ''}`;
                card.dataset.path = m.file_path;
                card.innerHTML = `
                    <img src="${m.thumbnail_url}" loading="lazy"
                         onclick="showModal(${idx})">
                    <div class="photo-card-footer">
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer">
                            <input type="checkbox" ${isSelected ? 'checked' : ''}
                                   onchange="togglePhoto('${m.file_path.replace(/\\/g, '\\\\')}', this.checked)">
                            <span class="confidence-badge ${confClass}">${m.confidence}%</span>
                        </label>
                        <select class="orient-select"
                                onchange="orientations['${m.file_path.replace(/\\/g, '\\\\')}'] = this.value">
                            <option value="landscape">Paisagem</option>
                            <option value="portrait">Retrato</option>
                        </select>
                    </div>
                `;
                grid.appendChild(card);
            });
        }

        function togglePhoto(path, checked) {
            if (checked) selectedPhotos.add(path);
            else selectedPhotos.delete(path);

            // Update card visual
            document.querySelectorAll('.photo-card').forEach(card => {
                if (card.dataset.path === path) {
                    card.classList.toggle('selected', checked);
                }
            });

            document.getElementById('gridStatus').textContent =
                `${matchResults.length} fotos encontradas, ${selectedPhotos.size} selecionadas`;
        }

        function toggleSelectAll() {
            const allSelected = selectedPhotos.size === matchResults.length;
            if (allSelected) {
                selectedPhotos.clear();
            } else {
                matchResults.forEach(m => selectedPhotos.add(m.file_path));
            }
            renderPhotoGrid();
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
                const { data } = await requestJson('/api/compose', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        selected: Array.from(selectedPhotos),
                        orientations: orientations
                    })
                }, {
                    text: 'Compondo imagens...',
                    mode: 'linear',
                    color: 'secondary'
                });

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

            composedFiles.forEach((f, idx) => {
                const card = document.createElement('div');
                card.className = 'preview-card';
                const url = `/api/output/${encodeOutputPath(f.filename)}`;
                const label = f.filename.split('/').pop();
                card.innerHTML = `
                    <img src="${url}"
                         onclick="showModal(${idx}, 'composed')"
                         loading="lazy">
                    <div class="preview-card-info">${label}</div>
                `;
                grid.appendChild(card);
            });
        }

        // === PRINT ===
        async function printAll() {
            try {
                const { data } = await requestJson('/api/print', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({files: composedFiles})
                }, {
                    text: 'Enviando para impressão...',
                    size: 'small'
                });
                showSnackbar(`${data.printed} imagem(ns) abertas — clique em Imprimir no visualizador para escolher a impressora`);
            } catch (err) {
                showSnackbar('Erro: ' + err.message);
            }
        }

        function saveAll() {
            showSnackbar(`${composedFiles.length} imagens já salvas na pasta output/`);
        }

        // === UI HELPERS ===
        function showSnackbar(msg) {
            const el = document.getElementById('snackbar');
            el.textContent = msg;
            el.classList.add('show');
            setTimeout(() => el.classList.remove('show'), 3000);
        }

        function showLoading(text, options = {}) {
            if (!loadingManager) {
                loadingManager = new LoadingComponent();
            }
            return loadingManager.show(text, options);
        }

        function hideLoading(token = null) {
            if (!loadingManager) return;
            loadingManager.hide(token);
        }

        async function requestJson(url, options = {}, loadingOptions = {}) {
            if (!loadingManager) {
                loadingManager = new LoadingComponent();
            }
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
            document.getElementById('imageModal').classList.add('show');
            document.addEventListener('keydown', carouselKeyHandler);
        }

        function closeModal() {
            document.getElementById('imageModal').classList.remove('show');
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

        // === INIT ===
        loadingManager = new LoadingComponent();
        initFolderPicker();
