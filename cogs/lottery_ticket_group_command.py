from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands

from Constants.vn_allstars_constants import VNA_SERVER_ID
from utils.db.lottery import active_lottery_autocomplete, ended_lottery_autocomplete
from utils.essentials.command_safe import run_command_safe
from utils.essentials.role_checks import *
from utils.group_command_func.lottery_tickets import *
from utils.logs.pretty_log import pretty_log


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

    # 🍭──────────────────────────────
    #   🎀 /lottery-ticket add
    # 🍭──────────────────────────────
    @lottery_ticket.command(
        name="add",
        description="Add lottery tickets to a user's entry in a lottery.",
    )
    @app_commands.autocomplete(
        message_id=active_lottery_autocomplete,
    )
    @app_commands.describe(
        message_id="The message ID of the lottery to add tickets to.",
        member="The member to add tickets for.",
        amount="The amount of tickets to add.",
    )
    @vna_staff()  # Only allow VNA staff to add tickets to a lottery
    async def lottery_ticket_add(
        self,
        interaction: discord.Interaction,
        message_id: str,
        member: discord.Member,
        amount: str,
    ):
        slash_cmd_name = "lottery-ticket add"
        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            command_func=add_lottery_tickets_func,
            slash_cmd_name=slash_cmd_name,
            message_id=message_id,
            member=member,
            amount=amount,
        )

    lottery_ticket_add.extras = {"category": "Staff"}

    # 🍭──────────────────────────────
    #   🎀 /lottery-ticket remove
    # 🍭──────────────────────────────
    @lottery_ticket.command(
        name="remove",
        description="Remove lottery tickets from a user's entry in a lottery.",
    )
    @app_commands.autocomplete(
        message_id=active_lottery_autocomplete,
    )
    @app_commands.describe(
        message_id="The message ID of the lottery to remove tickets from.",
        member="The member to remove tickets from.",
        amount="The amount of tickets to remove.",
    )
    @vna_staff()  # Only allow VNA staff to remove tickets from a lottery
    async def lottery_ticket_remove(
        self,
        interaction: discord.Interaction,
        message_id: str,
        member: discord.Member,
        amount: str,
    ):
        slash_cmd_name = "lottery-ticket remove"
        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            command_func=remove_lottery_tickets_func,
            slash_cmd_name=slash_cmd_name,
            message_id=message_id,
            member=member,
            amount=amount,
        )

    lottery_ticket_remove.extras = {"category": "Staff"}


async def setup(bot: commands.Bot):
    await bot.add_cog(Lottery_Ticket_Group_Command(bot))

