import random


import nextcord
from nextcord.ext import commands
import mafic
from collections import deque


import tomobot.config as config 
from tomobot.utils import is_youtube_url, format_duration
from tomobot.cogs import CogBase
from tomobot.bot import play_next

class Music(CogBase):
    """Music commands for the bot."""

    @commands.Cog.listener()
    async def on_track_start(self, event: mafic.TrackStartEvent):
        """Forward track start events to the bot's event handler."""
        from bot.events import on_track_start
        await on_track_start(self.bot, event)

    @commands.Cog.listener()
    async def on_track_end(self, event: mafic.TrackEndEvent):
        """Forward track end events to the bot's event handler."""
        from bot.events import on_track_end
        await on_track_end(self.bot, event)

    async def create_timeout_handler(self, inter: nextcord.Interaction, player: mafic.Player):
        """Create a timeout handler for a view."""
        async def on_timeout():
            # Check if the player is still in use
            if not player.current and player.connected:
                guild_id = inter.guild_id
                if guild_id in self.bot.music_queues and not self.bot.music_queues[guild_id]:
                    await player.disconnect()
                    if guild_id in self.bot.text_channels:
                        await self.bot.text_channels[guild_id].send("Search timed out. Disconnected from the voice channel.")
        
        return on_timeout

    @nextcord.slash_command(description="Play music or search for tracks", dm_permission=False, guild_ids=[config.DISCORD_GUILD])
    async def play(self, inter: nextcord.Interaction, query: str):
        """Play music from a query or URL."""
        if not inter.user.voice:
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Message", value="You need to be in a voice channel!", inline=False)
            return await inter.send(embed=embed)
        
        if inter.guild.voice_client and inter.guild.voice_client.channel != inter.user.voice.channel:
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Message", value="I'm already in a different voice channel. Please join my channel or use the stop command first.", inline=False)
            return await inter.send(embed=embed)
        
        self.bot.text_channels[inter.guild_id] = inter.channel

        if not inter.guild.voice_client:
            try:
                player = await inter.user.voice.channel.connect(cls=mafic.Player)
            except Exception as e:
                embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
                embed.add_field(name="Message", value=f"Failed to connect to voice channel: {str(e)}", inline=False)
                return await inter.send(embed=embed)
        else:
            player = inter.guild.voice_client

        if inter.guild_id not in self.bot.music_queues:
            self.bot.music_queues[inter.guild_id] = deque()

        try:
            if is_youtube_url(query):
                results = await player.fetch_tracks(query)
            else:
                results = await player.fetch_tracks(query, search_type=mafic.SearchType.YOUTUBE)
        except Exception as e:
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Message", value=f"An error occurred while fetching tracks: {str(e)}", inline=False)
            return await inter.send(embed=embed)

        if not results:
            embed = nextcord.Embed(title="No Results", color=nextcord.Color.yellow())
            embed.add_field(name="Message", value="No tracks found.", inline=False)
            return await inter.send(embed=embed)

        if isinstance(results, mafic.Playlist):
            for track in results.tracks:
                self.bot.music_queues[inter.guild_id].append(track)
            embed = nextcord.Embed(title="Playlist Added", color=nextcord.Color.green())
            embed.add_field(name="Playlist Name", value=results.name, inline=False)
            embed.add_field(name="Tracks Added", value=str(len(results.tracks)), inline=False)
            await inter.send(embed=embed)
            if inter.guild_id not in self.bot.current_song:
                await play_next(self.bot, player)
        elif is_youtube_url(query) or len(results) == 1:
            track = results[0]
            self.bot.music_queues[inter.guild_id].append(track)
            embed = nextcord.Embed(title="Track Added", color=nextcord.Color.green())
            embed.add_field(name="Title", value=track.title, inline=False)
            embed.add_field(name="Author", value=track.author, inline=False)
            await inter.send(embed=embed)
            if inter.guild_id not in self.bot.current_song:
                await play_next(self.bot, player)
        else:
            options = [nextcord.SelectOption(label=f"{i+1}. {track.title[:50]}", description=f"By {track.author[:50]}", value=str(i)) for i, track in enumerate(results[:10])]
            select = nextcord.ui.Select(placeholder="Choose a track...", options=options)

            async def select_callback(interaction: nextcord.Interaction):
                selected_index = int(select.values[0])
                selected_track = results[selected_index]
                self.bot.music_queues[interaction.guild_id].append(selected_track)
                embed = nextcord.Embed(title="Track Added", color=nextcord.Color.green())
                embed.add_field(name="Title", value=selected_track.title, inline=False)
                embed.add_field(name="Author", value=selected_track.author, inline=False)
                await interaction.response.send_message(embed=embed)
                if interaction.guild_id not in self.bot.current_song:
                    await play_next(self.bot, player)

            select.callback = select_callback
            view = nextcord.ui.View(timeout=60)
            view.add_item(select)
            view.on_timeout = await self.create_timeout_handler(inter, player)

            embed = nextcord.Embed(title="Track Selection", color=nextcord.Color.blue())
            embed.add_field(name="Action", value="Please select a track to add to the queue:", inline=False)
            await inter.send(embed=embed, view=view)

    @nextcord.slash_command(description="Play music or search for tracks (add to front of queue)", dm_permission=False, guild_ids=[config.DISCORD_GUILD])
    async def playnext(self, inter: nextcord.Interaction, query: str):
        """Play music from a query or URL at the front of the queue."""
        if not inter.user.voice:
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Message", value="You need to be in a voice channel!", inline=False)
            return await inter.send(embed=embed)
        
        if inter.guild.voice_client and inter.guild.voice_client.channel != inter.user.voice.channel:
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Message", value="I'm already in a different voice channel. Please join my channel or use the stop command first.", inline=False)
            return await inter.send(embed=embed)
        
        self.bot.text_channels[inter.guild_id] = inter.channel

        if not inter.guild.voice_client:
            try:
                player = await inter.user.voice.channel.connect(cls=mafic.Player)
            except Exception as e:
                embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
                embed.add_field(name="Message", value=f"Failed to connect to voice channel: {str(e)}", inline=False)
                return await inter.send(embed=embed)
        else:
            player = inter.guild.voice_client

        if inter.guild_id not in self.bot.music_queues:
            self.bot.music_queues[inter.guild_id] = deque()

        try:
            if is_youtube_url(query):
                results = await player.fetch_tracks(query)
            else:
                results = await player.fetch_tracks(query, search_type=mafic.SearchType.YOUTUBE)
        except Exception as e:
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Message", value=f"An error occurred while fetching tracks: {str(e)}", inline=False)
            return await inter.send(embed=embed)

        if not results:
            embed = nextcord.Embed(title="No Results", color=nextcord.Color.yellow())
            embed.add_field(name="Message", value="No tracks found.", inline=False)
            return await inter.send(embed=embed)

        if isinstance(results, mafic.Playlist):
            for track in reversed(results.tracks):
                self.bot.music_queues[inter.guild_id].appendleft(track)
            embed = nextcord.Embed(title="Playlist Added", color=nextcord.Color.green())
            embed.add_field(name="Playlist Name", value=results.name, inline=False)
            embed.add_field(name="Tracks Added", value=str(len(results.tracks)), inline=False)
            embed.add_field(name="Position", value="Next in queue", inline=False)
            await inter.send(embed=embed)
            if inter.guild_id not in self.bot.current_song:
                await play_next(self.bot, player)
        elif is_youtube_url(query) or len(results) == 1:
            track = results[0]
            self.bot.music_queues[inter.guild_id].appendleft(track)
            embed = nextcord.Embed(title="Track Added", color=nextcord.Color.green())
            embed.add_field(name="Title", value=track.title, inline=False)
            embed.add_field(name="Author", value=track.author, inline=False)
            embed.add_field(name="Position", value="Next in queue", inline=False)
            await inter.send(embed=embed)
            if inter.guild_id not in self.bot.current_song:
                await play_next(self.bot, player)
        else:
            options = [nextcord.SelectOption(label=f"{i+1}. {track.title[:50]}", description=f"By {track.author[:50]}", value=str(i)) for i, track in enumerate(results[:10])]
            select = nextcord.ui.Select(placeholder="Choose a track...", options=options)

            async def select_callback(interaction: nextcord.Interaction):
                selected_index = int(select.values[0])
                selected_track = results[selected_index]
                self.bot.music_queues[interaction.guild_id].appendleft(selected_track)
                embed = nextcord.Embed(title="Track Added", color=nextcord.Color.green())
                embed.add_field(name="Title", value=selected_track.title, inline=False)
                embed.add_field(name="Author", value=selected_track.author, inline=False)
                embed.add_field(name="Position", value="Next in queue", inline=False)
                await interaction.response.send_message(embed=embed)
                if interaction.guild_id not in self.bot.current_song:
                    await play_next(self.bot, player)

            select.callback = select_callback
            view = nextcord.ui.View(timeout=60)
            view.add_item(select)
            view.on_timeout = await self.create_timeout_handler(inter, player)

            embed = nextcord.Embed(title="Track Selection", color=nextcord.Color.blue())
            embed.add_field(name="Action", value="Please select a track to play next:", inline=False)
            await inter.send(embed=embed, view=view)

    @nextcord.slash_command(description="Stop the music and clear the queue", dm_permission=False, guild_ids=[config.DISCORD_GUILD])
    async def stop(self, inter: nextcord.Interaction):
        """Stop the music, clear the queue, and disconnect."""
        if not inter.guild.voice_client or not isinstance(inter.guild.voice_client, mafic.Player):
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Message", value="I'm not playing anything right now.", inline=False)
            return await inter.send(embed=embed)

        player = inter.guild.voice_client
        guild_id = inter.guild_id
        
        if player.connected:
            # Disable replay mode
            self.bot.replay_mode[guild_id] = False
            
            if guild_id in self.bot.music_queues:
                self.bot.music_queues[guild_id].clear()
            await player.stop()
            await player.disconnect()
            
            embed = nextcord.Embed(title="Playback Stopped", color=nextcord.Color.blue())
            embed.add_field(name="Action", value="Stopped the music, cleared the queue, and disconnected from the voice channel.", inline=False)
            embed.add_field(name="Replay Mode", value="Disabled", inline=False)
            
            await inter.send(embed=embed)
        else:
            embed = nextcord.Embed(title="Error", color=nextcord.Color.red())
            embed.add_field(name="Message", value="The player is not connected to a voice channel.", inline=False)
            await inter.send(embed=embed)

    @nextcord.slash_command(description="Pause the current track", dm_permission=False, guild_ids=[config.DISCORD_GUILD])
    async def pause(self, inter: nextcord.Interaction):
        """Pause the current track."""
        if not inter.guild.voice_client or not isinstance(inter.guild.voice_client, mafic.Player):
            return await inter.send("I'm not playing anything right now.")

        player = inter.guild.voice_client
        if player.connected and player.current:
            if player.paused:
                return await inter.send("The player is already paused.")
            await player.pause()
            await inter.send("Paused the current track.")
        else:
            await inter.send("Unable to pause. No track is currently playing.")

    @nextcord.slash_command(description="Resume the paused track", dm_permission=False, guild_ids=[config.DISCORD_GUILD])
    async def resume(self, inter: nextcord.Interaction):
        """Resume the paused track."""
        if not inter.guild.voice_client or not isinstance(inter.guild.voice_client, mafic.Player):
            return await inter.send("I'm not playing anything right now.")

        player = inter.guild.voice_client
        if player.connected and player.current:
            if not player.paused:
                return await inter.send("The player is not paused.")
            await player.resume()
            await inter.send("Resumed the current track.")
        else:
            await inter.send("Unable to resume. No track is currently playing.")

    @nextcord.slash_command(description="Skip the current track", dm_permission=False, guild_ids=[config.DISCORD_GUILD])
    async def skip(self, inter: nextcord.Interaction):
        """Skip the current track."""
        if not inter.guild.voice_client or not isinstance(inter.guild.voice_client, mafic.Player):
            return await inter.send("I'm not playing anything right now.")

        player = inter.guild.voice_client
        if player.current:
            guild_id = inter.guild_id
            
            # Temporarily add a flag to the bot to indicate this is a skip operation
            if not hasattr(self.bot, 'skip_operations'):
                self.bot.skip_operations = {}
            
            # Set this guild's skip flag to True
            self.bot.skip_operations[guild_id] = True
            
            # Stop the current track
            await player.stop()
            
            # Send confirmation
            await inter.send("Skipped the current track.")
        else:
            await inter.send("No track is currently playing.")

    @nextcord.slash_command(description="Delete a specific track from the queue", dm_permission=False, guild_ids=[config.DISCORD_GUILD])
    async def delete_from_queue(self, inter: nextcord.Interaction):
        """Delete a specific track from the queue."""
        if inter.guild_id not in self.bot.music_queues or not self.bot.music_queues[inter.guild_id]:
            return await inter.send("The queue is empty.")

        queue = self.bot.music_queues[inter.guild_id]
        options = [
            nextcord.SelectOption(
                label=f"{i+1}. {track.title[:50]}",
                description=f"By {track.author[:50]}",
                value=str(i)
            ) for i, track in enumerate(queue)
        ]

        if len(options) > 25:  # Discord has a limit of 25 options in a select menu
            options = options[:25]
            await inter.send("Only showing the first 25 tracks due to Discord limitations.")

        select = nextcord.ui.Select(
            placeholder="Choose a track to delete...",
            options=options
        )

        async def select_callback(interaction: nextcord.Interaction):
            selected_index = int(select.values[0])
            deleted_track = queue[selected_index]
            del queue[selected_index]
            await interaction.response.send_message(f"Removed '{deleted_track.title}' from the queue.")

        select.callback = select_callback
        view = nextcord.ui.View(timeout=60)
        view.add_item(select)

        await inter.send("Select a track to remove from the queue:", view=view)

        async def on_timeout():
            await inter.edit_original_message(content="The selection timed out.", view=None)

        view.on_timeout = on_timeout

    @nextcord.slash_command(description="Show information about the currently playing track", dm_permission=False, guild_ids=[config.DISCORD_GUILD])
    async def now_playing(self, inter: nextcord.Interaction):
        """Show information about the currently playing track."""
        if not inter.guild.voice_client or not isinstance(inter.guild.voice_client, mafic.Player):
            return await inter.send("I'm not playing anything right now.")

        player = inter.guild.voice_client
        if not player.current:
            return await inter.send("No track is currently playing.")

        track = player.current
        duration = format_duration(track.length)
        position = format_duration(player.position)
        guild_id = inter.guild_id
        
        # Check replay mode
        replay_mode = self.bot.replay_mode.get(guild_id, False)

        embed = nextcord.Embed(title="Now Playing", color=nextcord.Color.blue())
        embed.add_field(name="Title", value=track.title, inline=False)
        embed.add_field(name="Author", value=track.author, inline=False)
        embed.add_field(name="Duration", value=f"{position} / {duration}", inline=False)
        
        if replay_mode:
            embed.add_field(name="Replay Mode", value="Enabled ♻️", inline=False)
        
        if track.uri:
            embed.add_field(name="Link", value=f"[Click here]({track.uri})", inline=False)

        await inter.send(embed=embed)

    @nextcord.slash_command(description="Set the volume of the player", dm_permission=False, guild_ids=[config.DISCORD_GUILD])
    async def volume(self, inter: nextcord.Interaction, volume: int):
        """Set the volume of the player."""
        if not inter.guild.voice_client or not isinstance(inter.guild.voice_client, mafic.Player):
            return await inter.send("I'm not playing anything right now.")

        player = inter.guild.voice_client
        if 0 <= volume <= 1000:
            await player.set_volume(volume)
            await inter.send(f"Set the volume to {volume}%")
        else:
            await inter.send("Volume must be between 0 and 1000")

    @nextcord.slash_command(description="Shuffle the current queue", dm_permission=False, guild_ids=[config.DISCORD_GUILD])
    async def shuffle(self, inter: nextcord.Interaction):
        """Shuffle the current queue."""
        if inter.guild_id not in self.bot.music_queues or len(self.bot.music_queues[inter.guild_id]) < 2:
            return await inter.send("The queue needs at least two tracks to shuffle.")

        queue = self.bot.music_queues[inter.guild_id]
        
        # Convert the deque to a list, shuffle it, and convert back to deque
        queue_list = list(queue)
        random.shuffle(queue_list)
        self.bot.music_queues[inter.guild_id] = deque(queue_list)

        # Create an embed to display the shuffled queue
        embed = nextcord.Embed(title="Queue Shuffled", color=nextcord.Color.green())
        
        # Display the current track (if any) and the first 10 tracks of the shuffled queue
        track_list = []
        current_track = self.bot.current_song.get(inter.guild_id)
        if current_track:
            track_list.append(f"Currently playing: {current_track.title} - {current_track.author}")
        
        for i, track in enumerate(queue_list):
            if i < 10:  # Show up to 10 tracks from the queue
                duration = format_duration(track.length)
                track_list.append(f"{i+1}. {track.title} - {track.author} ({duration})")
            else:
                break

        if track_list:
            embed.add_field(name="Current Track and Queue", value="\n".join(track_list), inline=False)
            if len(queue_list) > 10:
                embed.add_field(name="", value=f"And {len(queue_list) - 10} more...", inline=False)

        total_tracks = len(queue_list) + (1 if current_track else 0)
        embed.add_field(name="Queue Info", value=f"Total tracks: {total_tracks}\n"
                                                f"Tracks shuffled: {len(queue_list)}", inline=False)

        await inter.send(embed=embed)

    @nextcord.slash_command(description="Show the current queue", dm_permission=False, guild_ids=[config.DISCORD_GUILD])
    async def queue(self, inter: nextcord.Interaction):
        """Show the current queue."""
        if inter.guild_id not in self.bot.music_queues and inter.guild_id not in self.bot.current_song:
            return await inter.send("The queue is empty and no song is currently playing.")

        embed = nextcord.Embed(title="Current Queue", color=nextcord.Color.blue())

        # Add current track information
        current_track = self.bot.current_song.get(inter.guild_id)
        if current_track:
            player = inter.guild.voice_client
            if player and isinstance(player, mafic.Player):
                current_position = format_duration(player.position)
                current_duration = format_duration(current_track.length)
                embed.add_field(name="Now Playing", value=f"{current_track.title} - {current_track.author}\n"
                                                        f"Duration: {current_position} / {current_duration}", inline=False)

        # Add queued tracks
        queue = self.bot.music_queues.get(inter.guild_id, [])
        track_list = []
        total_duration = 0
        for i, track in enumerate(queue):
            duration = format_duration(track.length)
            if i < 10:  # Show only first 10 tracks to avoid hitting Discord's character limit
                track_list.append(f"{i+1}. {track.title} - {track.author} ({duration})")
            total_duration += track.length

        if track_list:
            embed.add_field(name="Next in Queue", value="\n".join(track_list), inline=False)
            if len(queue) > 10:
                embed.add_field(name="", value=f"And {len(queue) - 10} more...", inline=False)
        else:
            embed.add_field(name="Next in Queue", value="No tracks in queue", inline=False)

        # Add total queue information
        total_tracks = len(queue)
        total_duration_formatted = format_duration(total_duration)
        embed.add_field(name="Queue Info", value=f"Total tracks in queue: {total_tracks}\n"
                                                f"Total duration of queue: {total_duration_formatted}", inline=False)

        await inter.send(embed=embed)

    @nextcord.slash_command(description="Toggle automatic song recommendations", dm_permission=False, guild_ids=[config.DISCORD_GUILD])
    async def recommend(self, inter: nextcord.Interaction):
        """Toggle automatic song recommendations."""
        guild_id = inter.guild_id
        self.bot.recommendation_enabled[guild_id] = not self.bot.recommendation_enabled.get(guild_id, False)
        status = "enabled" if self.bot.recommendation_enabled[guild_id] else "disabled"
        
        embed = nextcord.Embed(title="Recommendation Settings", color=nextcord.Color.blue())
        embed.add_field(name="Status", value=f"Automatic song recommendations are now {status}.", inline=False)
        
        await inter.send(embed=embed)
    @nextcord.slash_command(description="Toggle replay mode for the current song", dm_permission=False, guild_ids=[config.DISCORD_GUILD])
    async def replay(self, inter: nextcord.Interaction):
        """Toggle replay mode for the current song."""
        guild_id = inter.guild_id
        
        # Toggle replay mode
        self.bot.replay_mode[guild_id] = not self.bot.replay_mode.get(guild_id, False)
        
        # Create status message
        status = "enabled" if self.bot.replay_mode[guild_id] else "disabled"
        
        # Check if there's a current song
        current_song = None
        if guild_id in self.bot.current_song:
            current_song = self.bot.current_song[guild_id]
        
        embed = nextcord.Embed(
            title="Replay Mode", 
            color=nextcord.Color.green() if self.bot.replay_mode[guild_id] else nextcord.Color.red()
        )
        
        embed.add_field(name="Status", value=f"Replay mode is now {status}.", inline=False)
        
        if current_song and self.bot.replay_mode[guild_id]:
            embed.add_field(
                name="Current Song", 
                value=f"Will replay: {current_song.title} - {current_song.author}",
                inline=False
            )
        elif self.bot.replay_mode[guild_id]:
            embed.add_field(
                name="Note", 
                value="No song is currently playing. The next song that plays will be set for replay.",
                inline=False
            )
        
        await inter.send(embed=embed)
def setup(bot):
    bot.add_cog(Music(bot))