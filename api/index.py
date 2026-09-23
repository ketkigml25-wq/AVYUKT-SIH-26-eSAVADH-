import sys
import os

# Add root directory to python module path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app
from werkzeug.middleware.proxy_fix import ProxyFix

# Apply ProxyFix for reverse proxy headers
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

class VercelPathFixMiddleware:
    """
    Middleware ensuring that Vercel's serverless function path rewrites
    (/api/index.py, /api/index, /api -> /) correctly map to Flask's internal routing table.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path_info = environ.get("PATH_INFO", "")
        
        prefixes = [
            "/api/index.py",
            "/api/index",
            "/api/app.py",
            "/api/app",
            "/api"
        ]
        
        for p in prefixes:
            if path_info == p:
                path_info = "/"
                break
            elif path_info.startswith(p + "/"):
                path_info = path_info[len(p):]
                break
                
        environ["PATH_INFO"] = path_info if path_info else "/"
        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathFixMiddleware(app.wsgi_app)

# Export application for Vercel Serverless Function entry
app = app

if __name__ == "__main__":
    app.run()

