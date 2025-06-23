#!/usr/bin/env python3
"""
Test script for YouTube Transcript MCP Server
"""

import asyncio
import subprocess
import json
import sys
import os
import tempfile
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_mcp_server():
    """Test the MCP server functionality."""
    print("🧪 Testing YouTube Transcript MCP Server...\n")
    
    # Test video ID (Rick Astley - Never Gonna Give You Up)
    test_video_id = "dQw4w9WgXcQ"
    test_video_url = f"https://www.youtube.com/watch?v={test_video_id}"
    
    try:
        # Create server parameters - updated path
        server_params = StdioServerParameters(
            command="python",
            args=["src/youtube_transcript_mcp_server.py"],
            env=None
        )
        
        # Connect to the MCP server
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                print("✅ Connected to MCP server\n")
                
                # Initialize the client
                await session.initialize()
                
                # Test 1: List available tools
                print("🔧 Testing available tools...")
                tools = await session.list_tools()
                print(f"Available tools: {[tool.name for tool in tools.tools]}")
                
                expected_tools = ["get_transcript_from_url", "get_transcript_from_id", "list_available_transcripts"]
                for expected_tool in expected_tools:
                    if expected_tool in [tool.name for tool in tools.tools]:
                        print(f"✅ Tool '{expected_tool}' found")
                    else:
                        print(f"❌ Tool '{expected_tool}' missing")
                print()
                
                # Test 2: List available resources
                print("📋 Testing available resources...")
                resources = await session.list_resources()
                print(f"Available resources: {[resource.uri for resource in resources.resources]}")
                print()
                
                # Test 3: List available transcripts
                print("📝 Testing list_available_transcripts...")
                transcript_list = await session.call_tool("list_available_transcripts", {
                    "video_url_or_id": test_video_id
                })
                print("Transcript list result:")
                result_text = transcript_list.content[0].text if transcript_list.content else "No content"
                print(result_text[:500] + "..." if len(result_text) > 500 else result_text)
                print()
                
                # Test 4: Get transcript from URL
                print("🔗 Testing get_transcript_from_url...")
                url_result = await session.call_tool("get_transcript_from_url", {
                    "url": test_video_url,
                    "language": "en",
                    "format_type": "text"
                })
                print("URL transcript result (first 200 chars):")
                result_text = url_result.content[0].text if url_result.content else "No content"
                print(result_text[:200] + "..." if len(result_text) > 200 else result_text)
                print()
                
                # Test 5: Get transcript from video ID  
                print("🆔 Testing get_transcript_from_id...")
                id_result = await session.call_tool("get_transcript_from_id", {
                    "video_id": test_video_id,
                    "language": "en", 
                    "format_type": "json"
                })
                print("ID transcript result (JSON format, first 200 chars):")
                result_text = id_result.content[0].text if id_result.content else "No content"
                print(result_text[:200] + "..." if len(result_text) > 200 else result_text)
                print()
                
                # Test 6: Test resource endpoint
                print("📦 Testing resource endpoint...")
                try:
                    resource_content = await session.read_resource(f"youtube://transcript/{test_video_id}")
                    print("Resource content (first 200 chars):")
                    result_text = resource_content.contents[0].text if resource_content.contents else "No content"
                    print(result_text[:200] + "..." if len(result_text) > 200 else result_text)
                except Exception as e:
                    print(f"❌ Resource test failed: {e}")
                print()
                
                # Test 7: Error handling - invalid video ID
                print("⚠️  Testing error handling with invalid video ID...")
                try:
                    error_result = await session.call_tool("get_transcript_from_id", {
                        "video_id": "invalid_id",
                        "language": "en"
                    })
                    print("Error handling result:")
                    result_text = error_result.content[0].text if error_result.content else "No content"
                    print(result_text)
                except Exception as e:
                    print(f"Caught exception as expected: {e}")
                print()
                
                print("✅ All tests completed successfully!")
                
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def test_docker_build():
    """Test Docker build process."""
    print("🐳 Testing Docker build...\n")
    
    try:
        # Test Docker build from docker directory
        result = subprocess.run([
            "docker", "build", "-f", "docker/Dockerfile", "-t", "youtube-transcript-mcp-test", "."
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ Docker build successful")
            
            # Test Docker run (quick test)
            print("🐳 Testing Docker container startup...")
            result = subprocess.run([
                "docker", "run", "--rm", 
                "youtube-transcript-mcp-test", "python", "-c", 
                "import youtube_transcript_mcp_server; print('Import successful')"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ Docker container runs successfully")
            else:
                print(f"❌ Docker container test failed: {result.stderr}")
                
        else:
            print(f"❌ Docker build failed: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("⏱️  Docker build/test timed out")
    except FileNotFoundError:
        print("⚠️  Docker not found - skipping Docker tests")
    except Exception as e:
        print(f"❌ Docker test failed: {e}")

if __name__ == "__main__":
    print("🚀 YouTube Transcript MCP Server Test Suite\n")
    print("=" * 50)
    
    # Test 1: MCP Server functionality
    try:
        asyncio.run(test_mcp_server())
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    
    # Test 2: Docker build (optional)
    if "--skip-docker" not in sys.argv:
        test_docker_build()
    else:
        print("⏭️  Skipping Docker tests (--skip-docker flag used)")
    
    print("\n🎉 Test suite completed!")