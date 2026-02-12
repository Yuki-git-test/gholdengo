import asyncio
import random
import time
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks

import utils.cache.global_variables as globals
from Constants.giveaway import REQUIRED_ROLES
from Constants.vn_allstars_constants import DEFAULT_EMBED_COLOR, VN_ALLSTARS_ROLES
from utils.functions.snipe_ga_func import SnipeGAView, build_snipe_ga_embed
from utils.logs.pretty_log import pretty_log
from utils.parsers.duration import parse_total_seconds
from utils.visuals.pretty_defer import pretty_defer


async def create_snipe_ga_prefix(bot, message: discord.Message):

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

    question_one = "Which channel should the giveaway be hosted in? Please mention the channel or provide the channel ID."
    cancel_str = "To cancel the giveaway creation process, type 'cancel' at any time."
    description = f"{question_one}\n\n{cancel_str}"
    embed = discord.Embed(
        title="Snipe Giveaway",
        description=description,
        color=DEFAULT_EMBED_COLOR,
    )
    embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)

    def check(m):
        return m.author == user and m.channel == message.channel

    try:
        await message.reply(embed=embed)
        channel_response = await bot.wait_for("message", check=check, timeout=120)
        if channel_response.content.lower() == "cancel":
            await message.channel.send("Giveaway creation cancelled.")
            return

        # Extract channel ID from mention or use as is
        if channel_response.content.startswith(
            "<#"
        ) and channel_response.content.endswith(">"):
            channel_id = int(channel_response.content[2:-1])
        else:
            channel_id = int(channel_response.content)
        giveaway_channel = bot.get_channel(channel_id)
        if giveaway_channel is None:
            await message.channel.send("Invalid channel. Giveaway creation cancelled.")
            return

        # Ask for duration
        duration_question = "How long should the giveaway last? Please provide the duration (e.g. 1d, 2h, 30m)."
        description = f"{duration_question}\n\nType `cancel` to stop this process."
        duration_question_embed = embed.copy()
        duration_question_embed.description = description
        await message.reply(embed=duration_question_embed)
        duration_response = await bot.wait_for("message", check=check, timeout=120)
        if duration_response.content.lower() == "cancel":
            await message.channel.send("Giveaway creation cancelled.")
            return
        try:
            duration_seconds = parse_total_seconds(duration_response.content)
            if duration_seconds <= 0:
                raise ValueError
        except ValueError:
            await message.channel.send(
                "Invalid duration format. Please enter a valid duration (e.g. '5m', '2h'). Giveaway creation cancelled."
            )
            return

        # Ask for number of winners
        winners_question = "How many winners should there be for this giveaway? (Type a number, e.g. 1)"
        description = f"{winners_question}\n\nType `cancel` to stop this process."
        winners_question_embed = embed.copy()
        winners_question_embed.description = description
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
        await message.reply(embed=prize_question_embed)
        prize_response = await bot.wait_for("message", check=check, timeout=120)
        if prize_response.content.lower() == "cancel":
            await message.channel.send("Giveaway creation cancelled.")
            return
        prize = prize_response.content

        # Final confirmation embed
        confirm_embed = discord.Embed(
            title="Snipe Giveaway Created!",
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
