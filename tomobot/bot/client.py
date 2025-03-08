
import logging
from collections import deque, Counter
import random
import asyncio
import logging
from aiohttp.client_exceptions import ClientConnectorError

import nextcord
from nextcord.ext import commands
import mafic

from tomobot.utils import MusicQueue, MusicLock,LibraryManager
import tomobot.config as config

class MusicBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set up music client
        self.pool = mafic.NodePool(self)
        self.loop.create_task(self.add_nodes())
        
        # Music state tracking
        self.music_queues = {}
        self.text_channels = {}  # Store text channels for each guild
        self.play_locks = {}
        self.current_song = {}
        self.play_history = {}
        
        # Recommendation system
        self.recommendation_enabled = {}
        self.recommendation_history = {}
        self.max_recommendation_history = config.MAX_RECOMMENDATION_HISTORY
        
        # Replay mode
        self.replay_mode = {}  # Store replay mode state for each guild
        # Library manager
        self.library_manager = LibraryManager()

    async def add_nodes(self):
        max_retries = 10
        base_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                logging.info(f"Attempting to connect to Lavalink (attempt {attempt+1}/{max_retries})")
                await self.pool.create_node(
                    host=config.LAVALINK_HOST,
                    port=config.LAVALINK_PORT,
                    label=config.LAVALINK_LABEL,
                    password=config.LAVALINK_PASSWORD,
                )
                logging.info("Successfully connected to Lavalink")
                return
            except ClientConnectorError:
                # Exponential backoff with jitter for more reliable retries
                delay = min(30, base_delay * (2 ** attempt)) * (0.8 + 0.4 * random.random())
                logging.warning(f"Connection attempt {attempt+1} failed, retrying in {delay:.2f} seconds...")
                await asyncio.sleep(delay)
        
        logging.error("Failed to connect to Lavalink after multiple attempts")

    async def on_ready(self):
        """Called when the bot is ready."""
        logging.info(f'We have logged in as {self.user}')
        
    async def on_message(self, message):
        """Handle incoming messages."""
        # Skip messages from bots to prevent loops
        if message.author.bot:
            return
            
        # Process commands in messages if they exist
        await self.process_commands(message)