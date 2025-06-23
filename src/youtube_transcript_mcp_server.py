#!/usr/bin/env python3
"""
YouTube Transcript MCP Server
A Model Context Protocol server that extracts transcripts from YouTube videos.
"""

import re
import asyncio
import time
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, parse_qs

from mcp.server.fastmcp import FastMCP
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

# Try to import additional error classes that may not be available in all versions
try:
    from youtube_transcript_api._errors import RequestBlocked
except ImportError:
    RequestBlocked = Exception

try:
    from youtube_transcript_api._errors import YouTubeRequestFailed
except ImportError:
    YouTubeRequestFailed = Exception

import logging
import os
import xml.etree.ElementTree

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("youtube-transcript")

class YouTubeURLError(Exception):
    """Custom exception for YouTube URL parsing errors."""
    pass

def extract_video_id(url: str) -> str:
    """
    Extract YouTube video ID from various URL formats.

    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://www.youtube.com/v/VIDEO_ID

    Args:
        url: YouTube URL string

    Returns:
        str: 11-character video ID

    Raises:
        YouTubeURLError: If URL is invalid or video ID cannot be extracted
    """
    # Regex pattern for YouTube video ID extraction
    patterns = [
        r'(?:v=|v\/|vi=|vi\/|youtu\.be\/|embed\/|\/v\/|\/e\/|watch\?v=|youtube\.com\/user\/[^#]*#[^\/]*\/)*([^#\&\?]*)',
        r'(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})'
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            # YouTube video IDs are exactly 11 characters
            if len(video_id) == 11 and re.match(r'^[a-zA-Z0-9_-]+$', video_id):
                return video_id

    raise YouTubeURLError(f"Could not extract valid video ID from URL: {url}")

def validate_video_id(video_id: str) -> bool:
    """
    Validate YouTube video ID format.

    Args:
        video_id: String to validate

    Returns:
        bool: True if valid format, False otherwise
    """
    return bool(re.match(r'^[a-zA-Z0-9_-]{11}$', video_id))

def format_transcript_text(transcript_data: List[Any]) -> str:
    """
    Format transcript data into readable text.

    Args:
        transcript_data: List of transcript segments (either dicts or FetchedTranscriptSnippet objects)

    Returns:
        str: Formatted transcript text
    """
    formatted_lines = []
    for segment in transcript_data:
        # Handle both dict and FetchedTranscriptSnippet objects
        if hasattr(segment, 'text') and hasattr(segment, 'start'):
            # FetchedTranscriptSnippet object
            text = segment.text.strip() if segment.text else ''
            start_time = segment.start if hasattr(segment, 'start') else 0
        else:
            # Dictionary format
            text = segment.get('text', '').strip()
            start_time = segment.get('start', 0)

        # Convert seconds to MM:SS format
        minutes = int(start_time // 60)
        seconds = int(start_time % 60)
        timestamp = f"{minutes:02d}:{seconds:02d}"

        if text:
            formatted_lines.append(f"[{timestamp}] {text}")

    return "\n".join(formatted_lines)

def format_transcript_json(transcript_data: List[Any]) -> str:
    """
    Format transcript data as JSON string.

    Args:
        transcript_data: List of transcript segments (either dicts or FetchedTranscriptSnippet objects)

    Returns:
        str: JSON formatted transcript
    """
    import json
    
    # Convert FetchedTranscriptSnippet objects to dictionaries if needed
    json_data = []
    for segment in transcript_data:
        if hasattr(segment, 'text') and hasattr(segment, 'start'):
            # FetchedTranscriptSnippet object
            segment_dict = {
                'text': segment.text,
                'start': segment.start,
                'duration': getattr(segment, 'duration', None)
            }
            json_data.append(segment_dict)
        else:
            # Already a dictionary
            json_data.append(segment)
    
    return json.dumps(json_data, indent=2, ensure_ascii=False)

def fetch_transcript_with_retry(video_id: str, language_codes: List[str], max_retries: int = 3) -> tuple[List[Any], str]:
    """
    Fetch transcript with retry logic and better error handling.
    
    Args:
        video_id: YouTube video ID
        language_codes: List of language codes to try in order
        max_retries: Maximum number of retry attempts
        
    Returns:
        tuple: (transcript_data, actual_language_used)
        
    Raises:
        Exception: If all retry attempts fail
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempt {attempt + 1}/{max_retries} to fetch transcript for {video_id}")
            
            # Get transcript list
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Find the best available transcript
            transcript = None
            used_language = None
            
            for lang_code in language_codes:
                try:
                    transcript = transcript_list.find_transcript([lang_code])
                    used_language = lang_code
                    logger.info(f"Found transcript in language: {lang_code}")
                    break
                except NoTranscriptFound:
                    continue
            
            if transcript is None:
                # Get any available transcript as fallback
                available_transcripts = list(transcript_list)
                if available_transcripts:
                    transcript = available_transcripts[0]
                    used_language = transcript.language_code
                    logger.info(f"Using fallback language: {used_language}")
                else:
                    raise NoTranscriptFound(f"No transcripts available for video {video_id}")
            
            # Try to fetch the transcript data
            try:
                transcript_data = transcript.fetch(preserve_formatting=False)
                logger.info(f"Successfully fetched {len(transcript_data)} transcript segments")
                return transcript_data, used_language
            except xml.etree.ElementTree.ParseError as xml_error:
                logger.warning(f"XML parsing error on attempt {attempt + 1}: {xml_error}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    raise Exception(f"Failed to parse transcript XML after {max_retries} attempts. This might be due to YouTube API changes or rate limiting.")
                    
        except (TranscriptsDisabled, VideoUnavailable, NoTranscriptFound) as e:
            # These errors won't be fixed by retrying
            raise e
        except RequestBlocked as e:
            logger.warning(f"Request blocked on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))  # Longer wait for rate limiting
                continue
            else:
                raise e
        except YouTubeRequestFailed as e:
            logger.warning(f"YouTube request failed on attempt {attempt + 1}")
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(1 * (attempt + 1))
                continue
    
    # If we get here, all retries failed
    raise last_error or Exception("All retry attempts failed")

@mcp.tool()
async def get_transcript_from_url(
    url: str, 
    language: str = "en", 
    format_type: str = "text"
) -> str:
    """
    Extract transcript from YouTube video URL.

    Args:
        url: YouTube video URL
        language: Language code for transcript (default: "en")
        format_type: Output format - "text", "json", or "raw" (default: "text")

    Returns:
        str: Transcript content in requested format
    """
    logger.info(f"Getting transcript for URL: {url}, language: {language}, format: {format_type}")
    try:
        # Extract video ID from URL
        video_id = extract_video_id(url)

        # Use robust fetching with retry logic
        language_preference = [language, "en"] if language != "en" else ["en"]
        transcript_data, used_language = fetch_transcript_with_retry(video_id, language_preference)

        # Format based on requested type
        if format_type.lower() == "json":
            return format_transcript_json(transcript_data)
        elif format_type.lower() == "raw":
            return str(transcript_data)
        else:  # default to text
            formatted_text = format_transcript_text(transcript_data)
            return f"Transcript for {url} (Language: {used_language}):\n\n{formatted_text}"

    except YouTubeURLError as e:
        return f"URL Error: {str(e)}"
    except TranscriptsDisabled:
        return f"Error: Transcripts are disabled for this video"
    except VideoUnavailable:
        return f"Error: Video is unavailable or does not exist"
    except RequestBlocked:
        return f"Error: Request blocked. Please try again later"
    except YouTubeRequestFailed:
        return f"Error: YouTube request failed. Please try again later"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

@mcp.tool()
async def get_transcript_from_id(
    video_id: str, 
    language: str = "en", 
    format_type: str = "text"
) -> str:
    """
    Extract transcript from YouTube video ID.

    Args:
        video_id: YouTube video ID (11 characters)
        language: Language code for transcript (default: "en")
        format_type: Output format - "text", "json", or "raw" (default: "text")

    Returns:
        str: Transcript content in requested format
    """
    try:
        # Validate video ID format
        if not validate_video_id(video_id):
            return f"Error: Invalid video ID format. Must be 11 characters: {video_id}"

        # Use robust fetching with retry logic
        language_preference = [language, "en"] if language != "en" else ["en"]
        transcript_data, used_language = fetch_transcript_with_retry(video_id, language_preference)

        # Format based on requested type
        if format_type.lower() == "json":
            return format_transcript_json(transcript_data)
        elif format_type.lower() == "raw":
            return str(transcript_data)
        else:  # default to text
            formatted_text = format_transcript_text(transcript_data)
            return f"Transcript for video {video_id} (Language: {used_language}):\n\n{formatted_text}"

    except TranscriptsDisabled:
        return f"Error: Transcripts are disabled for this video"
    except VideoUnavailable:
        return f"Error: Video is unavailable or does not exist"
    except RequestBlocked:
        return f"Error: Request blocked. Please try again later"
    except YouTubeRequestFailed:
        return f"Error: YouTube request failed. Please try again later"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

@mcp.tool()
async def list_available_transcripts(video_url_or_id: str) -> str:
    """
    List all available transcript languages for a YouTube video.

    Args:
        video_url_or_id: YouTube video URL or video ID

    Returns:
        str: List of available transcript languages and types
    """
    try:
        # Try to extract video ID, if it fails assume it's already an ID
        try:
            video_id = extract_video_id(video_url_or_id)
        except YouTubeURLError:
            video_id = video_url_or_id
            if not validate_video_id(video_id):
                return f"Error: Invalid video ID or URL: {video_url_or_id}"

        # Get transcript list
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        available_transcripts = []
        for transcript in transcript_list:
            transcript_info = {
                'language': transcript.language,
                'language_code': transcript.language_code,
                'is_generated': transcript.is_generated,
                'is_translatable': transcript.is_translatable
            }
            available_transcripts.append(transcript_info)

        if not available_transcripts:
            return f"No transcripts available for video {video_id}"

        # Format output
        result = f"Available transcripts for video {video_id}:\n\n"
        for i, transcript in enumerate(available_transcripts, 1):
            result += f"{i}. {transcript['language']} ({transcript['language_code']})\n"
            result += f"   Generated: {'Yes' if transcript['is_generated'] else 'No'}\n"
            result += f"   Translatable: {'Yes' if transcript['is_translatable'] else 'No'}\n\n"

        return result

    except TranscriptsDisabled:
        return f"Error: Transcripts are disabled for this video"
    except VideoUnavailable:
        return f"Error: Video is unavailable or does not exist"
    except RequestBlocked:
        return f"Error: Request blocked. Please try again later"
    except YouTubeRequestFailed:
        return f"Error: YouTube request failed. Please try again later"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

@mcp.resource("youtube://transcript/{video_id}")
async def get_transcript_resource(video_id: str) -> str:
    """
    Get transcript as a resource.

    Args:
        video_id: YouTube video ID

    Returns:
        str: Transcript content
    """
    logger.info(f"Resource request for video: {video_id}")
    return await get_transcript_from_id(video_id)

# Main execution
if __name__ == "__main__":
    # Get transport from environment variable or default to stdio
    transport = os.getenv('MCP_TRANSPORT', 'stdio')
    
    logger.info(f"Starting YouTube Transcript MCP Server with {transport} transport")
    
    if transport == 'http':
        # Run HTTP transport on all interfaces for Docker
        mcp.run(transport='http', host='0.0.0.0', port=8000)
    else:
        # Default to stdio transport
        mcp.run(transport='stdio')
