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
        if self.path == '/favorite':
            content_length = int(self.headers['Content-Length'])
            data = json.loads(self.rfile.read(content_length).decode('utf-8'))
            
            try:
                # Tell scanner to move relative to our target root
                success = scanner.move_to_favorites(data['path'], SpectraHandler.root_dir)
                if success:
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
            
            # Pass the root_dir to the scanner
            images_data = scanner.scan_disk(SpectraHandler.root_dir)
            html_content = templates.get_gallery_html(images_data)
            
            self.wfile.write(html_content.encode('utf-8'))
        else:
            super().do_GET()