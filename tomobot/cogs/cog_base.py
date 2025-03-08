from nextcord.ext import commands

class CogBase(commands.Cog):
    """Base class for all cogs."""
    
    def __init__(self, bot):
        self.bot = bot