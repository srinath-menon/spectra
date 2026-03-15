import json

def get_gallery_html(images_data):
    # 1. Prepare the dynamic parts
    folders = sorted(list({img['folder'] for img in images_data if img['folder'] and img['folder'] != '.'}))
    folder_links_html = "".join([f'<div class="folder-link" onclick="filterByFolder(\'{f}\')">📁 {f}</div>' for f in folders])
    images_json = json.dumps(images_data)

    # 2. The Clean HTML Template
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Spectra</title>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
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

            #lightbox { display: none; position: fixed; z-index: 1000; top: 0; left: 0; width: 100vw; height: 100vh; background: #000; align-items: center; justify-content: center; }
            #lightbox img { width: 100%; height: 100%; object-fit: contain; }
            .close { position: absolute; top: 20px; right: 20px; font-size: 30px; cursor: pointer; z-index: 1010; }
            #fav-btn { position: absolute; bottom: 40px; right: 40px; font-size: 40px; background: rgba(255,255,255,0.2); border-radius: 50%; width: 70px; height: 70px; display: flex; align-items: center; justify-content: center; cursor: pointer; z-index: 1010; }
            #sentinel { height: 100px; width: 100%; }
            
            /* Loading Overlay */
            #loading-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 2000; color: white; flex-direction: column; align-items: center; justify-content: center; }
        </style>
    </head>
    <body>
        <div id="loading-overlay">
            <h2>Processing Move...</h2>
            <p>The gallery will refresh shortly.</p>
        </div>

        <header>
            <h1 onclick="resetFilter()">💎 Spectra</h1>
            <div id="current-folder-label">[All Photos]</div>
            <div class="nav-controls">
                <button id="batch-fav-btn" onclick="submitBatchFavorite()">❤️ Move Selected</button>
                <button id="select-mode-btn" onclick="toggleSelectMode()">Select</button>
                <button onclick="toggleFolders()">📂 Folders</button>
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
            <img id="lightbox-img" src="" onclick="closeLightbox()">
        </div>

        <script>
            const allImages = {{IMAGES_JSON}};
            let filteredImages = [...allImages];
            let selectedPaths = new Set();
            let isSelectMode = false;
            
            let loadedCount = 0;
            let currentIndex = 0;
            
            const container = document.getElementById('gallery-container');
            const folderLabel = document.getElementById('current-folder-label');
            const selectBtn = document.getElementById('select-mode-btn');
            const batchFavBtn = document.getElementById('batch-fav-btn');
            const loader = document.getElementById('loading-overlay');

            function updateLabel(name, count) {
                folderLabel.innerText = name + " [" + count + "]";
            }

            function toggleSelectMode() {
                isSelectMode = !isSelectMode;
                selectBtn.classList.toggle('active', isSelectMode);
                if (!isSelectMode) {
                    selectedPaths.clear();
                    renderSelection();
                }
                updateBatchButton();
            }

            function updateBatchButton() {
                batchFavBtn.style.display = (isSelectMode && selectedPaths.size > 0) ? 'block' : 'none';
            }

            function handleCardClick(index, element) {
                const img = filteredImages[index];
                if (isSelectMode) {
                    if (selectedPaths.has(img.src)) {
                        selectedPaths.delete(img.src);
                        element.classList.remove('selected');
                    } else {
                        selectedPaths.add(img.src);
                        element.classList.add('selected');
                    }
                    updateBatchButton();
                } else {
                    openLightbox(index);
                }
            }

            function renderSelection() {
                const cards = document.querySelectorAll('.img-card');
                cards.forEach((card) => {
                    card.classList.remove('selected');
                });
            }

            async function submitBatchFavorite() {
                const count = selectedPaths.size;
                if (count === 0) return;

                if (confirm(`Move ${count} files to Favorites?`)) {
                    loader.style.display = 'flex'; // Show processing overlay
                    try {
                        const res = await fetch('/favorite_batch', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ paths: Array.from(selectedPaths) })
                        });
                        
                        if (res.ok) {
                            alert("Success! " + count + " files moved. Refreshing now...");
                            location.reload();
                        } else {
                            loader.style.display = 'none';
                            alert("Server error: Could not move files.");
                        }
                    } catch (err) {
                        loader.style.display = 'none';
                        console.error("Fetch error:", err);
                    }
                }
            }

            function toggleFolders() {
                const drawer = document.getElementById('folder-drawer');
                drawer.style.display = drawer.style.display === 'block' ? 'none' : 'block';
            }

            function filterByFolder(folderPath) {
                filteredImages = allImages.filter(img => img.folder === folderPath);
                updateLabel(folderPath, filteredImages.length);
                applyFilterUpdate();
                toggleFolders();
            }

            function resetFilter() {
                filteredImages = [...allImages];
                updateLabel("[All Photos]", filteredImages.length);
                applyFilterUpdate();
                if(document.getElementById('folder-drawer').style.display === 'block') toggleFolders();
            }

            function applyFilterUpdate() {
                container.innerHTML = '';
                loadedCount = 0;
                selectedPaths.clear();
                updateBatchButton();
                loadMore();
                window.scrollTo(0, 0);
            }

            function loadMore() {
                // PERFORMANCE ENHANCEMENT: 
                // Load 10 images if it's the very first batch, otherwise load 50.
                const currentBatchSize = (loadedCount === 0) ? 10 : 50;
                
                const nextBatch = filteredImages.slice(loadedCount, loadedCount + currentBatchSize);
                nextBatch.forEach((imgData, index) => {
                    const globalIndex = loadedCount + index;
                    const div = document.createElement('div');
                    div.className = 'img-card';
                    div.onclick = function() { handleCardClick(globalIndex, this); };
                    div.innerHTML = `<img src="${imgData.src}" loading="lazy">`;
                    container.appendChild(div);
                });
                loadedCount += nextBatch.length;
            }

            const observer = new IntersectionObserver((entries) => {
                if (entries[0].isIntersecting && loadedCount < filteredImages.length) loadMore();
            }, { rootMargin: '400px' }); // Slightly larger margin for smoother scrolling
            observer.observe(document.getElementById('sentinel'));

            function openLightbox(index) {
                currentIndex = index;
                document.getElementById('lightbox').style.display = 'flex';
                document.body.style.overflow = 'hidden'; 
                updateLightbox();
            }
            function closeLightbox() {
                document.getElementById('lightbox').style.display = 'none';
                document.body.style.overflow = 'auto';
            }
            function updateLightbox() {
                document.getElementById('lightbox-img').src = filteredImages[currentIndex].src;
            }
            
            async function favoriteCurrent() {
                const imgPath = filteredImages[currentIndex].src;
                const response = await fetch('/favorite', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: imgPath })
                });
                if (response.ok) {
                    location.reload();
                }
            }

            document.addEventListener('keydown', (e) => {
                if (document.getElementById('lightbox').style.display === 'flex') {
                    if (e.key === "ArrowRight") { currentIndex = (currentIndex + 1) % filteredImages.length; updateLightbox(); }
                    else if (e.key === "ArrowLeft") { currentIndex = (currentIndex - 1 + filteredImages.length) % filteredImages.length; updateLightbox(); }
                    else if (e.key === "Escape") closeLightbox();
                    else if (e.key.toLowerCase() === "f") favoriteCurrent();
                }
            });

            updateLabel("[All Photos]", allImages.length);
            loadMore();
        </script>
    </body>
    </html>
    """

    # 3. Final Injection
    html_template = html_template.replace("{{FOLDER_LINKS}}", folder_links_html)
    html_template = html_template.replace("{{IMAGES_JSON}}", images_json)
    
    return html_template