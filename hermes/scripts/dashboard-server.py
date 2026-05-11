#!/usr/bin/env python3
"""
Dashboard Server — 启动本地 HTTP 服务展示 evolution dashboard
用法: python3 dashboard-server.py [port]
默认端口: 8765
"""
import os, sys, http.server, socketserver

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
DASHBOARD = os.path.expanduser("~/.hermes/notes/reports/evolution-dashboard-v2.html")

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/dashboard":
            self.path = DASHBOARD
        return super().do_GET()
    
    def log_message(self, format, *args):
        pass  # 静默日志

os.chdir(os.path.dirname(DASHBOARD))

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Dashboard running at http://localhost:{PORT}/")
    print(f"Press Ctrl+C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
