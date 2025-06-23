#!/usr/bin/env python3
"""
Docker build script for YouTube Transcript MCP Server
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

def main():
    """Build Docker image using the organized structure."""
    parser = argparse.ArgumentParser(description="Build YouTube Transcript MCP Docker image")
    parser.add_argument("--tag", "-t", default="youtube-transcript-mcp", 
                       help="Docker image tag (default: youtube-transcript-mcp)")
    parser.add_argument("--no-cache", action="store_true", 
                       help="Build without using cache")
    
    args = parser.parse_args()
    
    # Get the project root directory (parent of scripts directory)
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    print(f"🐳 Building Docker image: {args.tag}")
    print("=" * 50)
    
    # Build Docker command
    cmd = [
        "docker", "build",
        "-f", "docker/Dockerfile",
        "-t", args.tag
    ]
    
    if args.no_cache:
        cmd.append("--no-cache")
    
    cmd.append(".")
    
    try:
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True)
        print(f"✅ Successfully built Docker image: {args.tag}")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Docker build failed with exit code {e.returncode}")
        return e.returncode
    except Exception as e:
        print(f"❌ Error building Docker image: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 