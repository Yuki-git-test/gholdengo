import asyncio
import random
import time
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import Button, Modal, TextInput, View

import utils.cache.global_variables as globals
from Constants.aesthetic import *
from Constants.giveaway import (
    BLACKLISTED_ROLES,
    REG_GA_MIN_DURATION_SECONDS,
    REQUIRED_ROLES,
    Extra_Entries,
)
from Constants.vn_allstars_constants import (
    DEFAULT_EMBED_COLOR,
    KHY_USER_ID,
    VN_ALLSTARS_ROLES,
    VN_ALLSTARS_TEXT_CHANNELS,
)
from utils.cache.global_variables import TESTING_GA
from utils.db.ga_db import (
    update_giveaway_message_id,
    update_giveaway_thread_id,
    upsert_giveaway,
)
from utils.essentials.role_checks import *
from utils.functions.snipe_ga_func import SnipeGAView, build_snipe_ga_embed
from utils.giveaway.giveaway_funcs import build_ga_embed, can_host_ga
from utils.giveaway.views import GiveawayButtonsView
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log
from utils.logs.server_log import send_log_to_server_log
from utils.parsers.duration import parse_total_duration, parse_total_seconds
from utils.visuals.pretty_defer import pretty_defer


# For regular ga
async def create_ga_prefix(bot, message: discord.Message):

    user = message.author
    # Check if user has required roles to use the command
    user_roles = [role.id for role in user.roles]
    if not any(role in user_roles for role in REQUIRED_ROLES):
        required_roles_mentions = ", ".join(
            f"<@&{role_id}>" for role_id in REQUIRED_ROLES
        )
        content = f"You do not have permission to use this command. Only members with the following roles can use it: {required_roles_mentions}"
        await message.reply(content)
        return

    question_one = "What type of giveaway do you want to create? Please respond with either `clan` or `general`."
    cancel_str = "To cancel the giveaway creation process, type 'cancel' at any time."
    description = f"{question_one}\n\n{cancel_str}"
    embed = discord.Embed(
        title="Enter Giveaway Type",
        description=description,
        color=DEFAULT_EMBED_COLOR,
    )
    embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)

    def check(m):
        return m.author == user and m.channel == message.channel

    try:
        await message.reply(embed=embed)
        type_response = await bot.wait_for("message", check=check, timeout=120)
        if type_response.content.lower() == "cancel":
            await message.channel.send("Giveaway creation cancelled.")
            return

        # Extract giveaway type and validate must either be "clan" or "general"
        giveaway_type = type_response.content.lower()
        if giveaway_type not in ["clan", "general"]:
            await message.channel.send(
                "Invalid giveaway type. Please respond with either `clan` or `general`. Giveaway creation cancelled."
            )
            return

        # Ask for duration
        duration_question = "How long should the giveaway last? Please provide the duration (e.g. 1d, 2h, 30m)."
        description = f"{duration_question}\n\nType `cancel` to stop this process."
        duration_question_embed = embed.copy()
        duration_question_embed.description = description
        duration_question_embed.title = "Enter Giveaway Duration"
        await message.reply(embed=duration_question_embed)
        duration_response = await bot.wait_for("message", check=check, timeout=120)
        if duration_response.content.lower() == "cancel":
            await message.channel.send("Giveaway creation cancelled.")
            return
        try:
            duration_seconds = parse_total_seconds(duration_response.content)
            if duration_seconds <= 0:
                raise
            # Must not be less than 30 minutes unless in testing mode
            if duration_seconds < REG_GA_MIN_DURATION_SECONDS and not TESTING_GA:
                await message.channel.send(
                    "Giveaway duration must be at least 30 minutes. Giveaway creation cancelled."
                )
                return
        except ValueError:
            await message.channel.send(
                "Invalid duration format. Please enter a valid duration (e.g. '5m', '2h'). Giveaway creation cancelled."
            )
            return
        total_duration = duration_seconds + int(time.time())

        # Ask for number of winners
        winners_question = "How many winners should there be for this giveaway? (Type a number, e.g. 1)"
        description = f"{winners_question}\n\nType `cancel` to stop this process."
        winners_question_embed = embed.copy()
        winners_question_embed.description = description
        winners_question_embed.title = "Enter Number of Winners"
        await message.reply(embed=winners_question_embed)
        winners_response = await bot.wait_for("message", check=check, timeout=120)
        if winners_response.content.lower() == "cancel":
            await message.channel.send("Giveaway creation cancelled.")
            return
        try:
            winners = int(winners_response.content)
            if winners < 1 or winners > 25:
                raise ValueError
        except ValueError:
            await message.channel.send(
                "Invalid number of winners. Please enter a number between 1 and 25. Giveaway creation cancelled."
            )
            return

        # Ask for prize
        prize_question = (
            f"There will be {winners} winner(s). What do you want to giveaway?"
        )
        description = f"{prize_question}\n\nType `cancel` to stop this process."
        prize_question_embed = embed.copy()
        prize_question_embed.description = description
        prize_question_embed.title = "Enter Giveaway Prize"
        await message.reply(embed=prize_question_embed)
        prize_response = await bot.wait_for("message", check=check, timeout=120)
        if prize_response.content.lower() == "cancel":
            await message.channel.send("Giveaway creation cancelled.")
            return
        prize = prize_response.content

        # Ask for message
        special_msg_question = f"Is there any special message you want to include in the giveaway announcement? If not, type `no`."
        description = f"{special_msg_question}\n\nType `cancel` to stop this process."
        special_msg_question_embed = embed.copy()
        special_msg_question_embed.description = description
        special_msg_question_embed.title = "Enter Giveaway Special Message"
        await message.reply(embed=special_msg_question_embed)
        special_msg_response = await bot.wait_for("message", check=check, timeout=120)
        if special_msg_response.content.lower() == "cancel":
            await message.channel.send("Giveaway creation cancelled.")
            return
        normalized = special_msg_response.content.lower().strip()
        if normalized in {"no", "none", ""}:
            special_msg = None
        else:
            special_msg = special_msg_response.content

        # ...existing code...

        if giveaway_type == "clan":
            channel_id = VN_ALLSTARS_TEXT_CHANNELS.clan_giveaway
        else:
            channel_id = VN_ALLSTARS_TEXT_CHANNELS.giveaway
        if TESTING_GA:
            channel_id = VN_ALLSTARS_TEXT_CHANNELS.khys_chamber

        giveaway_channel = message.guild.get_channel(channel_id)
        if giveaway_channel is None:
            await message.channel.send(
                "Giveaway channel not found. Giveaway creation cancelled."
            )
            return

        host = message.author
        # Create giveaway embed and view

        success, error_msg = await ga_create_handler(
            bot,
            host,
            giveaway_type,
            winners,
            giveaway_channel,
            prize,
            total_duration,
            special_msg,
        )
        if not success:
            await message.channel.send(
                f"An error occurred while creating the giveaway: {error_msg}. Giveaway creation cancelled."
            )
            return

        # Final confirmation embed
        giveaway_type_display = (
            "Clan Giveaway" if giveaway_type == "clan" else "General Giveaway"
        )
        confirm_embed = discord.Embed(
            title=f"{giveaway_type_display} Created!",
            description=(
                f"✅ Successfully created that giveaway in {giveaway_channel.mention}!\n"
                f"**Duration:** {duration_response.content}\n"
                f"**Winners:** {winners}\n"
                f"**Prize:** {prize}"
            ),
            color=discord.Color.green(),
        )
        confirm_embed.set_author(
            name=user.display_name, icon_url=user.display_avatar.url
        )
        await message.reply(embed=confirm_embed)

    except asyncio.TimeoutError:
        await message.channel.send("You took too long to reply. Giveaway cancelled.")


