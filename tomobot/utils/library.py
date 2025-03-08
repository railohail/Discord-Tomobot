import json
import os
import logging
from pathlib import Path
import shutil

class LibraryManager:
    """Manages music libraries for users."""
    
    def __init__(self, storage_dir="libraries"):
        """Initialize the library manager.
        
        Args:
            storage_dir: Directory to store library files
        """
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
    
    def _get_library_path(self, guild_id):
        """Get the path to a guild's library file."""
        return os.path.join(self.storage_dir, f"library_{guild_id}.json")
    
    def get_libraries(self, guild_id):
        """Get all libraries for a guild.
        
        Returns:
            dict: Libraries and their tracks
        """
        path = self._get_library_path(guild_id)
        if not os.path.exists(path):
            return {}
            
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logging.error(f"Error decoding library file for guild {guild_id}: {e}")
            
            # Try to recover the file - create backup and start with empty library
            backup_path = path + ".bak"
            try:
                if os.path.exists(backup_path):
                    os.remove(backup_path)  # Remove old backup if exists
                shutil.copy2(path, backup_path)  # Create backup of corrupted file
                logging.info(f"Created backup of corrupted library file: {backup_path}")
                
                # Create a new empty library file
                empty_libraries = {}
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(empty_libraries, f, indent=2, ensure_ascii=False)
                logging.info(f"Created new empty library file for guild {guild_id}")
                
                return empty_libraries
            except Exception as backup_error:
                logging.error(f"Failed to create backup or new file: {backup_error}")
                return {}
        except Exception as e:
            logging.error(f"Error loading library for guild {guild_id}: {e}")
            return {}
    
    def save_libraries(self, guild_id, libraries):
        """Save all libraries for a guild.
        
        Args:
            guild_id: ID of the guild
            libraries: Dict of libraries and their tracks
        """
        path = self._get_library_path(guild_id)
        
        # Create a temporary file first
        temp_path = path + ".tmp"
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(libraries, f, indent=2, ensure_ascii=False)
                
            # If successful, rename the temp file to the actual file
            if os.path.exists(path):
                os.replace(temp_path, path)
            else:
                os.rename(temp_path, path)
                
            return True
        except Exception as e:
            logging.error(f"Error saving library for guild {guild_id}: {e}")
            # Clean up temp file if it exists
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            return False
    
    def create_library(self, guild_id, library_name):
        """Create a new library for a guild.
        
        Args:
            guild_id: ID of the guild
            library_name: Name of the library
            
        Returns:
            bool: True if successful, False otherwise
        """
        libraries = self.get_libraries(guild_id)
        
        # Check if library already exists
        if library_name in libraries:
            return False
        
        # Create new library
        libraries[library_name] = []
        
        # Save libraries
        return self.save_libraries(guild_id, libraries)
    
    def delete_library(self, guild_id, library_name):
        """Delete a library.
        
        Args:
            guild_id: ID of the guild
            library_name: Name of the library
            
        Returns:
            bool: True if successful, False otherwise
        """
        libraries = self.get_libraries(guild_id)
        
        # Check if library exists
        if library_name not in libraries:
            return False
        
        # Delete library
        del libraries[library_name]
        
        # Save libraries
        return self.save_libraries(guild_id, libraries)
    
    def add_track(self, guild_id, library_name, track_data):
        """Add a track to a library.
        
        Args:
            guild_id: ID of the guild
            library_name: Name of the library
            track_data: Track data to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        libraries = self.get_libraries(guild_id)
        
        # Check if library exists
        if library_name not in libraries:
            return False
        
        # Check if track already exists in the library (by URI)
        track_uri = track_data.get('uri')
        if track_uri:
            for existing_track in libraries[library_name]:
                if existing_track.get('uri') == track_uri:
                    return False  # Track already exists
        
        # Add track to library
        libraries[library_name].append(track_data)
        
        # Save libraries
        return self.save_libraries(guild_id, libraries)
    
    def remove_track(self, guild_id, library_name, track_index):
        """Remove a track from a library.
        
        Args:
            guild_id: ID of the guild
            library_name: Name of the library
            track_index: Index of the track to remove
            
        Returns:
            bool: True if successful, False otherwise
        """
        libraries = self.get_libraries(guild_id)
        
        # Check if library exists
        if library_name not in libraries:
            return False
        
        # Check if track index is valid
        if track_index < 0 or track_index >= len(libraries[library_name]):
            return False
        
        # Remove track from library
        libraries[library_name].pop(track_index)
        
        # Save libraries
        return self.save_libraries(guild_id, libraries)
    
    def get_library(self, guild_id, library_name):
        """Get tracks from a library.
        
        Args:
            guild_id: ID of the guild
            library_name: Name of the library
            
        Returns:
            list: List of tracks in the library, or None if library doesn't exist
        """
        libraries = self.get_libraries(guild_id)
        
        # Check if library exists
        if library_name not in libraries:
            return None
        
        return libraries[library_name]
    
    def list_libraries(self, guild_id):
        """List all libraries for a guild.
        
        Args:
            guild_id: ID of the guild
            
        Returns:
            dict: Dict of library names and track counts
        """
        libraries = self.get_libraries(guild_id)
        
        return {name: len(tracks) for name, tracks in libraries.items()}
    
    def fix_corrupted_library(self, guild_id):
        """Attempt to fix a corrupted library file by trying various encoding methods.
        
        Args:
            guild_id: ID of the guild
            
        Returns:
            bool: True if successful, False otherwise
        """
        path = self._get_library_path(guild_id)
        if not os.path.exists(path):
            return False
            
        # Try different encoding methods
        encodings = ['utf-8', 'latin1', 'cp1252', 'ascii']
        
        for encoding in encodings:
            try:
                with open(path, 'r', encoding=encoding) as f:
                    libraries = json.load(f)
                
                # If we get here, we successfully decoded the file
                # Save it back with proper utf-8 encoding
                return self.save_libraries(guild_id, libraries)
            except:
                continue
                
        # If all encodings fail, create a new empty file
        logging.warning(f"All encoding recovery attempts failed for guild {guild_id}, creating new empty library")
        empty_libraries = {}
        return self.save_libraries(guild_id, empty_libraries)