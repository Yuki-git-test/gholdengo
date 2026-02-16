import discord

from Constants.vn_allstars_constants import (
    KHY_USER_ID,
    VN_ALLSTARS_EMOJIS,
    VN_ALLSTARS_ROLES,
    VN_ALLSTARS_TEXT_CHANNELS,
    YUKI_USER_ID,
)
from utils.cache.cache_list import processing_end_giveaway_message_ids
from utils.db.ga_db import (
    delete_giveaways_which_ended_a_week_ago,
    fetch_all_due_giveaways,
)
from utils.giveaway.giveaway_end_func import end_giveaway_handler
from utils.logs.pretty_log import pretty_log


async def giveaway_end_checker(bot: discord.Client):
    """Checks for giveaways that have ended and processes them, and deletes giveaways that ended over a week ago."""
    await delete_giveaways_which_ended_a_week_ago(bot)
    due_giveaways = await fetch_all_due_giveaways(bot)
    if not due_giveaways:
        return

    for giveaway in due_giveaways:
        message_id = giveaway["message_id"]
        if message_id in processing_end_giveaway_message_ids:
            continue  # Skip if already being processed

        processing_end_giveaway_message_ids.add(message_id)
        try:
            await end_giveaway_handler(bot, message_id)
            processing_end_giveaway_message_ids.remove(message_id)
        except Exception as e:
            processing_end_giveaway_message_ids.remove(message_id)
            pretty_log(
                "error",
                f"Error processing giveaway end for message ID {message_id}: {e}",
            )
            continue  # Continue processing other giveaways even if one fails