async def ga_create_handler(
    bot,
    host: discord.Member,
    giveaway_type: str,
    winners: int,
    channel: discord.TextChannel,
    prize: str,
    ends_at: int,
    special_msg: str | None,
):
    guild = channel.guild
    # Upsert giveaway to database and get giveaway ID
    try:
        giveaway_id = await upsert_giveaway(
            bot=bot,
            message_id=0,
            host_id=host.id,
            host_name=host.name,
            giveaway_type=giveaway_type,
            prize=prize,
            max_winners=winners,
            ends_at=ends_at,
            channel_id=channel.id,
        )
    except Exception as e:
        pretty_log("error", f"Error upserting giveaway to database: {e}")
        return False, f"{e}"

    # Build giveaway embed and view
    try:
        ga_embed, content = build_ga_embed(
            host=host,
            giveaway_type=giveaway_type,
            prize=prize,
            ends_at=ends_at,
            winners=winners,
            message=special_msg,
        )
        view = GiveawayButtonsView(
            bot=bot,
            giveaway_type=giveaway_type,
            giveaway_id=giveaway_id,
            guild=guild,
        )
        ga_msg = await channel.send(embed=ga_embed, view=view)
        view.message_id = ga_msg.id
        await channel.send(content)
        await update_giveaway_message_id(bot, giveaway_id, ga_msg.id)

        # Make thread
        thread = await ga_msg.create_thread(
            name=f"🎁 | ID: {giveaway_id}", auto_archive_duration=4320
        )
        thread_id = thread.id
        await update_giveaway_thread_id(
            bot=bot, giveaway_id=giveaway_id, thread_id=thread_id
        )

        return True, None

    except Exception as e:
        pretty_log("error", f"Error building giveaway embed and view: {e}")
        return False, f"{e}"
