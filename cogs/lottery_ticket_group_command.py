from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands

from Constants.vn_allstars_constants import VNA_SERVER_ID
from utils.db.lottery import active_lottery_autocomplete, ended_lottery_autocomplete
from utils.essentials.command_safe import run_command_safe

from utils.group_command_func.lottery_tickets import *
from utils.logs.pretty_log import pretty_log
from utils.essentials.role_checks import *

# 🍭──────────────────────────────
#   🎀 Lottery Ticket Group Command
# 🍭──────────────────────────────
class Lottery_Ticket_Group_Command(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    lottery_ticket = app_commands.Group(
        name="lottery-ticket",
        description="Manage lottery tickets command.",
        guild_ids=[VNA_SERVER_ID],
    )

    # 🍭──────────────────────────────
    #   🎀 /lottery-ticket view
    # 🍭──────────────────────────────
    @lottery_ticket.command(
        name="view",
        description="View your lottery tickets across all active lotteries.",
    )
    async def lottery_ticket_view(
        self,
        interaction: discord.Interaction,
    ):
        slash_cmd_name = "lottery-ticket view"
        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            command_func=view_lottery_tickets_func,
            slash_cmd_name=slash_cmd_name,
        )

    lottery_ticket_view.extras = {"category": "Public"}

    # 🍭──────────────────────────────
    #   🎀 /lottery-ticket list
    # 🍭──────────────────────────────
    @lottery_ticket.command(
        name="list",
        description="List all tickets for a specific lottery.",
    )
    @app_commands.autocomplete(
        message_id=active_lottery_autocomplete,
    )
    @app_commands.describe(
        message_id="The message ID of the lottery to view tickets for."
    )
    @vna_staff()  # Only allow VNA staff to view all tickets for a lottery
    async def lottery_ticket_list(
        self,
        interaction: discord.Interaction,
        message_id: str,
    ):
        slash_cmd_name = "lottery-ticket list"
        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            command_func=list_lottery_tickets_func,
            slash_cmd_name=slash_cmd_name,
            message_id=message_id,
        )

    lottery_ticket_list.extras = {"category": "Staff"}


async def setup(bot: commands.Bot):
    await bot.add_cog(Lottery_Ticket_Group_Command(bot))
