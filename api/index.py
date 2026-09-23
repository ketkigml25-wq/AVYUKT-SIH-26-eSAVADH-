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
    (/api/index.py, /api/index, /api -> /) correctly map to Flask's internal routing table,
    extracting the true requested URI from Vercel proxy headers.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        # Retrieve the original client requested URI
        raw_path = (
            environ.get("HTTP_X_FORWARDED_URI") or
            environ.get("HTTP_X_MATCHED_PATH") or
            environ.get("RAW_URI") or
            environ.get("REQUEST_URI") or
            environ.get("PATH_INFO") or
            "/"
        )

        # Strip query parameters if present
        if "?" in raw_path:
            raw_path = raw_path.split("?", 1)[0]

        # Strip serverless entrypoint prefixes
        prefixes = [
            "/api/index.py",
            "/api/index",
            "/api/app.py",
            "/api/app"
        ]

        for p in prefixes:
            if raw_path == p:
                raw_path = "/"
                break
            elif raw_path.startswith(p + "/"):
                raw_path = raw_path[len(p):]
                break

        environ["PATH_INFO"] = raw_path if raw_path else "/"
        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathFixMiddleware(app.wsgi_app)

# Export application for Vercel Serverless Function entry
app = app

if __name__ == "__main__":
    app.run()
