from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands

from Constants.vn_allstars_constants import VNA_SERVER_ID
from utils.essentials.command_safe import run_command_safe
from utils.essentials.pokemon_autocomplete import (
    pokemon_autocomplete,
    user_alerts_autocomplete,
)
from utils.group_command_func.lottery import *
from utils.logs.pretty_log import pretty_log


# 🍭──────────────────────────────
#   🎀 Lottery Group Command
# 🍭──────────────────────────────
class Lottery_Group_Command(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    lottery = app_commands.Group(
        name="lottery",
        description="Manage lotteries.",
        guild_ids=[VNA_SERVER_ID],
    )

    # 🍭──────────────────────────────
    #   🎀 /lottery pokemon
    # 🍭──────────────────────────────
    @lottery.command(
        name="pokemon",
        description="Start a new Pokémon lottery.",
    )
    @app_commands.autocomplete(pokemon_name=pokemon_autocomplete)
    @app_commands.describe(
        pokemon_name="The Pokémon prize for the lottery.",
        cost_per_ticket="The cost per ticket (e.g., 500).",
        duration="The duration of the lottery (e.g., 1d12h for 1 day and 12 hours).",
        max_tickets="The maximum number of tickets for the lottery.",
    )
    async def lottery_pokemon(
        self,
        interaction: discord.Interaction,
        pokemon_name: str,
        cost_per_ticket: str,
        duration: Optional[str] = None,
        max_tickets: Optional[str] = None,
    ):
        slash_cmd_name = "lottery pokemon"
        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            command_func=pokemon_lottery_func,
            slash_cmd_name=slash_cmd_name,
            pokemon_name=pokemon_name,
            cost_per_ticket=cost_per_ticket,
            duration=duration,
            max_tickets=max_tickets,
        )

    lottery_pokemon.extras = {"category": "Staff"}


async def setup(bot: commands.Bot):
    await bot.add_cog(Lottery_Group_Command(bot))
