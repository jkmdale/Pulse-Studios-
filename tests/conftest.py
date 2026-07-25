import os
import sys

# Ensure backend/ is always on the path when running pytest from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
