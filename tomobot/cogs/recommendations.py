import random
from collections import Counter

import nextcord
from nextcord.ext import commands
import mafic


from tomobot.utils import format_duration
import tomobot.config as config
from tomobot.cogs import CogBase

class Recommendations(CogBase):
    """Music recommendation commands."""
    
    @nextcord.slash_command(description="Get song recommendations based on your listening history", dm_permission=False, guild_ids=[config.DISCORD_GUILD])
    async def get_recommendations(self, inter: nextcord.Interaction, count: int = 5):
        """Get song recommendations based on your listening history."""
        guild_id = inter.guild_id
        
        if guild_id not in self.bot.play_history or not self.bot.play_history[guild_id]:
            return await inter.response.send_message("You don't have any listening history yet. Play some songs first!")
        
        if not inter.guild.voice_client or not isinstance(inter.guild.voice_client, mafic.Player):
            if not inter.user.voice:
                return await inter.response.send_message("You need to be in a voice channel to get recommendations!")
            
            try:
                player = await inter.user.voice.channel.connect(cls=mafic.Player)
            except Exception as e:
                return await inter.response.send_message(f"Failed to connect to voice channel: {str(e)}")
        else:
            player = inter.guild.voice_client
        
        await inter.response.defer()
        
        # Get the most common authors from play history
        author_counts = Counter(self.bot.play_history[guild_id])
        common_authors = [author for author, _ in author_counts.most_common()]
        
        # Randomly select authors (or all if less than count)
        num_authors = min(count, len(common_authors))
        selected_authors = random.sample(common_authors, num_authors)
        
        recommended_tracks = []
        for author in selected_authors:
            if len(recommended_tracks) >= count:
                break
                
            query = f"{author} music"
            try:
                results = await player.fetch_tracks(query, search_type=mafic.SearchType.YOUTUBE)
                if results:
                    # Find a track that's not already in recommended_tracks
                    for track in results:
                        track_id = (track.title, track.author)
                        if not any(r.title == track.title and r.author == track.author for r in recommended_tracks):
                            recommended_tracks.append(track)
                            break
            except Exception as e:
                continue
        
        if not recommended_tracks:
            if not inter.guild.voice_client or player.guild.id != guild_id:
                await player.disconnect()
            return await inter.followup.send("Couldn't find any recommendations for you. Try playing more music!")
        
        # Create recommendation options
        options = [
            nextcord.SelectOption(
                label=f"{i+1}. {track.title[:50]}",
                description=f"By {track.author[:50]}",
                value=str(i)
            ) for i, track in enumerate(recommended_tracks)
        ]
        
        select = nextcord.ui.Select(
            placeholder="Choose a track to add to queue...",
            options=options
        )
        
        async def select_callback(interaction: nextcord.Interaction):
            selected_index = int(select.values[0])
            selected_track = recommended_tracks[selected_index]
            
            if guild_id not in self.bot.music_queues:
                self.bot.music_queues[guild_id] = []
                
            self.bot.music_queues[guild_id].append(selected_track)
            
            embed = nextcord.Embed(title="Recommendation Added", color=nextcord.Color.green())
            embed.add_field(name="Title", value=selected_track.title, inline=False)
            embed.add_field(name="Author", value=selected_track.author, inline=False)
            
            await interaction.response.send_message(embed=embed)
            
            if guild_id not in self.bot.current_song:
                from bot.events import play_next
                await play_next(self.bot, player)
        
        select.callback = select_callback
        view = nextcord.ui.View(timeout=60)
        view.add_item(select)
        
        embed = nextcord.Embed(title="Song Recommendations", color=nextcord.Color.blue())
        embed.add_field(name="Based On", value="Your listening history", inline=False)
        embed.add_field(name="Instructions", value="Select a track to add to your queue:", inline=False)
        
        await inter.followup.send(embed=embed, view=view)
        
        async def on_timeout():
            if not player.current and player.connected:
                await player.disconnect()
        
        view.on_timeout = on_timeout

def setup(bot):
    bot.add_cog(Recommendations(bot))