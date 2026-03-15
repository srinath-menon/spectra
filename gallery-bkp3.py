import http.server
import socketserver
import os
import urllib.parse
import socket
import json
import shutil 

PORT = 8580
EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
FAV_FOLDER = "_fav_"

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

class GalleryHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/favorite':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            relative_path = urllib.parse.unquote(data['path'])
            source_path = os.path.join(os.getcwd(), relative_path)
            fav_dir = os.path.join(os.getcwd(), FAV_FOLDER)
            if not os.path.exists(fav_dir):
                os.makedirs(fav_dir)
            try:
                filename = os.path.basename(source_path)
                destination = os.path.join(fav_dir, filename)
                shutil.move(source_path, destination)
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())

    def do_GET(self):
        if self.path == '/' or self.path == '':
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(self.generate_gallery_html().encode('utf-8'))
        else:
            super().do_GET()

    def generate_gallery_html(self):
        images_data = []
        folders = set()
        files_list = []
        for root, dirs, files in os.walk('.'):
            if FAV_FOLDER in root: continue 
            for file in files:
                if os.path.splitext(file)[1].lower() in EXTENSIONS:
                    full_path = os.path.join(root, file)
                    files_list.append(full_path)
        
        files_list.sort(key=os.path.getmtime, reverse=True)
        for path in files_list:
            rel_path = os.path.relpath(path, '.')
            folder_path = os.path.dirname(rel_path)
            if folder_path and folder_path != '.':
                folders.add(folder_path)
            images_data.append({
                "src": urllib.parse.quote(rel_path),
                "folder": folder_path.replace("\\", "/") 
            })

        sorted_folders = sorted(list(folders))
        folder_links_html = ""
        for f in sorted_folders:
            folder_links_html += f'<div class="folder-link" onclick="filterByFolder(\'{f}\')">📁 {f}</div>'

        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>LAN Photo Gallery</title>
            <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #000; color: #eee; margin: 0; }}
                header {{ background: #1a1a1a; padding: 15px; position: sticky; top: 0; z-index: 100; border-bottom: 1px solid #333; display: flex; align-items: center; justify-content: space-between; }}
                h1 {{ margin: 0; cursor: pointer; font-size: 1.2rem; }}
                
                #current-folder-label {{ font-size: 0.9rem; color: #888; font-weight: bold; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding: 0 10px; flex-grow: 1; text-align: center; }}
                
                #folder-toggle {{ background: #333; border: 1px solid #444; color: white; padding: 8px 12px; border-radius: 4px; cursor: pointer; }}
                
                /* FIXED DRAWER CSS */
                #folder-drawer {{ 
                    display: none; background: #111; padding: 20px; 
                    border-bottom: 1px solid #333; max-height: 300px; 
                    overflow-y: auto; position: sticky; top: 60px; z-index: 99;
                }}
                
                .folder-link {{ display: block; padding: 10px 0; color: #aaa; cursor: pointer; border-bottom: 1px solid #222; }}
                .gallery {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; padding: 15px; }}
                .img-card {{ width: 150px; height: 150px; overflow: hidden; border-radius: 4px; cursor: pointer; background: #111; }}
                .img-card img {{ width: 100%; height: 100%; object-fit: cover; }}
                #lightbox {{ display: none; position: fixed; z-index: 1000; top: 0; left: 0; width: 100vw; height: 100vh; background: #000; align-items: center; justify-content: center; }}
                #lightbox img {{ width: 100%; height: 100%; object-fit: contain; }}
                .close {{ position: absolute; top: 20px; right: 20px; font-size: 30px; cursor: pointer; z-index: 1010; }}
                #fav-btn {{ position: absolute; bottom: 40px; right: 40px; font-size: 40px; background: rgba(255,255,255,0.2); border-radius: 50%; width: 70px; height: 70px; display: flex; align-items: center; justify-content: center; cursor: pointer; z-index: 1010; }}
                #sentinel {{ height: 100px; width: 100%; }}
            </style>
        </head>
        <body>
            <header>
                <h1 onclick="resetFilter()">🖼️</h1>
                <div id="current-folder-label">[All Photos]</div>
                <button id="folder-toggle" onclick="toggleFolders()">📂 Folders</button>
            </header>
            <div id="folder-drawer">
                <div class="folder-link" onclick="resetFilter()">🏠 [All Photos]</div>
                {folder_links_html}
            </div>
            <div id="gallery-container" class="gallery"></div>
            <div id="sentinel"></div>
            <div id="lightbox">
                <span class="close" onclick="closeLightbox()">&times;</span>
                <div id="fav-btn" onclick="favoriteCurrent()">❤️</div>
                <img id="lightbox-img" src="" onclick="closeLightbox()">
            </div>
            <script>
                const allImages = {json.dumps(images_data)};
                let filteredImages = [...allImages];
                const BATCH_SIZE = 50;
                let loadedCount = 0;
                let currentIndex = 0;
                const container = document.getElementById('gallery-container');
                const folderLabel = document.getElementById('current-folder-label');

                function updateLabel(name, count) {{
                    folderLabel.innerText = name + " [" + count + "]";
                }}

                function toggleFolders() {{
                    const drawer = document.getElementById('folder-drawer');
                    drawer.style.display = drawer.style.display === 'block' ? 'none' : 'block';
                }}

                function filterByFolder(folderPath) {{
                    filteredImages = allImages.filter(img => img.folder === folderPath);
                    updateLabel(folderPath, filteredImages.length);
                    applyFilterUpdate();
                    toggleFolders();
                }}

                function resetFilter() {{
                    filteredImages = [...allImages];
                    updateLabel("[All Photos]", filteredImages.length);
                    applyFilterUpdate();
                    if(document.getElementById('folder-drawer').style.display === 'block') toggleFolders();
                }}

                function applyFilterUpdate() {{
                    container.innerHTML = '';
                    loadedCount = 0;
                    loadMore();
                    window.scrollTo(0, 0);
                }}

                function loadMore() {{
                    const nextBatch = filteredImages.slice(loadedCount, loadedCount + BATCH_SIZE);
                    nextBatch.forEach((imgData, index) => {{
                        const globalIndex = loadedCount + index;
                        const div = document.createElement('div');
                        div.className = 'img-card';
                        div.onclick = () => openLightbox(globalIndex);
                        div.innerHTML = `<img src="${{imgData.src}}" loading="lazy">`;
                        container.appendChild(div);
                    }});
                    loadedCount += nextBatch.length;
                }}

                const observer = new IntersectionObserver((entries) => {{
                    if (entries[0].isIntersecting && loadedCount < filteredImages.length) loadMore();
                }}, {{ rootMargin: '200px' }});
                observer.observe(document.getElementById('sentinel'));

                function openLightbox(index) {{
                    currentIndex = index;
                    document.getElementById('lightbox').style.display = 'flex';
                    document.body.style.overflow = 'hidden'; 
                    updateLightbox();
                }}

                function closeLightbox() {{
                    document.getElementById('lightbox').style.display = 'none';
                    document.body.style.overflow = 'auto';
                }}

                function updateLightbox() {{
                    document.getElementById('lightbox-img').src = filteredImages[currentIndex].src;
                }}

                async function favoriteCurrent() {{
                    const imgPath = filteredImages[currentIndex].src;
                    const response = await fetch('/favorite', {{
                        method: 'POST',
                        body: JSON.stringify({{ path: imgPath }})
                    }});
                    if (response.ok) {{
                        const btn = document.getElementById('fav-btn');
                        btn.style.background = 'rgba(255, 0, 0, 0.6)';
                        setTimeout(() => btn.style.background = 'rgba(255,255,255,0.2)', 500);
                        
                        // Incrementally hide the moved photo from UI
                        filteredImages.splice(currentIndex, 1);
                        updateLabel(folderLabel.innerText.split(' [')[0], filteredImages.length);
                        applyFilterUpdate();
                        closeLightbox();
                    }}
                }}

                document.addEventListener('keydown', (e) => {{
                    if (document.getElementById('lightbox').style.display === 'flex') {{
                        if (e.key === "ArrowRight") {{
                            currentIndex = (currentIndex + 1) % filteredImages.length;
                            updateLightbox();
                        }} else if (e.key === "ArrowLeft") {{
                            currentIndex = (currentIndex - 1 + filteredImages.length) % filteredImages.length;
                            updateLightbox();
                        }} else if (e.key === "Escape") {{
                            closeLightbox();
                        }} else if (e.key.toLowerCase() === "f") {{
                            favoriteCurrent();
                        }}
                    }}
                }});

                updateLabel("[All Photos]", allImages.length);
                loadMore();
            </script>
        </body>
        </html>
        """
        return html_template

if __name__ == "__main__":
    local_ip = get_ip()
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("0.0.0.0", PORT), GalleryHandler) as httpd:
            print(f"🚀 Gallery serving at http://{local_ip}:{PORT}")
            print("Press Ctrl+C to stop.")
            httpd.serve_forever()
    except OSError as e:
        if e.errno == 48:
            print(f"❌ Error: Port {PORT} is already in use.")
            print(f"Try running: lsof -ti :{PORT} | xargs kill -9")
        else:
            raise e
    except KeyboardInterrupt:
        print("\\nShutting down...")