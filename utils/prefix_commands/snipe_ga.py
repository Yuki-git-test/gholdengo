import asyncio
import random
import time
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks

import utils.cache.global_variables as globals
from Constants.giveaway import REQUIRED_ROLES
from Constants.vn_allstars_constants import DEFAULT_EMBED_COLOR, VN_ALLSTARS_ROLES, VN_ALLSTARS_TEXT_CHANNELS
from utils.functions.snipe_ga_func import SnipeGAView, build_snipe_ga_embed
from utils.logs.pretty_log import pretty_log
from utils.parsers.duration import parse_total_seconds
from utils.visuals.pretty_defer import pretty_defer


async def create_snipe_ga_prefix(bot: discord.Client, message: discord.Message):

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
    cancel_str = "To cancel the snipe giveaway creation process, type 'cancel' at any time."
    description = f"{question_one}\n\n{cancel_str}"
    embed = discord.Embed(
        title="Enter Snipe Giveaway Type",
        description=description,
        color=DEFAULT_EMBED_COLOR,
    )
    embed.set_author(name="Snipe Giveaway", icon_url=bot.user.display_avatar.url)

    def check(m):
        return m.author == user and m.channel == message.channel

    try:
        await message.reply(embed=embed)
        giveaway_type = await bot.wait_for("message", check=check, timeout=120)
        if giveaway_type not in ["clan", "general"]:
            await message.channel.send(
                "Invalid giveaway type. Please respond with either `clan` or `general`. Snipe Giveaway creation cancelled."
            )
            return
        if giveaway_type.content.lower() == "cancel":
            await message.channel.send("Snipe Giveaway creation cancelled.")
            return
        giveaway_type = giveaway_type.content.strip().lower()
        # Extract channel ID from mention or use as is
        if giveaway_type  == "clan":
            channel_id = VN_ALLSTARS_TEXT_CHANNELS.clan_giveaway
        else:
            channel_id = VN_ALLSTARS_TEXT_CHANNELS.giveaway
        giveaway_channel = bot.get_channel(channel_id)
        if giveaway_channel is None:
            await message.channel.send("Invalid channel. Snipe Giveaway creation cancelled.")
            return

        # Ask for duration
        duration_question = "How long should the giveaway last? Please provide the duration (e.g. `30s`).\n\n**Note:** For Snipe Giveaways, the duration must be between 15 and 60 seconds."
        description = f"{duration_question}\n\n{cancel_str}"
        duration_question_embed = embed.copy()

        duration_question_embed.description = description
        duration_title = "Enter Snipe Giveaway Duration"
        duration_question_embed.title = duration_title
        await message.reply(embed=duration_question_embed)
        duration_response = await bot.wait_for("message", check=check, timeout=120)
        if duration_response.content.lower() == "cancel":
            await message.channel.send("Snipe Giveaway creation cancelled.")
            return
        try:
            duration_seconds = parse_total_seconds(duration_response.content)
            if duration_seconds <= 0:
                raise ValueError
            # Duration must be 60 seconds or less for snipe giveaways but at least 15 seconds
            if duration_seconds < 15 or duration_seconds > 60:
                await message.channel.send(
                    "Please specify a duration between 15 and 60 seconds for Snipe GA. Snipe Giveaway creation cancelled."
                )
                return
        except ValueError:
            await message.channel.send(
                "Invalid duration format. Please enter a valid duration (e.g. `15s`, '5m'). Snipe Giveaway creation cancelled."
            )
            return

        # Ask for number of winners
        winners_question = "How many winners should there be for this giveaway? (Type a number, e.g. 1)"
        description = f"{winners_question}\n\n{cancel_str}"
        winners_question_embed = embed.copy()
        winners_question_embed.description = description
        winners_question_embed.title = "Enter Number of Winners"
        await message.reply(embed=winners_question_embed)
        winners_response = await bot.wait_for("message", check=check, timeout=120)
        if winners_response.content.lower() == "cancel":
            await message.channel.send("Snipe Giveaway creation cancelled.")
            return
        try:
            winners = int(winners_response.content)
            if winners < 1 or winners > 25:
                raise ValueError
        except ValueError:
            await message.channel.send(
                "Invalid number of winners. Please enter a number between 1 and 25. Snipe Giveaway creation cancelled."
            )
            return

        # Ask for prize
        prize_question = (
            f"There will be {winners} winner(s). What do you want to giveaway?"
        )
        description = f"{prize_question}\n\n{cancel_str}"
        prize_question_embed = embed.copy()
        prize_question_embed.description = description
        prize_question_embed.title = "Enter Snipe Giveaway Prize"
        await message.reply(embed=prize_question_embed)
        prize_response = await bot.wait_for("message", check=check, timeout=120)
        if prize_response.content.lower() == "cancel":
            await message.channel.send("Snipe Giveaway creation cancelled.")
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

        ends_at = datetime.now() + timedelta(seconds=duration_seconds)
        content = f"SNIPE <@&{VN_ALLSTARS_ROLES.giveaways}>!"
        snipe_ga_embed = build_snipe_ga_embed(
            giveaway_type=giveaway_type,
            host=message.author,
            prize=prize,
            ends_at=ends_at,
        )
        view = SnipeGAView(
            bot=bot,
            prize=prize,
            giveaway_type=giveaway_type,
            author=message.author,
            embed_color=DEFAULT_EMBED_COLOR,
            timeout=duration_seconds,
            winners_count=winners,
        )
        ga_msg = await giveaway_channel.send(
            content=content,
            embed=snipe_ga_embed,
            view=view,
        )
        view.message = ga_msg
    except asyncio.TimeoutError:
        await message.channel.send("You took too long to reply. Giveaway cancelled.")
