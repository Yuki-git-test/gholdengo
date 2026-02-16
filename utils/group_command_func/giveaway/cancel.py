import time

import discord
from discord.ext import commands
from discord.ui import Button, Modal, TextInput, View

from Constants.aesthetic import *
from Constants.giveaway import BLACKLISTED_ROLES, Extra_Entries
from Constants.vn_allstars_constants import (
    KHY_USER_ID,
    VN_ALLSTARS_EMOJIS,
    VN_ALLSTARS_ROLES,
    VN_ALLSTARS_TEXT_CHANNELS,
    YUKI_USER_ID,
)
from utils.db.ga_db import (
    delete_giveaway,
    fetch_giveaway_id_by_message_id,
    fetch_giveaway_row_by_message_id,
    update_giveaway_message_id,
    update_giveaway_thread_id,
    upsert_giveaway,
)
from utils.db.ga_entry_db import (
    delete_ga_entry,
    fetch_entries_by_giveaway,
    fetch_ga_entry,
    upsert_ga_entry,
)
from utils.essentials.role_checks import *
from utils.giveaway.giveaway_end_func import end_giveaway_handler
from utils.giveaway.giveaway_funcs import (
    build_ga_embed,
    can_host_ga,
    compute_total_entries,
)
from utils.giveaway.views import GiveawayButtonsView
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log
from utils.logs.server_log import send_log_to_server_log
from utils.parsers.duration import parse_total_duration
from utils.visuals.colors import get_random_ghouldengo_color
from utils.visuals.design_embed import design_embed
from utils.visuals.pretty_defer import pretty_defer
from utils.visuals.thumbnails import random_ga_thumbnail_url


async def cancel_giveaway_func(
    bot: discord.Client, interaction: discord.Interaction, message_id: int
):
    message_id = int(message_id)  # Convert message_id to int
    # Defer response early since this can take a while
    loader = await pretty_defer(
        interaction=interaction, content="Canceling giveaway...", ephemeral=True
    )
    # Check if staff
    if not is_staff_member(interaction.user):
        await loader.error(content="You do not have permission to cancel giveaways.")
        return

    giveaway_row = await fetch_giveaway_row_by_message_id(bot, message_id)

    if not giveaway_row:
        pretty_log(
            "error",
            f"No giveaway found for message ID {message_id}",
        )
        await loader.error(
            content="No giveaway found for this message.",
        )
        return

    giveaway_id = giveaway_row["giveaway_id"]
    channel_id = giveaway_row["channel_id"]
    thread_id = giveaway_row["thread_id"]

    # Delete giveaway from DB
    try:
        await delete_giveaway(bot, giveaway_id)
        pretty_log(
            "info",
            f"Deleted giveaway with ID {giveaway_id} from database",
            label="Giveaway Cancel Handler",
        )
    except Exception as e:
        pretty_log(
            "error",
            f"Error deleting giveaway with ID {giveaway_id} from database: {e}",
            label="Giveaway Cancel Handler",
            include_trace=True,
        )
        await loader.error(content="An error occurred while canceling the giveaway.")
        return

    # Delete giveaway message and thread
    try:
        channel = bot.get_channel(channel_id)
        if channel:
            message = await channel.fetch_message(message_id)
            if message:
                await message.delete()
                # Delete the next message if it exists and is from the bot (to clean up error/success messages)
                try:
                    async for next_message in channel.history(
                        after=message, limit=1, oldest_first=True
                    ):
                        if next_message.author.id == bot.user.id:
                            await next_message.delete()
                except Exception:
                    pass  # Ignore if no next message or can't delete

        if thread_id:
            thread = bot.get_channel(thread_id)
            if thread:
                await thread.delete()
        await loader.success(content="Giveaway canceled and message/thread deleted.")
    except Exception as e:
        pretty_log(
            "error",
            f"Error deleting giveaway message or thread for giveaway ID {giveaway_id}: {e}",
            label="Giveaway Cancel Handler",
            include_trace=True,
        )
