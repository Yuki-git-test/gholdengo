from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands

from Constants.vn_allstars_constants import VNA_SERVER_ID
from utils.essentials.command_safe import run_command_safe
from utils.group_command_func.giveaway import *
from utils.logs.pretty_log import pretty_log


# 🍭──────────────────────────────
#   🎀 Giveaway Group Command
# 🍭──────────────────────────────
class Giveaway_Group_Command(commands.Cog):
    """
    Group command for managing giveaways.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    giveaway = app_commands.Group(
        name="giveaway",
        description="Manage giveaways.",
        guild_ids=[VNA_SERVER_ID],
    )

    # 🍭──────────────────────────────
    #   🎀 /giveaway start
    # 🍭──────────────────────────────
    @giveaway.command(
        name="start",
        description="Start a new giveaway.",
    )
    @app_commands.describe(
        prize="The prize for the giveaway.",
        duration="The duration of the giveaway (e.g., 1d12h for 1 day and 12 hours).",
        winners="The number of winners for the giveaway.",
        giveaway_type="The type of giveaway (general or clan).",
        has_message="Whether the giveaway is associated with an existing message.",
        image_link="An optional image link for the giveaway embed.",
    )
    async def giveaway_create(
        self,
        interaction: discord.Interaction,
        prize: str,
        duration: str,
        winners: int,
        giveaway_type: Literal["general", "clan", "server booster"],
        has_message: bool = False,
        image_link: str = None,
    ):
        slash_cmd_name = "giveaway start"
        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            command_func=create_giveaway_func,
            slash_cmd_name=slash_cmd_name,
            prize=prize,
            duration=duration,
            winners=winners,
            giveaway_type=giveaway_type,
            has_message=has_message,
            image_link=image_link,
        )

    giveaway_create.extras = {"category": "Staff"}

    # 🍭──────────────────────────────
    #   🎀 /giveaway snipe
    # 🍭──────────────────────────────
    @giveaway.command(
        name="snipe",
        description="Start a quick snipe giveaway.",
    )
    @app_commands.describe(
        prize="Prize for the giveaway",
        duration="Duration of the giveaway in seconds",
        winners="Number of winners (default is 1)",
    )
    async def giveaway_snipe(
        self,
        interaction: discord.Interaction,
        prize: str,
        duration: int,
        winners: int = 1,
    ):
        slash_cmd_name = "giveaway snipe"
        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            command_func=snipe_ga_func,
            slash_cmd_name=slash_cmd_name,
            prize=prize,
            duration=duration,
            winners=winners,
        )

    giveaway_snipe.extras = {"category": "Staff"}

    # 🍭──────────────────────────────
    #   🎀 /giveaway end
    # 🍭──────────────────────────────
    @giveaway.command(
        name="end",
        description="End an active giveaway.",
    )
    @app_commands.describe(
        message_id="The ID of the giveaway message to end.",
    )
    async def giveaway_end(
        self,
        interaction: discord.Interaction,
        message_id: str,
    ):
        slash_cmd_name = "giveaway end"
        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            command_func=end_giveaway_func,
            slash_cmd_name=slash_cmd_name,
            message_id=message_id,
        )

    giveaway_end.extras = {"category": "Staff"}

    # 🍭──────────────────────────────
    #   🎀 /giveaway cancel
    # 🍭──────────────────────────────
    @giveaway.command(
        name="cancel",
        description="Cancel an active giveaway.",
    )
    @app_commands.describe(
        message_id="The ID of the giveaway message to cancel.",
    )
    async def giveaway_cancel(
        self,
        interaction: discord.Interaction,
        message_id: str,
    ):
        slash_cmd_name = "giveaway cancel"
        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            command_func=cancel_giveaway_func,
            slash_cmd_name=slash_cmd_name,
            message_id=message_id,
        )

    giveaway_cancel.extras = {"category": "Staff"}

    # 🍭──────────────────────────────
    #   🎀 /giveaway reroll
    # 🍭──────────────────────────────
    @giveaway.command(
        name="reroll",
        description="Reroll a giveaway to select new winners.",
    )
    @app_commands.describe(
        message_id="The ID of the giveaway message to reroll.",
        reroll_count="The number of times to reroll (default is 1).",
    )
    async def giveaway_reroll(
        self,
        interaction: discord.Interaction,
        message_id: str,
        reroll_count: int = 1,
    ):
        slash_cmd_name = "giveaway reroll"
        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            command_func=reroll_giveaway_func,
            slash_cmd_name=slash_cmd_name,
            message_id=message_id,
            reroll_count=reroll_count,
        )

    giveaway_reroll.extras = {"category": "Staff"}


async def setup(bot: commands.Bot):
    await bot.add_cog(Giveaway_Group_Command(bot))
