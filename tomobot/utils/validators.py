import re

def is_youtube_url(url):
    """
    Check if a URL is a valid YouTube URL.
    
    Args:
        url (str): The URL to check
        
    Returns:
        bool: True if the URL is a valid YouTube URL, False otherwise
    """
    # YouTube URL patterns
    patterns = [
        r'^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'^https?://(?:www\.)?youtu\.be/[\w-]+',
    ]
    return any(re.match(pattern, url) for pattern in patterns)