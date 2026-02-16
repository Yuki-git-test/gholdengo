import discord

from utils.db.ga_db import fetch_all_giveaways
from utils.giveaway.views import GiveawayButtonsView
from utils.logs.pretty_log import pretty_log
from Constants.vn_allstars_constants import VNA_SERVER_ID

async def restore_giveaway_views(bot: discord.Client):
    pretty_log("info", "Restoring giveaway views...")
    giveaways = await fetch_all_giveaways(bot)
    restored_count = []
    for giveaway in giveaways:
        db_message_id = giveaway["message_id"]
        channel_id = giveaway["channel_id"]
        thread_id = giveaway["thread_id"]
        giveaway_id = giveaway["giveaway_id"]
        giveaway_type = giveaway["giveaway_type"]

        try:
            channel = bot.get_channel(channel_id)
            guild = bot.get_guild(VNA_SERVER_ID)
            if not channel:
                pretty_log(
                    "error",
                    f"Could not find channel with ID {channel_id} for giveaway {giveaway['giveaway_id']}",
                )
                continue
            message = await channel.fetch_message(db_message_id)
            if not message:
                pretty_log(
                    "error",
                    f"Could not find message with ID {db_message_id} in channel {channel_id} for giveaway {giveaway['giveaway_id']}",
                )
                continue
            view = GiveawayButtonsView(
                bot=bot,
                giveaway_id=giveaway_id,
                giveaway_type=giveaway_type,
                guild=guild,
                message_id=db_message_id,
            )
            # ✅ Register view with the correct message ID
            bot.add_view(view, message_id=db_message_id)
            restored_count.append(giveaway_id)
            pretty_log(
                "info",
                f"Restored view for giveaway {giveaway['giveaway_id']} (message ID {db_message_id})",
            )
        except Exception as e:
            pretty_log(
                "error",
                f"Error restoring view for giveaway {giveaway['giveaway_id']} (message ID {db_message_id}): {e}",
            )
    pretty_log(
        "info",
        f"Finished restoring giveaway views. Successfully restored {len(restored_count)}/{len(giveaways)} giveaways.",
    )
