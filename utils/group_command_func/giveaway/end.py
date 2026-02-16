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


async def end_giveaway_func(
    bot: discord.Client, interaction: discord.Interaction, message_id: str
):
    message_id = int(message_id)  # Convert message_id to int
    # Defer response early since this can take a while
    loader = await pretty_defer(
        interaction=interaction, content="Ending giveaway...", ephemeral=True
    )
    # Check if staff
    if not is_staff_member(interaction.user):
        await loader.error(content="You do not have permission to end giveaways.")
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

    # End giveaway and pick winners
    try:
        winners = await end_giveaway_handler(bot, message_id)
        if winners:
            await loader.success(content="Giveaway ended! Winners have been picked.")
        else:
            await loader.error(
                content="No entries found or giveaway not found for message."
            )
    except Exception as e:
        pretty_log(
            "error",
            f"Error ending giveaway for message ID {message_id}: {e}",
            include_trace=True,
        )
        await loader.error(content="An error occurred while ending the giveaway.")
        return
