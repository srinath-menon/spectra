import json

def get_gallery_html(images_data):
    folders = sorted(list({img['folder'] for img in images_data if img['folder'] and img['folder'] != '.'}))
    folder_links_html = "".join([f'<div class="folder-link" onclick="filterByFolder(\'{f}\')">📁 {f}</div>' for f in folders])
    images_json = json.dumps(images_data)

    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Spectra</title>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
        <style>
            body { font-family: -apple-system, system-ui, sans-serif; background: #000; color: #eee; margin: 0; }
            header { background: #1a1a1a; padding: 10px 15px; position: sticky; top: 0; z-index: 100; border-bottom: 1px solid #333; display: flex; align-items: center; justify-content: space-between; gap: 10px; }
            h1 { margin: 0; cursor: pointer; font-size: 1.1rem; }
            #current-folder-label { font-size: 0.85rem; color: #888; font-weight: bold; flex-grow: 1; text-align: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
            
            .nav-controls { display: flex; gap: 8px; }
            button { background: #333; border: 1px solid #444; color: white; padding: 6px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85rem; }
            button.active { background: #007aff; border-color: #005bb7; }
            #batch-fav-btn { background: #ff3b30; display: none; }

            #folder-drawer { display: none; background: #111; padding: 20px; border-bottom: 1px solid #333; max-height: 300px; overflow-y: auto; position: sticky; top: 50px; z-index: 99; }
            .folder-link { display: block; padding: 10px 0; color: #aaa; cursor: pointer; border-bottom: 1px solid #222; }
            
            .gallery { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; padding: 15px; }
            .img-card { width: 150px; height: 150px; overflow: hidden; border-radius: 4px; cursor: pointer; background: #111; position: relative; border: 2px solid transparent; transition: transform 0.1s; }
            .img-card img { width: 100%; height: 100%; object-fit: cover; }
            
            .img-card.selected { border-color: #007aff; transform: scale(0.95); }
            .img-card.selected::after { content: '✓'; position: absolute; top: 5px; right: 5px; background: #007aff; color: white; border-radius: 50%; width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold; }

            /* Lightbox & Zoom Styles */
            #lightbox { 
                display: none; position: fixed; z-index: 1000; top: 0; left: 0; 
                width: 100vw; height: 100vh; background: rgba(0,0,0,0.95); 
                align-items: center; justify-content: center; overflow: hidden;
                touch-action: none; /* Prevents browser pull-to-refresh while zooming */
            }
            #lightbox img { 
                /* Ensure it starts from a consistent base */
                width: 100vw;
                height: 100vh;
                object-fit: contain; 
                
                transition: transform 0.1s ease-out; /* For zoom/pan */
                cursor: grab;
                transform-origin: center;
                display: block;
            }
            #lightbox img:active { cursor: grabbing; }

            .close { position: absolute; top: 20px; right: 20px; font-size: 35px; color: #fff; cursor: pointer; z-index: 1010; text-shadow: 0 0 10px #000; }
            #fav-btn { position: absolute; bottom: 40px; right: 40px; font-size: 40px; background: rgba(255,255,255,0.1); border-radius: 50%; width: 70px; height: 70px; display: flex; align-items: center; justify-content: center; cursor: pointer; z-index: 1010; border: 1px solid rgba(255,255,255,0.3); }
            
            #loading-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 2000; color: white; flex-direction: column; align-items: center; justify-content: center; }
            #sentinel { height: 100px; width: 100%; }
        </style>
    </head>
    <body>
        <div id="loading-overlay"><h2>Processing...</h2></div>
        <header>
            <h1 onclick="resetFilter()">💎 Spectra</h1>
            <div id="current-folder-label">[All Photos]</div>
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

            // Zoom & Pan State
            let scale = 1;
            let pointX = 0;
            let pointY = 0;
            let start = { x: 0, y: 0 };
            let isPanning = false;

            const container = document.getElementById('gallery-container');
            const folderLabel = document.getElementById('current-folder-label');
            const lightbox = document.getElementById('lightbox');
            const lbImg = document.getElementById('lightbox-img');

            function setTransform() {
                lbImg.style.transform = `translate(${pointX}px, ${pointY}px) scale(${scale})`;
            }

            // Mouse Wheel Zoom
            lightbox.onwheel = function (e) {
                e.preventDefault();
                const delta = e.deltaY;
                const zoomSpeed = 0.1;
                if (delta > 0) {
                    scale = Math.max(1, scale - zoomSpeed);
                } else {
                    scale = Math.min(5, scale + zoomSpeed);
                }
                if (scale === 1) { pointX = 0; pointY = 0; }
                setTransform();
            }

            // Panning Logic
            lbImg.onmousedown = function (e) {
                if (scale === 1) return;
                e.preventDefault();
                start = { x: e.clientX - pointX, y: e.clientY - pointY };
                isPanning = true;
            }

            window.onmousemove = function (e) {
                if (!isPanning) return;
                e.preventDefault();
                pointX = e.clientX - start.x;
                pointY = e.clientY - start.y;
                setTransform();
            }

            window.onmouseup = function () { isPanning = false; }

            function openLightbox(index) {
                currentIndex = index;
                
                // Reset zoom/pan state immediately
                scale = 1; 
                pointX = 0; 
                pointY = 0;
                setTransform();
                
                // Set source and display
                lbImg.src = filteredImages[currentIndex].src;
                lightbox.style.display = 'flex';
                
                // Lock scroll
                document.body.style.overflow = 'hidden'; 
            }

            function closeLightbox() {
                lightbox.style.display = 'none';
                document.body.style.overflow = 'auto';
            }

            // Existing logic remains below...
            function updateLabel(name, count) { folderLabel.innerText = name + " [" + count + "]"; }
            function toggleFolders() { const d = document.getElementById('folder-drawer'); d.style.display = d.style.display === 'block' ? 'none' : 'block'; }
            function toggleSelectMode() { isSelectMode = !isSelectMode; document.getElementById('select-mode-btn').classList.toggle('active', isSelectMode); if(!isSelectMode){ selectedPaths.clear(); renderSelection(); } updateBatchButton(); }
            function updateBatchButton() { document.getElementById('batch-fav-btn').style.display = (isSelectMode && selectedPaths.size > 0) ? 'block' : 'none'; }
            function renderSelection() { document.querySelectorAll('.img-card').forEach(c => c.classList.remove('selected')); }
            
            function handleCardClick(index, element) {
                if (isSelectMode) {
                    const src = filteredImages[index].src;
                    if (selectedPaths.has(src)) { selectedPaths.delete(src); element.classList.remove('selected'); }
                    else { selectedPaths.add(src); element.classList.add('selected'); }
                    updateBatchButton();
                } else { openLightbox(index); }
            }

            async function submitBatchFavorite() {
                const count = selectedPaths.size;
                if (count === 0) return;

                if (confirm(`Move ${count} files to Favorites?`)) {
                    document.getElementById('loading-overlay').style.display = 'flex';
                    try {
                        const res = await fetch('/favorite_batch', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ paths: Array.from(selectedPaths) })
                        });
                        
                        if (res.ok) {
                            // First, update the hash so the browser knows where to go
                            if (currentFolderName !== ".") {
                                location.hash = encodeURIComponent(currentFolderName);
                            } else {
                                location.hash = "";
                            }
                            // Then reload the page
                            location.reload();
                        } else {
                            document.getElementById('loading-overlay').style.display = 'none';
                            alert("Server error: Could not move files.");
                        }
                    } catch (err) {
                        document.getElementById('loading-overlay').style.display = 'none';
                        console.error("Fetch error:", err);
                    }
                }
            }

            function filterByFolder(f) { currentFolderName = f; filteredImages = allImages.filter(img => img.folder === f); updateLabel(f, filteredImages.length); applyFilterUpdate(); toggleFolders(); }
            function resetFilter() { currentFolderName = "."; filteredImages = [...allImages]; updateLabel("[All Photos]", filteredImages.length); applyFilterUpdate(); if(document.getElementById('folder-drawer').style.display === 'block') toggleFolders(); }
            function applyFilterUpdate() { container.innerHTML = ''; loadedCount = 0; selectedPaths.clear(); updateBatchButton(); loadMore(); window.scrollTo(0, 0); }

            function loadMore() {
                const size = (loadedCount === 0) ? 10 : 50;
                const next = filteredImages.slice(loadedCount, loadedCount + size);
                next.forEach((img, i) => {
                    const div = document.createElement('div');
                    div.className = 'img-card';
                    const globalIdx = loadedCount + i;
                    div.onclick = function() { handleCardClick(globalIdx, this); };
                    div.innerHTML = `<img src="${img.src}" loading="lazy">`;
                    container.appendChild(div);
                });
                loadedCount += next.length;
            }

            const observer = new IntersectionObserver((e) => { if (e[0].isIntersecting && loadedCount < filteredImages.length) loadMore(); }, { rootMargin: '400px' });
            observer.observe(document.getElementById('sentinel'));

            async function favoriteCurrent() {
                const imgPath = filteredImages[currentIndex].src;
                const response = await fetch('/favorite', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: imgPath })
                });
                if (response.ok) {
                    if (currentFolderName !== ".") {
                        location.hash = encodeURIComponent(currentFolderName);
                    } else {
                        location.hash = "";
                    }
                    location.reload();
                }
            }

            document.addEventListener('keydown', (e) => {
                if (lightbox.style.display === 'flex') {
                    if (e.key === "ArrowRight") { currentIndex = (currentIndex + 1) % filteredImages.length; openLightbox(currentIndex); }
                    else if (e.key === "ArrowLeft") { currentIndex = (currentIndex - 1 + filteredImages.length) % filteredImages.length; openLightbox(currentIndex); }
                    else if (e.key === "Escape") closeLightbox();
                    else if (e.key.toLowerCase() === "f") favoriteCurrent();
                }
            });

            window.addEventListener('DOMContentLoaded', () => {
                const hash = window.location.hash.substring(1);
                if (hash) {
                    const f = decodeURIComponent(hash);
                    if (allImages.some(i => i.folder === f)) { filterByFolder(f); document.getElementById('folder-drawer').style.display = 'none'; return; }
                }
                resetFilter();
            });
        </script>
    </body>
    </html>
    """

    html_template = html_template.replace("{{FOLDER_LINKS}}", folder_links_html)
    html_template = html_template.replace("{{IMAGES_JSON}}", images_json)
    return html_template