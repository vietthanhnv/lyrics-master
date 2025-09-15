#!/usr/bin/env python3
"""
Simple launcher script for the Lyric-to-Subtitle App.
"""

import sys
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

# Import and run the main application
from main import main

if __name__ == "__main__":
    main()