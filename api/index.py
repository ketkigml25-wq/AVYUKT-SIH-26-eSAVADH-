import sys
import os

# Add root directory to python module path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app

# Export application for Vercel Serverless Function entry
app = app

if __name__ == "__main__":
    app.run()
