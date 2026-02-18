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
from utils.visuals.pretty_defer import pretty_defer

SNIPE_COOLDOWNS = {}
COOLDOWN_SECONDS = 30
SNIPE_GA_DURATION_SECONDS = 30


def check_and_set_cooldown(user_id: int) -> int:
    """
    Returns seconds remaining if on cooldown, or 0 if not.
    Sets the cooldown if not on cooldown.
    """
    now = time.time()
    last_used = SNIPE_COOLDOWNS.get(user_id, 0)
    if now - last_used < COOLDOWN_SECONDS:
        return int(COOLDOWN_SECONDS - (now - last_used))
    SNIPE_COOLDOWNS[user_id] = now
    return 0


def reset_cooldown(user_id: int):
    """Remove the user's cooldown so they can use the command again immediately."""
    if user_id in SNIPE_COOLDOWNS:
        del SNIPE_COOLDOWNS[user_id]


async def snipe_ga_func(
    bot: commands.Bot,
    interaction: discord.Interaction,
    prize: str,
    duration: int,
    winners: int = 1,
):
    """Starts a quick snipe giveaway."""

    # Check if user has required roles to use the command
    user_roles = [role.id for role in interaction.user.roles]
    if not any(role in user_roles for role in REQUIRED_ROLES):
        required_roles_mentions = ", ".join(
            f"<@&{role_id}>" for role_id in REQUIRED_ROLES
        )
        await interaction.response.send_message(
            f"You do not have permission to use this command. Only members with the following roles can use it: {required_roles_mentions}",
            ephemeral=True,
        )
        return

    # Check if there is an active snipe giveaway
    if globals.snipe_ga_active:
        await interaction.response.send_message(
            "There is already an active snipe giveaway. Please wait for it to finish before starting a new one.",
            ephemeral=True,
        )
        return

    # Duration must be more than or equal to 15 seconds but less than or equal to 1 minute
    if duration < 15 or duration > 60:
        await interaction.response.send_message(
            "Please specify a duration between 15 and 60 seconds.",
            ephemeral=True,
        )
        return

    # Set the snipe giveaway as active
    globals.snipe_ga_active = True

    # Initialize loader
    loader = await pretty_defer(
        interaction=interaction,
        content="Starting snipe giveaway...",
        ephemeral=True,
    )
    ends_at = datetime.now() + timedelta(seconds=duration)
    content = f"SNIPE <@&{VN_ALLSTARS_ROLES.giveaways}>!"
    snipe_ga_embed = build_snipe_ga_embed(
        host=interaction.user,
        prize=prize,
        ends_at=ends_at,
    )
    view = SnipeGAView(
        bot=bot,
        prize=prize,
        author=interaction.user,
        embed_color=DEFAULT_EMBED_COLOR,
        timeout=duration,
        winners_count=winners,
    )
    await loader.success(content="Snipe giveaway started!", delete=True)
    try:
        ga_msg = await interaction.channel.send(
            content=content,
            embed=snipe_ga_embed,
            view=view,
        )
        view.message = ga_msg
        await view.wait()
        await view.end_giveaway()
        globals.snipe_ga_active = False
    except Exception as e:
        globals.snipe_ga_active = False
        await loader.error(
            content="An error occurred while starting the snipe giveaway.",
        )
        pretty_log("error", f"SnipeGA command error: {e}")
