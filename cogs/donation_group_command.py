from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands

from Constants.vn_allstars_constants import VNA_SERVER_ID
from utils.essentials.command_safe import run_command_safe
from utils.group_command_func.donation import *
from utils.logs.pretty_log import pretty_log


# 🍭──────────────────────────────
#   🎀 Donation Group Command
# 🍭──────────────────────────────
class Donation_Group_Command(commands.Cog):
    """
    Group command for managing market alerts.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    donation_group = app_commands.Group(
        name="donation",
        description="Donation related commands.",
        guild_ids=[VNA_SERVER_ID],
    )

    # 🍭──────────────────────────────
    #   🎀 /donation overall-leaderboard
    # 🍭──────────────────────────────
    @donation_group.command(
        name="overall-leaderboard",
        description="View the overall donations leaderboard.",
    )
    async def donation_overall_leaderboard(
        self,
        interaction: discord.Interaction,
    ):
        slash_cmd_name = "donation overall-leaderboard"
        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            command_func=view_overall_leaderboard,
            slash_cmd_name=slash_cmd_name,
        )

    donation_overall_leaderboard.extras = {"category": "Public"}

    # 🍭──────────────────────────────
    #   🎀 /donation monthly-leaderboard
    # 🍭──────────────────────────────
    @donation_group.command(
        name="monthly-leaderboard",
        description="View the monthly donations leaderboard.",
    )
    async def donation_monthly_leaderboard(
        self,
        interaction: discord.Interaction,
    ):
        slash_cmd_name = "donation monthly-leaderboard"
        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            slash_cmd_name=slash_cmd_name,
            command_func=view_monthly_donation_leaderboard_func,
        )

    donation_monthly_leaderboard.extras = {"category": "Public"}

    # 🍭──────────────────────────────
    #   🎀 /donation view
    # 🍭──────────────────────────────
    @donation_group.command(
        name="view",
        description="View your donation stats.",
    )
    @app_commands.describe(
        member="Optionally view another member's donation stats.",
    )
    async def donation_view(
        self,
        interaction: discord.Interaction,
        member: discord.Member = None,
    ):
        slash_cmd_name = "donation view"
        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            slash_cmd_name=slash_cmd_name,
            command_func=view_donation_func,
            member=member,
        )

    donation_view.extras = {"category": "Public"}

    # 🍭──────────────────────────────
    #   🎀 /donation update
    # 🍭──────────────────────────────
    @donation_group.command(
        name="update",
        description="Update a member's donation amount.",
    )
    @app_commands.describe(
        member="The member whose donation record you want to update.",
        total_donations="The new total donations amount for the member.",
        monthly_donations="The new monthly donations amount for the member.",
    )
    async def donation_update(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        total_donations: Optional[str] = None,
        monthly_donations: Optional[str] = None,
    ):
        slash_cmd_name = "donation update"
        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            slash_cmd_name=slash_cmd_name,
            command_func=update_donation_func,
            member=member,
            total_donations=total_donations,
            monthly_donations=monthly_donations,
        )
    donation_update.extras = {"category": "Staff"}


async def setup(bot: commands.Bot):
    await bot.add_cog(Donation_Group_Command(bot))
