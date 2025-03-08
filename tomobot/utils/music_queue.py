from collections import deque

class MusicQueue:
    """
    A class to manage music queues for different guilds.
    """
    def __init__(self):
        self.queues = {}
        
    def get_queue(self, guild_id):
        """
        Get the queue for a specific guild.
        
        Args:
            guild_id: The ID of the guild
            
        Returns:
            deque: The queue for the guild
        """
        if guild_id not in self.queues:
            self.queues[guild_id] = deque()
        return self.queues[guild_id]
    
    def add_track(self, guild_id, track):
        """
        Add a track to the end of a guild's queue.
        
        Args:
            guild_id: The ID of the guild
            track: The track to add
        """
        self.get_queue(guild_id).append(track)
    
    def add_track_front(self, guild_id, track):
        """
        Add a track to the front of a guild's queue.
        
        Args:
            guild_id: The ID of the guild
            track: The track to add
        """
        self.get_queue(guild_id).appendleft(track)
        
    def get_next_track(self, guild_id):
        """
        Get the next track from a guild's queue.
        
        Args:
            guild_id: The ID of the guild
            
        Returns:
            The next track, or None if the queue is empty
        """
        queue = self.get_queue(guild_id)
        if queue:
            return queue.popleft()
        return None
    
    def clear_queue(self, guild_id):
        """
        Clear a guild's queue.
        
        Args:
            guild_id: The ID of the guild
        """
        if guild_id in self.queues:
            self.queues[guild_id].clear()
    
    def remove_track(self, guild_id, index):
        """
        Remove a track from a guild's queue.
        
        Args:
            guild_id: The ID of the guild
            index: The index of the track to remove
            
        Returns:
            The removed track, or None if the index is out of range
        """
        queue = self.get_queue(guild_id)
        if 0 <= index < len(queue):
            track = queue[index]
            del queue[index]
            return track
        return None
    
    def get_queue_length(self, guild_id):
        """
        Get the length of a guild's queue.
        
        Args:
            guild_id: The ID of the guild
            
        Returns:
            int: The length of the queue
        """
        return len(self.get_queue(guild_id))
    
    def shuffle(self, guild_id):
        """
        Shuffle a guild's queue.
        
        Args:
            guild_id: The ID of the guild
        """
        import random
        queue = self.get_queue(guild_id)
        queue_list = list(queue)
        random.shuffle(queue_list)
        self.queues[guild_id] = deque(queue_list)