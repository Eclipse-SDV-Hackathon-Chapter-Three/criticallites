#!/usr/bin/env python3

"""
Entry point script for running the modular JACCUS client.
This script serves as a convenient way to launch JACCUS from the command line.
"""

import sys
import os

# Add the targets directory to the Python path so we can import jaccus as a module
targets_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, targets_dir)

# Import and run the main JACCUS application
try:
    from jaccus.main import main
    if __name__ == '__main__':
        # Forward all command-line arguments to the main function
        main()
except ImportError as e:
    print(f"Error importing JACCUS modules: {e}")
    print("Make sure you're running this from the targets directory and all modules are present.")
    sys.exit(1)
except Exception as e:
    print(f"Error running JACCUS: {e}")
    sys.exit(1)
