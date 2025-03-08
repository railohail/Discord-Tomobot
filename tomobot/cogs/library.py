import asyncio
import logging
import json
import os
from typing import Optional, List, Dict, Union
from collections import deque
import unicodedata
import random
import re

import nextcord
from nextcord.ext import commands
import mafic

import tomobot.config as config
from tomobot.cogs import CogBase

class Library(CogBase):
    """Commands for managing music libraries."""
    
    @nextcord.slash_command(description="Create a new library", dm_permission=False, guild_ids=[config.DISCORD_GUILD])
    async def library_create(self, inter: nextcord.Interaction, library_name: str):
        """Create a new library."""
        guild_id = inter.guild_id
        
        # Create library
        success = self.bot.library_manager.create_library(guild_id, library_name)
        
        if success:
            embed = nextcord.Embed(title="Library Created", color=nextcord.Color.green())
            embed.add_field(name="Library", value=library_name, inline=False)
            embed.add_field(name="Status", value="Library created successfully.", inline=False)
        else:
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Error", value=f"Library '{library_name}' already exists or couldn't be created.", inline=False)
        
        await inter.send(embed=embed)
    
    @nextcord.slash_command(description="List all libraries", dm_permission=False, guild_ids=[config.DISCORD_GUILD])
    async def library_list(self, inter: nextcord.Interaction):
        """List all libraries."""
        guild_id = inter.guild_id
        
        # Get libraries
        libraries = self.bot.library_manager.list_libraries(guild_id)
        
        if libraries:
            embed = nextcord.Embed(title="Libraries", color=nextcord.Color.blue())
            
            # Debug info - print library names as they are stored
            logging.info(f"Libraries for guild {guild_id}: {list(libraries.keys())}")
            
            for library_name, track_count in libraries.items():
                embed.add_field(name=library_name, value=f"{track_count} track(s)", inline=False)
        else:
            embed = nextcord.Embed(title="Libraries", color=nextcord.Color.blue())
            embed.add_field(name="No Libraries", value="You don't have any libraries yet. Create one with /library_create", inline=False)
        
        await inter.send(embed=embed)

    @nextcord.slash_command(description="Add a track or playlist to a library", dm_permission=False, guild_ids=[config.DISCORD_GUILD])
    async def library_add(self, inter: nextcord.Interaction, library_name: str, query: str):
        """Add a track or playlist to a library."""
        guild_id = inter.guild_id
        
        # Check if library exists
        libraries = self.bot.library_manager.get_libraries(guild_id)
        actual_name = self._find_library_name(libraries, library_name)
        
        if actual_name is None:
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Error", value=f"Library '{library_name}' doesn't exist.", inline=False)
            embed.add_field(name="Available Libraries", value=", ".join(libraries.keys()) if libraries else "None", inline=False)
            return await inter.send(embed=embed)
        
        # Use the actual name found in the libraries dict
        library_name = actual_name
        
        # Defer reply since this might take some time
        await inter.response.defer()
        
        try:
            # First try to use an existing player if one exists
            if inter.guild.voice_client and isinstance(inter.guild.voice_client, mafic.Player):
                search_entity = inter.guild.voice_client
            else:
                # If no player exists, find a suitable node
                node = None
                for n in self.bot.pool.nodes:
                    if n.available:
                        node = n
                        break
                
                if not node:
                    embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
                    embed.add_field(name="Error", value="No Lavalink nodes available.", inline=False)
                    return await inter.followup.send(embed=embed)
                
                search_entity = node
            
            # Determine if the query is a URL or a search term
            is_url = query.startswith(("http://", "https://"))
            
            # Fetch tracks based on query type
            if is_url:
                # For URLs, we don't specify a search type in the query but still need to provide it as a parameter
                results = await search_entity.fetch_tracks(query, search_type="")
            else:
                results = await search_entity.fetch_tracks(query, search_type=mafic.SearchType.YOUTUBE)
                
            if not results:
                embed = nextcord.Embed(title="No Results", color=nextcord.Color.yellow())
                embed.add_field(name="Message", value="No tracks found.", inline=False)
                return await inter.followup.send(embed=embed)
            
            # Process the results
            if isinstance(results, mafic.Playlist):
                # Handle playlist
                added_tracks = 0
                skipped_tracks = 0
                
                # Add all tracks from the playlist
                for track in results.tracks:
                    # Create track data
                    track_data = {
                        'title': track.title,
                        'author': track.author,
                        'length': track.length,
                        'uri': track.uri,
                        'identifier': track.identifier
                    }
                    
                    # Add optional fields if they exist
                    if hasattr(track, 'is_stream'):
                        track_data['is_stream'] = track.is_stream
                    
                    if hasattr(track, 'artwork_url') and track.artwork_url:
                        track_data['artwork_url'] = track.artwork_url
                    
                    # Add to library
                    success = self.bot.library_manager.add_track(guild_id, library_name, track_data)
                    
                    if success:
                        added_tracks += 1
                    else:
                        skipped_tracks += 1
                
                # Create response
                embed = nextcord.Embed(title="Playlist Added", color=nextcord.Color.green())
                embed.add_field(name="Playlist Name", value=results.name if hasattr(results, 'name') and results.name else "Playlist", inline=False)
                embed.add_field(name="Library", value=library_name, inline=False)
                embed.add_field(name="Tracks Added", value=str(added_tracks), inline=True)
                
                if skipped_tracks > 0:
                    embed.add_field(name="Tracks Skipped", value=str(skipped_tracks) + " (already exist)", inline=True)
                
            elif is_url or len(results) == 1:
                # Single track from URL or first search result
                track = results[0]
                
                # Create track data
                track_data = {
                    'title': track.title,
                    'author': track.author,
                    'length': track.length,
                    'uri': track.uri,
                    'identifier': track.identifier
                }
                
                # Add optional fields if they exist
                if hasattr(track, 'is_stream'):
                    track_data['is_stream'] = track.is_stream
                
                if hasattr(track, 'artwork_url') and track.artwork_url:
                    track_data['artwork_url'] = track.artwork_url
                
                # Add to library
                success = self.bot.library_manager.add_track(guild_id, library_name, track_data)
                
                if success:
                    embed = nextcord.Embed(title="Track Added", color=nextcord.Color.green())
                    embed.add_field(name="Title", value=track.title, inline=False)
                    embed.add_field(name="Author", value=track.author, inline=False)
                    embed.add_field(name="Library", value=library_name, inline=False)
                else:
                    embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
                    embed.add_field(name="Error", value="Track already exists in the library.", inline=False)
            
            else:
                # Multiple search results - create a selection menu
                options = [
                    nextcord.SelectOption(
                        label=f"{i+1}. {track.title[:50]}", 
                        description=f"By {track.author[:50]}", 
                        value=str(i)
                    ) for i, track in enumerate(results[:10])
                ]
                
                select = nextcord.ui.Select(placeholder="Choose a track...", options=options)
                
                async def select_callback(interaction: nextcord.Interaction):
                    selected_index = int(select.values[0])
                    selected_track = results[selected_index]
                    
                    # Create track data
                    track_data = {
                        'title': selected_track.title,
                        'author': selected_track.author,
                        'length': selected_track.length,
                        'uri': selected_track.uri,
                        'identifier': selected_track.identifier
                    }
                    
                    # Add optional fields if they exist
                    if hasattr(selected_track, 'is_stream'):
                        track_data['is_stream'] = selected_track.is_stream
                    
                    if hasattr(selected_track, 'artwork_url') and selected_track.artwork_url:
                        track_data['artwork_url'] = selected_track.artwork_url
                    
                    # Add to library
                    success = self.bot.library_manager.add_track(guild_id, library_name, track_data)
                    
                    if success:
                        embed = nextcord.Embed(title="Track Added", color=nextcord.Color.green())
                        embed.add_field(name="Title", value=selected_track.title, inline=False)
                        embed.add_field(name="Author", value=selected_track.author, inline=False)
                        embed.add_field(name="Library", value=library_name, inline=False)
                    else:
                        embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
                        embed.add_field(name="Error", value="Track already exists in the library.", inline=False)
                    
                    await interaction.response.send_message(embed=embed)
                
                select.callback = select_callback
                view = nextcord.ui.View(timeout=60)
                view.add_item(select)
                
                embed = nextcord.Embed(title="Track Selection", color=nextcord.Color.blue())
                embed.add_field(name="Action", value=f"Please select a track to add to the library '{library_name}':", inline=False)
                
                await inter.followup.send(embed=embed, view=view)
                return
            
            # Send the response for direct track/playlist adds
            await inter.followup.send(embed=embed)
            
        except Exception as e:
            logging.error(f"Error adding to library: {e}")
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Error", value=f"An error occurred: {str(e)}", inline=False)
            await inter.followup.send(embed=embed)
    @nextcord.slash_command(description="Save the current queue to a library", dm_permission=False, guild_ids=[config.DISCORD_GUILD])
    async def library_save_queue(self, inter: nextcord.Interaction, library_name: str):
        """Save the current queue to a library."""
        guild_id = inter.guild_id
        
        # Check if there's anything in the queue
        if guild_id not in self.bot.music_queues or not self.bot.music_queues[guild_id]:
            # Check if there's at least a current song
            current_song = self.bot.current_song.get(guild_id)
            if not current_song:
                embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
                embed.add_field(name="Error", value="There's nothing in the queue to save.", inline=False)
                return await inter.send(embed=embed)
        
        # Check if library exists
        libraries = self.bot.library_manager.get_libraries(guild_id)
        actual_name = self._find_library_name(libraries, library_name)
        
        if actual_name is None:
            # Create a new library if it doesn't exist
            success = self.bot.library_manager.create_library(guild_id, library_name)
            if not success:
                embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
                embed.add_field(name="Error", value=f"Failed to create library '{library_name}'.", inline=False)
                return await inter.send(embed=embed)
            actual_name = library_name
        
        # Use the actual name found in the libraries dict
        library_name = actual_name
        
        # Defer reply since this might take some time for large queues
        await inter.response.defer()
        
        # Add current song first if there is one
        added_tracks = 0
        skipped_tracks = 0
        
        current_song = self.bot.current_song.get(guild_id)
        if current_song:
            track_data = {
                'title': current_song.title,
                'author': current_song.author,
                'length': current_song.length,
                'uri': current_song.uri,
                'identifier': current_song.identifier
            }
            
            # Add optional fields if they exist
            if hasattr(current_song, 'is_stream'):
                track_data['is_stream'] = current_song.is_stream
            
            if hasattr(current_song, 'artwork_url'):
                track_data['artwork_url'] = current_song.artwork_url
            
            # Add to library
            success = self.bot.library_manager.add_track(guild_id, library_name, track_data)
            if success:
                added_tracks += 1
            else:
                skipped_tracks += 1
        
        # Add all tracks from the queue
        if guild_id in self.bot.music_queues:
            for track in self.bot.music_queues[guild_id]:
                track_data = {
                    'title': track.title,
                    'author': track.author,
                    'length': track.length,
                    'uri': track.uri,
                    'identifier': track.identifier
                }
                
                # Add optional fields if they exist
                if hasattr(track, 'is_stream'):
                    track_data['is_stream'] = track.is_stream
                
                if hasattr(track, 'artwork_url'):
                    track_data['artwork_url'] = track.artwork_url
                
                # Add to library
                success = self.bot.library_manager.add_track(guild_id, library_name, track_data)
                if success:
                    added_tracks += 1
                else:
                    skipped_tracks += 1
        
        # Create response
        embed = nextcord.Embed(title="Queue Saved", color=nextcord.Color.green())
        embed.add_field(name="Library", value=library_name, inline=False)
        embed.add_field(name="Tracks Added", value=str(added_tracks), inline=True)
        
        if skipped_tracks > 0:
            embed.add_field(name="Tracks Skipped", value=str(skipped_tracks) + " (already exist)", inline=True)
        
        await inter.followup.send(embed=embed)

    @nextcord.slash_command(description="View tracks in a library", dm_permission=False, guild_ids=[config.DISCORD_GUILD])
    async def library_view(self, inter: nextcord.Interaction, library_name: str, page: int = 1):
        """View tracks in a library."""
        guild_id = inter.guild_id
        
        # Find the correct library name
        libraries = self.bot.library_manager.get_libraries(guild_id)
        actual_name = self._find_library_name(libraries, library_name)
        
        if actual_name is None:
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Error", value=f"Library '{library_name}' doesn't exist.", inline=False)
            embed.add_field(name="Available Libraries", value=", ".join(libraries.keys()) if libraries else "None", inline=False)
            return await inter.send(embed=embed)
        
        # Use the actual library name found
        library_name = actual_name
        
        # Get library tracks
        tracks = self.bot.library_manager.get_library(guild_id, library_name)
        
        if not tracks:
            embed = nextcord.Embed(title=f"Library: {library_name}", color=nextcord.Color.blue())
            embed.add_field(name="Empty Library", value="This library doesn't have any tracks yet.", inline=False)
            return await inter.send(embed=embed)
        
        # Calculate pages
        tracks_per_page = 10
        total_pages = (len(tracks) + tracks_per_page - 1) // tracks_per_page
        
        # Adjust page number if out of bounds
        if page < 1:
            page = 1
        if page > total_pages:
            page = total_pages
        
        # Get tracks for this page
        start_idx = (page - 1) * tracks_per_page
        end_idx = min(start_idx + tracks_per_page, len(tracks))
        page_tracks = tracks[start_idx:end_idx]
        
        # Create embed
        embed = nextcord.Embed(title=f"Library: {library_name}", color=nextcord.Color.blue())
        embed.set_footer(text=f"Page {page}/{total_pages} · {len(tracks)} track(s) total")
        
        for i, track in enumerate(page_tracks, start=start_idx + 1):
            track_title = track.get('title', 'Unknown')
            track_author = track.get('author', 'Unknown')
            duration = self._format_duration(track.get('length', 0))
            embed.add_field(name=f"{i}. {track_title}", value=f"By: {track_author} ({duration})", inline=False)
        
        await inter.send(embed=embed)

    @nextcord.slash_command(description="Load a library into the queue", dm_permission=False, guild_ids=[config.DISCORD_GUILD])
    async def library_load(self, inter: nextcord.Interaction, library_name: str, shuffle: bool = False):
        """Load a library into the queue."""
        guild_id = inter.guild_id
        
        # Find the correct library name
        libraries = self.bot.library_manager.get_libraries(guild_id)
        actual_name = self._find_library_name(libraries, library_name)
        
        if actual_name is None:
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Error", value=f"Library '{library_name}' doesn't exist.", inline=False)
            embed.add_field(name="Available Libraries", value=", ".join(libraries.keys()) if libraries else "None", inline=False)
            return await inter.send(embed=embed)
        
        # Use the actual library name found
        library_name = actual_name
        
        # Get library tracks
        tracks = self.bot.library_manager.get_library(guild_id, library_name)
        
        if not tracks:
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Error", value="This library doesn't have any tracks.", inline=False)
            return await inter.send(embed=embed)
        
        # Check if user is in a voice channel
        channel = getattr(inter.user.voice, "channel", None)
        if not channel:
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Error", value="You need to be in a voice channel to use this command.", inline=False)
            return await inter.send(embed=embed)
        
        # Defer reply since this might take some time
        await inter.response.defer()
        
        # Initialize bot state for this guild if needed
        self.bot.text_channels[guild_id] = inter.channel
        if guild_id not in self.bot.music_queues:
            self.bot.music_queues[guild_id] = deque()
        
        # Get or create player for playback
        if not inter.guild.voice_client or not isinstance(inter.guild.voice_client, mafic.Player):
            try:
                player = await channel.connect(cls=mafic.Player)
            except Exception as e:
                embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
                embed.add_field(name="Error", value=f"Failed to connect to voice channel: {e}", inline=False)
                return await inter.followup.send(embed=embed)
        else:
            player = inter.guild.voice_client
        
        # Create a copy of tracks that we can shuffle
        tracks_to_add = list(tracks)
        if shuffle:
            random.shuffle(tracks_to_add)
        
        # Add tracks to queue and load them
        added_tracks = 0
        skipped_tracks = 0
        
        # Log total tracks
        logging.info(f"Attempting to load {len(tracks_to_add)} tracks from library '{library_name}'")
        
        for track_data in tracks_to_add:
            try:
                # First attempt: Try using identifier (most reliable)
                identifier = track_data.get('identifier')
                if identifier:
                    try:
                        # Use direct identifier search
                        logging.info(f"Searching with identifier: {identifier}")
                        results = await player.fetch_tracks(f"identifier:{identifier}", search_type="")
                        
                        if results and (isinstance(results, list) and results or 
                                        isinstance(results, mafic.Playlist) and results.tracks):
                            if isinstance(results, list):
                                self.bot.music_queues[guild_id].append(results[0])
                            else:
                                self.bot.music_queues[guild_id].append(results.tracks[0])
                            added_tracks += 1
                            continue  # Skip to next track if successful
                    except Exception as e:
                        logging.info(f"Identifier search failed: {e}")
                        # Continue to next method if this fails
                
                # Second attempt: Try using URI
                uri = track_data.get('uri')
                if uri:
                    try:
                        # Direct URI fetch
                        logging.info(f"Searching with URI: {uri}")
                        results = await player.fetch_tracks(uri, search_type="")
                        
                        if results and (isinstance(results, list) and results or 
                                        isinstance(results, mafic.Playlist) and results.tracks):
                            if isinstance(results, list):
                                self.bot.music_queues[guild_id].append(results[0])
                            else:
                                self.bot.music_queues[guild_id].append(results.tracks[0])
                            added_tracks += 1
                            continue  # Skip to next track if successful
                    except Exception as e:
                        logging.info(f"URI search failed: {e}")
                        # Continue to next method if this fails
                
                # Final attempt: Search by title and author
                title = track_data.get('title', '')
                author = track_data.get('author', '')
                
                if title:
                    try:
                        # If we have both title and author, use a more specific search
                        if author:
                            search_query = f"{title} {author}"
                        else:
                            search_query = title
                        
                        logging.info(f"Searching with query: {search_query}")
                        results = await player.fetch_tracks(search_query, search_type=mafic.SearchType.YOUTUBE)
                        
                        if results and (isinstance(results, list) and results or 
                                    isinstance(results, mafic.Playlist) and results.tracks):
                            if isinstance(results, list):
                                self.bot.music_queues[guild_id].append(results[0])
                            else:
                                self.bot.music_queues[guild_id].append(results.tracks[0])
                            added_tracks += 1
                            continue  # This was our last attempt
                    except Exception as e:
                        logging.info(f"Title/author search failed: {e}")
                        # No more methods to try
                
                # If we reach here, all methods failed
                skipped_tracks += 1
                logging.info(f"All search methods failed for track: {track_data.get('title', 'Unknown')}")
                
            except Exception as e:
                logging.error(f"Error loading track: {e}")
                skipped_tracks += 1
        
        # Start playing if not already playing
        if not player.current and added_tracks > 0:
            try:
                next_track = self.bot.music_queues[guild_id].popleft()
                await player.play(next_track)
                self.bot.current_song[guild_id] = next_track
                logging.info(f"Started playing: {next_track.title}")
            except Exception as e:
                logging.error(f"Error starting playback: {e}")
        
        # Create response embed
        embed = nextcord.Embed(title="Library Loaded", color=nextcord.Color.green())
        embed.add_field(name="Library", value=library_name, inline=False)
        embed.add_field(name="Tracks Added", value=f"{added_tracks} track(s)", inline=True)
        
        if skipped_tracks > 0:
            embed.add_field(name="Tracks Skipped", value=f"{skipped_tracks} track(s)", inline=True)
        
        if shuffle:
            embed.add_field(name="Shuffle", value="Tracks were shuffled", inline=False)
        
        await inter.followup.send(embed=embed)

    @nextcord.slash_command(description="Remove a track from a library", dm_permission=False, guild_ids=[config.DISCORD_GUILD])
    async def library_remove(self, inter: nextcord.Interaction, library_name: str, track_number: int):
        """Remove a track from a library."""
        guild_id = inter.guild_id
        
        # Find the correct library name
        libraries = self.bot.library_manager.get_libraries(guild_id)
        actual_name = self._find_library_name(libraries, library_name)
        
        if actual_name is None:
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Error", value=f"Library '{library_name}' doesn't exist.", inline=False)
            embed.add_field(name="Available Libraries", value=", ".join(libraries.keys()) if libraries else "None", inline=False)
            return await inter.send(embed=embed)
        
        # Use the actual library name found
        library_name = actual_name
        
        # Get library tracks
        tracks = self.bot.library_manager.get_library(guild_id, library_name)
        
        # Track number is 1-based for users, but 0-based for the list
        track_index = track_number - 1
        
        if track_index < 0 or track_index >= len(tracks):
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Error", value=f"Invalid track number. Please use a number between 1 and {len(tracks)}.", inline=False)
            return await inter.send(embed=embed)
        
        # Get track info before removing
        track_title = tracks[track_index].get('title', 'Unknown')
        track_author = tracks[track_index].get('author', 'Unknown')
        
        # Remove track
        success = self.bot.library_manager.remove_track(guild_id, library_name, track_index)
        
        if success:
            embed = nextcord.Embed(title="Track Removed", color=nextcord.Color.green())
            embed.add_field(name="Library", value=library_name, inline=False)
            embed.add_field(name="Track", value=f"{track_title} - {track_author}", inline=False)
        else:
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Error", value="Failed to remove track.", inline=False)
        
        await inter.send(embed=embed)

    @nextcord.slash_command(description="Delete a library", dm_permission=False, guild_ids=[config.DISCORD_GUILD])
    async def library_delete(self, inter: nextcord.Interaction, library_name: str):
        """Delete a library."""
        guild_id = inter.guild_id
        
        # Find the correct library name
        libraries = self.bot.library_manager.get_libraries(guild_id)
        actual_name = self._find_library_name(libraries, library_name)
        
        if actual_name is None:
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Error", value=f"Library '{library_name}' doesn't exist.", inline=False)
            embed.add_field(name="Available Libraries", value=", ".join(libraries.keys()) if libraries else "None", inline=False)
            return await inter.send(embed=embed)
        
        # Use the actual library name found
        library_name = actual_name
        
        # Delete library
        success = self.bot.library_manager.delete_library(guild_id, library_name)
        
        if success:
            embed = nextcord.Embed(title="Library Deleted", color=nextcord.Color.green())
            embed.add_field(name="Library", value=library_name, inline=False)
            embed.add_field(name="Status", value="Library deleted successfully.", inline=False)
        else:
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Error", value=f"Library '{library_name}' couldn't be deleted.", inline=False)
        
        await inter.send(embed=embed)

    @nextcord.slash_command(description="Select a track to remove from a library", dm_permission=False, guild_ids=[config.DISCORD_GUILD])
    async def library_remove_select(self, inter: nextcord.Interaction, library_name: str):
        """Select a track to remove from a library."""
        guild_id = inter.guild_id
        
        # Find the correct library name
        libraries = self.bot.library_manager.get_libraries(guild_id)
        actual_name = self._find_library_name(libraries, library_name)
        
        if actual_name is None:
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Error", value=f"Library '{library_name}' doesn't exist.", inline=False)
            embed.add_field(name="Available Libraries", value=", ".join(libraries.keys()) if libraries else "None", inline=False)
            return await inter.send(embed=embed)
        
        # Use the actual library name found
        library_name = actual_name
        
        # Get library tracks
        tracks = self.bot.library_manager.get_library(guild_id, library_name)
        
        if not tracks:
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Error", value="This library doesn't have any tracks.", inline=False)
            return await inter.send(embed=embed)
        
        # Create select options for tracks
        options = []
        for i, track in enumerate(tracks):
            title = track.get('title', 'Unknown')[:50]  # Limit title length
            author = track.get('author', 'Unknown')[:50]  # Limit author length
            options.append(nextcord.SelectOption(
                label=f"{i+1}. {title}",
                description=f"By: {author}",
                value=str(i)
            ))
        
        # Create selection menu
        select = nextcord.ui.Select(
            placeholder="Select a track to remove...",
            options=options[:25]  # Discord has a 25 option limit
        )
        
        async def select_callback(interaction: nextcord.Interaction):
            track_index = int(select.values[0])
            
            # Get track info before removing
            track_title = tracks[track_index].get('title', 'Unknown')
            track_author = tracks[track_index].get('author', 'Unknown')
            
            # Remove track
            success = self.bot.library_manager.remove_track(guild_id, library_name, track_index)
            
            if success:
                embed = nextcord.Embed(title="Track Removed", color=nextcord.Color.green())
                embed.add_field(name="Library", value=library_name, inline=False)
                embed.add_field(name="Track", value=f"{track_title} - {track_author}", inline=False)
            else:
                embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
                embed.add_field(name="Error", value="Failed to remove track.", inline=False)
            
            await interaction.response.send_message(embed=embed)
        
        select.callback = select_callback
        view = nextcord.ui.View(timeout=60)
        view.add_item(select)
        
        # If there are more than 25 tracks, let the user know
        if len(tracks) > 25:
            content = f"Showing first 25 tracks out of {len(tracks)}. Use /library_remove with the track number to remove tracks beyond the first 25."
        else:
            content = f"Select a track to remove from library '{library_name}':"
        
        await inter.send(content=content, view=view)

    # Helper methods
    def _find_library_name(self, libraries, library_name):
        """Find the correct library name, handling Unicode normalization."""
        # Try direct match
        if library_name in libraries:
            return library_name
        
        # Try normalized comparison
        norm_input = unicodedata.normalize('NFC', library_name)
        for lib_key in libraries.keys():
            norm_key = unicodedata.normalize('NFC', lib_key)
            if norm_input == norm_key:
                return lib_key
        
        return None
    
    def _format_duration(self, duration_ms: int) -> str:
        """Format duration in milliseconds to a human-readable string."""
        seconds = duration_ms // 1000
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"


def setup(bot):
    """Set up the Library cog."""
    bot.add_cog(Library(bot))