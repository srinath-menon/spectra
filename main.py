import socketserver
import socket
import sys
import os
from handler import SpectraHandler

DEFAULT_PORT = 8000

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

if __name__ == "__main__":
    # 1. Determine port
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"⚠️  Invalid port. Using {DEFAULT_PORT}")

    # 2. Determine root path
    # If a second arg is provided, use it; otherwise use current directory
    root_path = os.getcwd()
    if len(sys.argv) > 2:
        target = os.path.abspath(sys.argv[2])
        if os.path.isdir(target):
            root_path = target
        else:
            print(f"❌ Error: {target} is not a valid directory.")
            sys.exit(1)

    # Store the root path in the Handler class so it knows where to look
    SpectraHandler.root_dir = root_path
    local_ip = get_ip()
    socketserver.TCPServer.allow_reuse_address = True
    
    try:
        with socketserver.TCPServer(("0.0.0.0", port), SpectraHandler) as httpd:
            print(f"💎 Spectra is live!")
            print(f"📂 Scanning: {root_path}")
            print(f"🚀 LAN:   http://{local_ip}:{port}")
            print("Press Ctrl+C to stop.")
            httpd.serve_forever()
    except OSError as e:
        if e.errno == 48:
            print(f"❌ Port {port} busy. Try: lsof -ti :{port} | xargs kill -9")
        else:
            raise e
    except KeyboardInterrupt:
        print("\nShutting down Spectra...")