from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands

from Constants.vn_allstars_constants import VNA_SERVER_ID
from utils.db.lottery import active_lottery_autocomplete, ended_lottery_autocomplete
from utils.essentials.command_safe import run_command_safe
from utils.db.market_value_db import pokemon_autocomplete
from utils.group_command_func.lottery import *
from utils.logs.pretty_log import pretty_log

from utils.essentials.role_checks import *

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
    @vna_staff()
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

    # 🍭──────────────────────────────
    #   🎀 /lottery coin
    # 🍭──────────────────────────────
    @lottery.command(
        name="coin",
        description="Start a new Coin lottery.",
    )
    @app_commands.describe(
        cost_per_ticket="The cost per ticket (e.g., 500).",
        base_pot="An optional starting amount to add to the lottery pot.",
        duration="The duration of the lottery (e.g., 1d12h for 1 day and 12 hours).",
        max_tickets="The maximum number of tickets for the lottery.",
    )
    @vna_staff()  # Only allow VNA staff to create coin lotteries
    async def lottery_coin(
        self,
        interaction: discord.Interaction,
        cost_per_ticket: str,
        base_pot: Optional[str] = None,
        duration: Optional[str] = None,
        max_tickets: Optional[str] = None,
    ):
        slash_cmd_name = "lottery coin"
        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            command_func=coin_lottery_func,
            slash_cmd_name=slash_cmd_name,
            cost_per_ticket=cost_per_ticket,
            base_pot=base_pot,
            duration=duration,
            max_tickets=max_tickets,
        )

    lottery_coin.extras = {"category": "Staff"}

    # 🍭──────────────────────────────
    #   🎀 /lottery end
    # 🍭──────────────────────────────
    @lottery.command(
        name="end",
        description="End an active lottery.",
    )
    @app_commands.autocomplete(message_id=active_lottery_autocomplete)
    @app_commands.describe(
        message_id="Select the lottery to end (by its prize name).",
    )
    @vna_staff()  # Only allow VNA staff to end lotteries
    async def lottery_end(
        self,
        interaction: discord.Interaction,
        message_id: str,
    ):
        slash_cmd_name = "lottery end"
        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            command_func=end_lottery_func,
            slash_cmd_name=slash_cmd_name,
            message_id=int(message_id),
        )

    lottery_end.extras = {"category": "Staff"}

    # 🍭──────────────────────────────
    #   🎀 /lottery reroll
    # 🍭──────────────────────────────
    @lottery.command(
        name="reroll",
        description="Reroll a finished lottery.",
    )
    @app_commands.autocomplete(message_id=ended_lottery_autocomplete)
    @app_commands.describe(
        message_id="Select the lottery to reroll (by its prize name).",
    )
    @vna_staff()  # Only allow VNA staff to reroll lotteries
    async def lottery_reroll(
        self,
        interaction: discord.Interaction,
        message_id: str,
    ):
        slash_cmd_name = "lottery reroll"
        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            command_func=reroll_lottery_func,
            slash_cmd_name=slash_cmd_name,
            message_id=int(message_id),
        )

    lottery_reroll.extras = {"category": "Staff"}


async def setup(bot: commands.Bot):
    await bot.add_cog(Lottery_Group_Command(bot))
