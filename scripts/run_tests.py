#!/usr/bin/env python3
"""
Test runner script for YouTube Transcript MCP Server
"""

import sys
import os
import subprocess
from pathlib import Path

def main():
    """Run all tests from the project root directory."""
    # Get the project root directory (parent of scripts directory)
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    print("🧪 YouTube Transcript MCP Server Test Suite")
    print("=" * 50)
    
    # Run the test server
    try:
        result = subprocess.run([
            sys.executable, "tests/test_server.py"
        ], check=True)
        print("✅ All tests passed!")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Tests failed with exit code {e.returncode}")
        return e.returncode
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 