import discord
from discord import app_commands
from discord.ext import commands

from Constants.vn_allstars_constants import (
    DEFAULT_EMBED_COLOR,
    VN_ALLSTARS_ROLES,
    VNA_SERVER_ID,
)
from utils.essentials.pokemon_autocomplete import pokemon_autocomplete
from utils.functions.pokemon_func import (
    format_price_w_coin,
    get_display_name,
    get_embed_color_by_rarity,
)
from utils.logs.pretty_log import pretty_log
from utils.visuals.get_pokemon_gif import get_pokemon_gif
from utils.visuals.pretty_defer import pretty_defer
from utils.essentials.role_checks import *

class TestGif(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def __init__(self, bot):
        self.bot = bot

    @app_commands.guilds(discord.Object(id=VNA_SERVER_ID))
    @app_commands.command(name="gif", description="View a pokemon gif")
    @app_commands.autocomplete(pokemon_name=pokemon_autocomplete)
    @app_commands.describe(pokemon_name="The name of the Pokémon to view the gif for.")
    @vna_staff()  # Only allow VNA staff to use this command
    async def gif(self, interaction: discord.Interaction, pokemon_name: str):

        # Defer
        loader = await pretty_defer(
            interaction=interaction,
            content=f"Fetching gif for {pokemon_name}...",
            ephemeral=False,
        )
        # Get the gif URL
        gif_url = get_pokemon_gif(pokemon_name)
        if not gif_url:
            await loader.error(f"Could not find a gif for {pokemon_name}.")
            return
        display_name = get_display_name(pokemon_name)
        embed_color = get_embed_color_by_rarity(pokemon_name)
        embed = discord.Embed(title=display_name, color=embed_color)
        embed.set_image(url=gif_url)
        await loader.success(content="", embed=embed)

    gif.extras = {"category": "Staff"}


async def setup(bot):
    await bot.add_cog(TestGif(bot))
