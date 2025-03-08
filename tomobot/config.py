import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Discord Bot Configuration
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_GUILD = int(os.getenv("DISCORD_GUILD"))

# Lavalink Configuration
LAVALINK_HOST = "lavalink"
LAVALINK_PORT = 2333
LAVALINK_PASSWORD = "youshallnotpass"
LAVALINK_LABEL = "MAIN"

# Music Configuration
MAX_RECOMMENDATION_HISTORY = 100