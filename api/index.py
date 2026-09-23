import sys
import os
import urllib.parse

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
    (/api/index.py?__v_path=... -> actual path) correctly map to Flask's internal routing table,
    extracting the true requested route without interfering with actual query parameters.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        query_string = environ.get("QUERY_STRING", "")
        real_path = None

        if "__v_path=" in query_string:
            parsed_qs = urllib.parse.parse_qs(query_string)
            if "__v_path" in parsed_qs:
                real_path = parsed_qs["__v_path"][0]
                # Reconstruct query string without __v_path
                new_qs_params = {k: v for k, v in parsed_qs.items() if k != "__v_path"}
                environ["QUERY_STRING"] = urllib.parse.urlencode(new_qs_params, doseq=True)

        if not real_path:
            raw_path = (
                environ.get("HTTP_X_ORIGINAL_URI") or
                environ.get("HTTP_X_FORWARDED_URI") or
                environ.get("RAW_URI") or
                environ.get("REQUEST_URI") or
                environ.get("PATH_INFO") or
                "/"
            )
            if "?" in raw_path:
                raw_path = raw_path.split("?", 1)[0]
            real_path = raw_path

        # Strip serverless entrypoint prefixes if any remain
        prefixes = [
            "/api/index.py",
            "/api/index",
            "/api/app.py",
            "/api/app"
        ]

        for p in prefixes:
            if real_path == p:
                real_path = "/"
                break
            elif real_path.startswith(p + "/"):
                real_path = real_path[len(p):]
                break

        # Normalize leading slashes
        while real_path.startswith("//"):
            real_path = real_path[1:]
        if not real_path.startswith("/"):
            real_path = "/" + real_path

        environ["PATH_INFO"] = real_path
        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathFixMiddleware(app.wsgi_app)

# Export application for Vercel Serverless Function entry
app = app

if __name__ == "__main__":
    app.run()
