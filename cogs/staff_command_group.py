from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands

from Constants.vn_allstars_constants import VNA_SERVER_ID
from utils.essentials.command_safe import run_command_safe
from utils.group_command_func.staff import *
from utils.logs.pretty_log import pretty_log
from utils.essentials.role_checks import *


# 🍭──────────────────────────────
#   🎀 Donation Group Command
# 🍭──────────────────────────────
class Staff_Group_Command(commands.Cog):
    """
    Group command for managing staff commands.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    staff_group = app_commands.Group(
        name="staff",
        description="Staff related commands.",
        guild_ids=[VNA_SERVER_ID],
    )

    # 🍭──────────────────────────────
    #   🎀 /staff edit-embed
    # 🍭──────────────────────────────
    @staff_group.command(
        name="edit-embed",
        description="Edit an existing embed message.",
    )
    @app_commands.describe(
        message_link="Link to the message containing the embed you want to edit.",
    )
    @vna_staff()
    async def staff_edit_embed(
        self,
        interaction: discord.Interaction,
        message_link: str,
    ):
        slash_cmd_name = "staff edit-embed"
        await run_command_safe(
            bot=self.bot,
            interaction=interaction,
            command_func=edit_embed_func,
            slash_cmd_name=slash_cmd_name,
            message_link=message_link,
        )
    staff_edit_embed.extras = {"category": "Staff"}

async def setup(bot: commands.Bot):
    await bot.add_cog(Staff_Group_Command(bot))