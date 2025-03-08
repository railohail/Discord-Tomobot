import logging
from collections import Counter, deque
import random

import nextcord
import mafic

import tomobot.config  as config
from tomobot.utils import format_duration

async def on_track_start(bot, event: mafic.TrackStartEvent):
    """Handle track start events."""
    player = event.player
    track = event.track
    guild_id = player.guild.id
    bot.current_song[guild_id] = track
    
    # Record play history
    if guild_id not in bot.play_history:
        bot.play_history[guild_id] = []
    bot.play_history[guild_id].append(track.author)
    
    # Keep only the last 100 played songs
    bot.play_history[guild_id] = bot.play_history[guild_id][-100:]
    
    if guild_id in bot.text_channels:
        embed = nextcord.Embed(title="Now Playing", color=nextcord.Color.green())
        embed.add_field(name="Title", value=track.title, inline=False)
        embed.add_field(name="Author", value=track.author, inline=False)
        await bot.text_channels[guild_id].send(embed=embed)
    
    # Check if recommendations are needed
    await check_and_recommend(bot, player, guild_id)

async def on_track_end(bot, event: mafic.TrackEndEvent):
    """Handle track end events."""
    player = event.player
    guild_id = player.guild.id
    
    # Check if this is a skip operation
    is_skip = False
    if hasattr(bot, 'skip_operations'):
        is_skip = bot.skip_operations.get(guild_id, False)
        # Reset the skip flag
        if is_skip:
            bot.skip_operations[guild_id] = False
    
    # Check if we're in replay mode and should replay the current song
    # Only replay if replay mode is on and this is not a skip operation
    if bot.replay_mode.get(guild_id, False) and guild_id in bot.current_song and not is_skip:
        # Store the current song before it gets popped
        current_song = bot.current_song[guild_id]
        
        # Play the same song again
        try:
            await player.play(current_song)
            if guild_id in bot.text_channels:
                embed = nextcord.Embed(title="Replaying", color=nextcord.Color.blue())
                embed.add_field(name="Title", value=current_song.title, inline=False)
                embed.add_field(name="Author", value=current_song.author, inline=False)
                await bot.text_channels[guild_id].send(embed=embed)
            return  # Skip the rest of the function
        except Exception as e:
            logging.error(f"Error replaying track: {e}")
            # If replay fails, continue with normal flow
    
    # Normal flow (if not in replay mode or replay failed)
    bot.current_song.pop(guild_id, None)  # Clear the current song
    
    # Manage recommendation history
    manage_recommendation_history(bot, guild_id)
    
    # Check if there are more tracks in the queue
    if guild_id in bot.music_queues and bot.music_queues[guild_id]:
        await play_next(bot, player)
    else:
        if guild_id in bot.text_channels:
            embed = nextcord.Embed(title="Playback Finished", color=nextcord.Color.blue())
            embed.add_field(name="Message", value="Queue is empty. Playback finished.", inline=False)
            await bot.text_channels[guild_id].send(embed=embed)
        await player.disconnect()

async def play_next(bot, player: mafic.Player):
    """Play the next track in the queue."""
    guild_id = player.guild.id
    if not player.connected:
        if guild_id in bot.music_queues:
            bot.music_queues[guild_id].clear()
        return

    if guild_id in bot.music_queues and bot.music_queues[guild_id]:
        next_track = bot.music_queues[guild_id].popleft()
        try:
            await player.play(next_track)
            bot.current_song[guild_id] = next_track
            logging.info(f"Started playing: {next_track.title}")
        except Exception as e:
            logging.error(f"Error playing track: {e}")
            if guild_id in bot.text_channels:
                embed = nextcord.Embed(title="Playback Error", color=nextcord.Color.red())
                embed.add_field(name="Error", value=f"Error playing track: {e}", inline=False)
                await bot.text_channels[guild_id].send(embed=embed)
            await play_next(bot, player)
    else:
        if guild_id in bot.text_channels:
            embed = nextcord.Embed(title="Playback Finished", color=nextcord.Color.blue())
            embed.add_field(name="Message", value="Queue is empty. Playback finished.", inline=False)
            await bot.text_channels[guild_id].send(embed=embed)
        await player.disconnect()
    
    # Check for recommendations after playing a track
    await check_and_recommend(bot, player, guild_id)

async def check_and_recommend(bot, player: mafic.Player, guild_id: int):
    """Check if recommendations are needed and add them to the queue."""
    if (bot.recommendation_enabled.get(guild_id, False) and 
        len(bot.music_queues[guild_id]) <= 1 and 
        guild_id in bot.play_history and 
        bot.play_history[guild_id]):
        
        # Initialize recommendation history for the guild if it doesn't exist
        if guild_id not in bot.recommendation_history:
            bot.recommendation_history[guild_id] = deque(maxlen=bot.max_recommendation_history)
        
        # Get the most common authors from play history
        author_counts = Counter(bot.play_history[guild_id])
        common_authors = [author for author, _ in author_counts.most_common()]
        
        # Randomly select up to 10 authors (or all if less than 10)
        num_authors = min(10, len(common_authors))
        selected_authors = random.sample(common_authors, num_authors)
        
        recommended_tracks = 0
        added_tracks = set()  # To keep track of added tracks and avoid duplicates
        
        for author in selected_authors:
            if recommended_tracks >= 10:
                break
            
            query = f"{author} music"
            try:
                results = await player.fetch_tracks(query, search_type=mafic.SearchType.YOUTUBE)
                if results:
                    for track in results:
                        track_id = (track.title, track.author)
                        # Check if the track is not in recommendation history, not in added_tracks, and not in the current queue
                        if (track_id not in bot.recommendation_history[guild_id] and
                            track_id not in added_tracks and
                            not any(t.title == track.title and t.author == track.author for t in bot.music_queues[guild_id])):
                            
                            bot.music_queues[guild_id].append(track)
                            added_tracks.add(track_id)
                            bot.recommendation_history[guild_id].append(track_id)
                            recommended_tracks += 1
                            if guild_id in bot.text_channels:
                                embed = nextcord.Embed(title="Recommended Track Added", color=nextcord.Color.green())
                                embed.add_field(name="Title", value=track.title, inline=False)
                                embed.add_field(name="Author", value=track.author, inline=False)
                                await bot.text_channels[guild_id].send(embed=embed)
                            break  # Move to the next author after adding one track
            except Exception as e:
                logging.error(f"Error fetching recommendation for {author}: {e}")

def manage_recommendation_history(bot, guild_id: int):
    """Manage the recommendation history for a guild."""
    if guild_id in bot.recommendation_history:
        while len(bot.recommendation_history[guild_id]) > bot.max_recommendation_history:
            bot.recommendation_history[guild_id].popleft()