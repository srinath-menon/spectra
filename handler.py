import http.server
import json
import scanner
import templates
import os

class SpectraHandler(http.server.SimpleHTTPRequestHandler):
    root_dir = os.getcwd() # Default placeholder

    def __init__(self, *args, **kwargs):
        # This tells Python where to look for the images
        super().__init__(*args, directory=SpectraHandler.root_dir, **kwargs)

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))

        if self.path == '/favorite':
            # ... (keep existing single favorite logic)
            success = scanner.move_to_favorites(data['path'], SpectraHandler.root_dir)
            
        elif self.path == '/favorite_batch':
            try:
                success = scanner.move_batch_to_favorites(data['paths'], SpectraHandler.root_dir)
                if success:
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success"}).encode())
                    return
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
                return

    def do_GET(self):
        if self.path == '/' or self.path == '':
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            
            # Pass the root_dir to the scanner
            images_data = scanner.scan_disk(SpectraHandler.root_dir)
            html_content = templates.get_gallery_html(images_data)
            
            self.wfile.write(html_content.encode('utf-8'))
        else:
            super().do_GET()