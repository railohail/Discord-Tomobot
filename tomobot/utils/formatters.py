def format_duration(duration_ms: int) -> str:
    """
    Format duration from milliseconds to a readable string.
    
    Args:
        duration_ms (int): Duration in milliseconds
        
    Returns:
        str: Formatted duration string (HH:MM:SS or MM:SS)
    """
    seconds = duration_ms // 1000
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"