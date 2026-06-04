import http.server
import socketserver
import webbrowser
import os
import threading
import time
import sys

# Default Port
START_PORT = 8000
MAX_PORT_ATTEMPTS = 10
FILENAME = "text2image.html"
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler to serve files from the script's directory."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

def start_server(port):
    """Starts the HTTP server on the specified port."""
    handler = QuietHandler
    # Bind to localhost (127.0.0.1) for security and local access
    for attempt in range(MAX_PORT_ATTEMPTS):
        current_port = port + attempt
        try:
            with socketserver.TCPServer(("127.0.0.1", current_port), handler) as httpd:
                print("=" * 60)
                print(f"本地 Web 伺服器已啟動！")
                print(f"網頁網址: http://localhost:{current_port}/{FILENAME}")
                print("按 Ctrl+C 可以關閉伺服器。")
                print("=" * 60)
                
                # Automatically open browser after a short delay
                threading.Thread(
                    target=lambda: (time.sleep(0.8), webbrowser.open(f"http://localhost:{current_port}/{FILENAME}")),
                    daemon=True
                ).start()
                
                httpd.serve_forever()
        except OSError as e:
            if e.errno == 98 or e.errno == 10048: # Port already in use
                print(f"埠號 {current_port} 已被佔用，嘗試下一個埠號...")
                continue
            else:
                print(f"啟動伺服器時發生錯誤: {e}")
                sys.exit(1)
    else:
        print(f"錯誤: 無法在埠號 {port} 到 {port + MAX_PORT_ATTEMPTS - 1} 之間找到可用埠號。")
        sys.exit(1)

if __name__ == "__main__":
    # Ensure the target HTML file exists
    target_path = os.path.join(DIRECTORY, FILENAME)
    if not os.path.exists(target_path):
        print(f"錯誤: 找不到網頁檔案 '{FILENAME}'，請確保它位於相同的資料夾內。")
        sys.exit(1)
        
    try:
        start_server(START_PORT)
    except KeyboardInterrupt:
        print("\n伺服器已關閉。")
        sys.exit(0)
