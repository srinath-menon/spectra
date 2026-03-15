import json

def get_gallery_html(images_data):
    # 1. Prepare dynamic data
    folders = sorted(list({img['folder'] for img in images_data if img['folder'] and img['folder'] != '.'}))
    folder_links_html = "".join([f'<div class="folder-link" onclick="filterByFolder(\'{f}\')">📁 {f}</div>' for f in folders])
    images_json = json.dumps(images_data)

    # 2. The Full Template
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Spectra</title>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
        <style>
            body { font-family: -apple-system, system-ui, sans-serif; background: #000; color: #eee; margin: 0; overflow-x: hidden; }
            header { background: #1a1a1a; padding: 10px 15px; position: sticky; top: 0; z-index: 100; border-bottom: 1px solid #333; display: flex; align-items: center; justify-content: space-between; gap: 10px; height: 50px; box-sizing: border-box; }
            h1 { margin: 0; cursor: pointer; font-size: 1.1rem; flex-shrink: 0; }
            
            #current-folder-label { font-size: 0.85rem; color: #888; font-weight: bold; flex-grow: 1; text-align: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
            
            .nav-controls { display: flex; gap: 8px; flex-shrink: 0; }
            button { background: #333; border: 1px solid #444; color: white; padding: 6px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85rem; }
            button.active { background: #007aff; border-color: #005bb7; }
            #batch-fav-btn { background: #ff3b30; display: none; }

            #folder-drawer { display: none; background: #111; padding: 20px; border-bottom: 1px solid #333; max-height: 300px; overflow-y: auto; position: sticky; top: 50px; z-index: 99; }
            .folder-link { display: block; padding: 10px 0; color: #aaa; cursor: pointer; border-bottom: 1px solid #222; }
            
            .gallery { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; padding: 15px; }
            .img-card { width: 150px; height: 150px; overflow: hidden; border-radius: 4px; cursor: pointer; background: #111; position: relative; border: 2px solid transparent; }
            .img-card img { width: 100%; height: 100%; object-fit: cover; pointer-events: none; }
            
            .img-card.selected { border-color: #007aff; }
            .img-card.selected::after { content: '✓'; position: absolute; top: 5px; right: 5px; background: #007aff; color: white; border-radius: 50%; width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold; }

            #lightbox { display: none; position: fixed; z-index: 1000; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.95); align-items: center; justify-content: center; overflow: hidden; touch-action: none; }
            #lightbox img { max-width: 100%; max-height: 100%; width: 100vw; height: 100vh; object-fit: contain; transform-origin: center; cursor: grab; transition: transform 0.1s ease-out; }
            #lightbox img:active { cursor: grabbing; }

            .close { position: absolute; top: 20px; right: 20px; font-size: 35px; color: #fff; cursor: pointer; z-index: 1010; }
            #fav-btn { position: absolute; bottom: 40px; right: 40px; font-size: 40px; background: rgba(255,255,255,0.1); border-radius: 50%; width: 70px; height: 70px; display: flex; align-items: center; justify-content: center; cursor: pointer; z-index: 1010; border: 1px solid rgba(255,255,255,0.3); }
            
            #loading-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); z-index: 2000; color: white; flex-direction: column; align-items: center; justify-content: center; }
            .progress-container { width: 200px; height: 6px; background: #333; border-radius: 3px; margin-top: 15px; overflow: hidden; }
            #progress-bar { width: 0%; height: 100%; background: #007aff; transition: width 0.2s; }
            
            #sentinel { height: 100px; width: 100%; }
        </style>
    </head>
    <body>
        <div id="loading-overlay">
            <h2 id="loading-text">Working...</h2>
            <div class="progress-container"><div id="progress-bar"></div></div>
        </div>

        <header>
            <h1 onclick="resetFilter()">💎 Spectra</h1>
            <div id="current-folder-label">Loading...</div>
            <div class="nav-controls">
                <button id="batch-fav-btn" onclick="submitBatchFavorite()">❤️ Move</button>
                <button id="select-mode-btn" onclick="toggleSelectMode()">Select</button>
                <button onclick="toggleFolders()">📂</button>
            </div>
        </header>
        
        <div id="folder-drawer">
            <div class="folder-link" onclick="resetFilter()">🏠 [All Photos]</div>
            {{FOLDER_LINKS}}
        </div>

        <div id="gallery-container" class="gallery"></div>
        <div id="sentinel"></div>

        <div id="lightbox">
            <span class="close" onclick="closeLightbox()">&times;</span>
            <div id="fav-btn" onclick="favoriteCurrent()">❤️</div>
            <img id="lightbox-img" src="" draggable="false">
        </div>

        <script>
            const allImages = {{IMAGES_JSON}};
            let filteredImages = [...allImages];
            let selectedPaths = new Set();
            let isSelectMode = false;
            let currentFolderName = ".";
            let loadedCount = 0;
            let currentIndex = 0;

            // Zoom State
            let scale = 1, pointX = 0, pointY = 0, start = { x: 0, y: 0 }, isPanning = false;

            const container = document.getElementById('gallery-container');
            const folderLabel = document.getElementById('current-folder-label');
            const lbImg = document.getElementById('lightbox-img');

            function updateLabel(name, count) { folderLabel.innerText = name + " [" + count + "]"; }
            function toggleFolders() { const d = document.getElementById('folder-drawer'); d.style.display = d.style.display === 'block' ? 'none' : 'block'; }
            
            function toggleSelectMode() { 
                isSelectMode = !isSelectMode; 
                document.getElementById('select-mode-btn').classList.toggle('active', isSelectMode);
                if(!isSelectMode) { selectedPaths.clear(); document.querySelectorAll('.img-card').forEach(c => c.classList.remove('selected')); }
                updateBatchBtn();
            }
            
            function updateBatchBtn() { document.getElementById('batch-fav-btn').style.display = (isSelectMode && selectedPaths.size > 0) ? 'block' : 'none'; }

            function handleCardClick(idx, el) {
                if (isSelectMode) {
                    const src = filteredImages[idx].src;
                    if (selectedPaths.has(src)) { selectedPaths.delete(src); el.classList.remove('selected'); }
                    else { selectedPaths.add(src); el.classList.add('selected'); }
                    updateBatchBtn();
                } else { openLightbox(idx); }
            }

            function startProgress(text) {
                const overlay = document.getElementById('loading-overlay');
                document.getElementById('loading-text').innerText = text;
                overlay.style.display = 'flex';
                let w = 0;
                const inv = setInterval(() => {
                    if (w >= 90) clearInterval(inv);
                    else { w += (90 - w) * 0.1; document.getElementById('progress-bar').style.width = w + '%'; }
                }, 150);
                return inv;
            }

            async function submitBatchFavorite() {
                if (!confirm(`Move ${selectedPaths.size} files?`)) return;
                const inv = startProgress("Moving batch...");
                const res = await fetch('/favorite_batch', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ paths: Array.from(selectedPaths) }) });
                if (res.ok) { 
                    clearInterval(inv); 
                    document.getElementById('progress-bar').style.width = '100%';
                    location.hash = encodeURIComponent(currentFolderName);
                    setTimeout(() => location.reload(), 300);
                }
            }

            async function favoriteCurrent() {
                const inv = startProgress("Moving file...");
                const res = await fetch('/favorite', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path: filteredImages[currentIndex].src }) });
                if (res.ok) { location.hash = encodeURIComponent(currentFolderName); location.reload(); }
            }

            function openLightbox(idx) {
                currentIndex = idx; scale = 1; pointX = 0; pointY = 0;
                lbImg.style.transform = `translate(0px, 0px) scale(1)`;
                lbImg.src = filteredImages[idx].src;
                document.getElementById('lightbox').style.display = 'flex';
                document.body.style.overflow = 'hidden';
            }
            
            function closeLightbox() { document.getElementById('lightbox').style.display = 'none'; document.body.style.overflow = 'auto'; }

            // Zoom/Pan Logic
            document.getElementById('lightbox').onwheel = (e) => {
                e.preventDefault();
                scale = e.deltaY > 0 ? Math.max(1, scale - 0.2) : Math.min(5, scale + 0.2);
                if (scale === 1) { pointX = 0; pointY = 0; }
                lbImg.style.transform = `translate(${pointX}px, ${pointY}px) scale(${scale})`;
            };

            lbImg.onmousedown = (e) => { if (scale > 1) { isPanning = true; start = { x: e.clientX - pointX, y: e.clientY - pointY }; } };
            window.onmousemove = (e) => { if (isPanning) { pointX = e.clientX - start.x; pointY = e.clientY - start.y; lbImg.style.transform = `translate(${pointX}px, ${pointY}px) scale(${scale})`; } };
            window.onmouseup = () => isPanning = false;

            function filterByFolder(f) { currentFolderName = f; filteredImages = allImages.filter(i => i.folder === f); updateLabel(f, filteredImages.length); resetView(); }
            function resetFilter() { currentFolderName = "."; filteredImages = [...allImages]; updateLabel("[All Photos]", filteredImages.length); resetView(); }
            function resetView() { container.innerHTML = ''; loadedCount = 0; selectedPaths.clear(); updateBatchBtn(); loadMore(); window.scrollTo(0,0); const d = document.getElementById('folder-drawer'); if(d.style.display==='block') d.style.display='none'; }

            function loadMore() {
                const step = loadedCount === 0 ? 10 : 50;
                const chunk = filteredImages.slice(loadedCount, loadedCount + step);
                chunk.forEach((img, i) => {
                    const gIdx = loadedCount + i;
                    const card = document.createElement('div');
                    card.className = 'img-card';
                    card.onclick = () => handleCardClick(gIdx, card);
                    card.innerHTML = `<img src="${img.src}" loading="lazy">`;
                    container.appendChild(card);
                });
                loadedCount += chunk.length;
            }

            const obs = new IntersectionObserver(e => { if(e[0].isIntersecting && loadedCount < filteredImages.length) loadMore(); }, { rootMargin: '400px' });
            obs.observe(document.getElementById('sentinel'));

            document.addEventListener('keydown', e => {
                if (document.getElementById('lightbox').style.display === 'flex') {
                    if (e.key === "ArrowRight") openLightbox((currentIndex + 1) % filteredImages.length);
                    else if (e.key === "ArrowLeft") openLightbox((currentIndex - 1 + filteredImages.length) % filteredImages.length);
                    else if (e.key === "Escape") closeLightbox();
                    else if (e.key.toLowerCase() === "f") favoriteCurrent();
                }
            });

            window.addEventListener('DOMContentLoaded', () => {
                const h = window.location.hash.substring(1);
                if (h && allImages.some(i => i.folder === decodeURIComponent(h))) filterByFolder(decodeURIComponent(h));
                else resetFilter();
            });
        </script>
    </body>
    </html>
    """

    # 3. Final Injection
    html_template = html_template.replace("{{FOLDER_LINKS}}", folder_links_html)
    html_template = html_template.replace("{{IMAGES_JSON}}", images_json)
    
    return html_template