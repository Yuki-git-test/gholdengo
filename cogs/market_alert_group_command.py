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
from utils.group_command_func.markert_alert import *
from utils.logs.pretty_log import pretty_log


# 🍭──────────────────────────────
#   🎀 Market Alert Group Command
# 🍭──────────────────────────────
class Market_Alert_Group_Command(commands.Cog):
    """
    Group command for managing market alerts.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    market_alert = app_commands.Group(
        name="market-alert",
        description="Manage your market alerts.",
        guild_ids=[VNA_SERVER_ID],
    )

    # 🍭──────────────────────────────
    #   🎀 /market-alert add
    # 🍭──────────────────────────────
    @market_alert.command(
        name="add",
        description="Add a new market alert.",
    )
    @app_commands.autocomplete(pokemon=pokemon_autocomplete)
    @app_commands.describe(
        pokemon="The Pokémon to set the market alert for.",
        max_price="The maximum price for the Pokémon.",
        channel="The channel to send the alert to.",
        ping_role="Whether to ping your custom role or not.",
    )
    async def market_alert_add(
        self,
        interaction: discord.Interaction,
        pokemon: str,
        max_price: str,
        channel: discord.TextChannel,
        ping_role: Literal["yes", "no"],
    ):
        slash_cmd_name = "market-alert add"
        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            command_func=add_market_alert_func,
            slash_cmd_name=slash_cmd_name,
            pokemon=pokemon,
            max_price=max_price,
            channel=channel,
            ping_role=ping_role,
        )

    market_alert_add.extras = {"category": "Public"}

    # 🍭──────────────────────────────
    #   🎀 /market-alert mine
    # 🍭──────────────────────────────
    @market_alert.command(
        name="mine",
        description="View your existing market alerts.",
    )
    async def market_alert_mine(self, interaction: discord.Interaction):
        slash_cmd_name = "market-alert mine"
        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            slash_cmd_name=slash_cmd_name,
            command_func=mine_market_alert_func,
        )

    market_alert_mine.extras = {"category": "Public"}

    # 🍭──────────────────────────────
    #   🎀 /market-alert remove
    # 🍭──────────────────────────────
    @market_alert.command(
        name="remove",
        description="Remove an/all existing market alert(s).",
    )
    @app_commands.autocomplete(pokemon=user_alerts_autocomplete)
    @app_commands.describe(
        pokemon="The Pokémon to remove the market alert for, or 'all' to remove all alerts."
    )
    async def market_alert_remove(
        self,
        interaction: discord.Interaction,
        pokemon: str,
    ):
        slash_cmd_name = "market-alert remove"
        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            command_func=remove_market_alert_func,
            slash_cmd_name=slash_cmd_name,
            pokemon=pokemon,
        )

    market_alert_remove.extras = {"category": "Public"}

    # 🍭──────────────────────────────
    #   🎀 /market-alert update
    # 🍭──────────────────────────────
    @market_alert.command(
        name="update",
        description="Update an existing market alert.",
    )
    @app_commands.autocomplete(pokemon=user_alerts_autocomplete)
    @app_commands.describe(
        pokemon="The Pokémon to update the market alert for.",
        new_max_price="The new maximum price for the Pokémon.",
        new_channel="The new channel to send the alert to.",
        ping_role="Whether to ping your custom role or not.",
    )
    async def market_alert_update(
        self,
        interaction: discord.Interaction,
        pokemon: str,
        new_max_price: str = None,
        new_channel: discord.TextChannel = None,
        ping_role: Literal["yes", "no"] = None,
    ):
        slash_cmd_name = "market-alert update"
        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            command_func=update_market_alert_func,
            pokemon=pokemon,
            slash_cmd_name=slash_cmd_name,
            new_max_price=new_max_price,
            new_channel=new_channel,
            ping_role=ping_role,
        )

    market_alert_update.extras = {"category": "Public"}


async def setup(bot: commands.Bot):
    await bot.add_cog(Market_Alert_Group_Command(bot))
