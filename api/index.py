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
    (/api/index -> /) correctly map to Flask's internal routing table.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path_info = environ.get("PATH_INFO", "")
        
        # Strip /api/index or /api prefix introduced by Vercel serverless function routing
        if path_info == "/api/index" or path_info == "/api":
            environ["PATH_INFO"] = "/"
        elif path_info.startswith("/api/index/"):
            environ["PATH_INFO"] = path_info[len("/api/index"):]
        elif path_info.startswith("/api/"):
            # Check if this was a root route rewritten as /api/<route>
            environ["PATH_INFO"] = path_info[len("/api"):]
            
        if not environ.get("PATH_INFO"):
            environ["PATH_INFO"] = "/"

        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathFixMiddleware(app.wsgi_app)

# Export application for Vercel Serverless Function entry
app = app

if __name__ == "__main__":
    app.run()

