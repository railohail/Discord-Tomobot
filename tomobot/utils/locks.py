from asyncio import Lock

class MusicLock:
    """
    A class to manage locks for music-related operations.
    """
    def __init__(self):
        self.locks = {}
    
    def get_lock(self, guild_id):
        """
        Get a lock for a specific guild.
        
        Args:
            guild_id: The ID of the guild
            
        Returns:
            Lock: An asyncio Lock for the guild
        """
        if guild_id not in self.locks:
            self.locks[guild_id] = Lock()
        return self.locks[guild_id]