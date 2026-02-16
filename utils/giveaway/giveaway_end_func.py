import random
import re
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
    mark_giveaway_as_ended,
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


async def pick_winners(
    bot: discord.Client, giveaway_id: int, entries, max_winners: int
):
    weighted_entries: list[int] = []
    entry_map: dict[int, dict] = {}

    for entry in entries:
        uid = entry["user_id"]
        count = entry["entry_count"]
        entry_map[uid] = dict(entry)
        weighted_entries.extend([uid] * count)

    # Pick winners
    winners: list[dict] = []
    chosen_ids = set()
    distinct_users = set(weighted_entries)

    while len(winners) < max_winners and len(chosen_ids) < len(distinct_users):
        winner_id = random.choice(weighted_entries)

        if winner_id in chosen_ids:
            weighted_entries = [uid for uid in weighted_entries if uid != winner_id]

        # Valid winner
        chosen_ids.add(winner_id)
        winner_entry = entry_map[winner_id]

        # Get user mention
        winner_entry["mention"] = f"<@{winner_id}>"
        winners.append(winner_entry)

        # Remove entry from db and local pool
        await delete_ga_entry(bot, giveaway_id, winner_id)
        weighted_entries = [uid for uid in weighted_entries if uid != winner_id]

    return winners


async def finalize_giveaway(
    *,
    message: discord.Message,
    channel: discord.TextChannel,
    giveaway_id: int,
    host_id: int | None,
    thread_id: int | None,
    winners,
    prize: str,
    color: discord.Color = discord.Color.blurple(),
    log_label: str = "🎉 GIVEAWAY",
):
    """
    Updates the giveaway message embed, sends announcement,
    archives/locks the thread, and logs the result.
    """

    # ✅ Update original giveaway embed
    embed = message.embeds[0] if message.embeds else discord.Embed()
    embed.title = (embed.title or "Giveaway") + " — Ended"

    if embed.description:
        embed.description = re.sub(
            r"⏰ \*\*Ends:\*\* <t:\d+:R>",
            "⏰ **Ended**",
            embed.description,
        )

    if winners is None:
        winners = []
    winners_value = (
        winners[0]["mention"]
        if len(winners) == 1
        else (
            "\n".join(w["mention"] for w in winners) if winners else "No one entered 😢"
        )
    )
    embed.add_field(name="🎁 Winners", value=winners_value, inline=False)
    await message.edit(embed=embed)

    # ✅ Build announcement embed
    desc = (
        "Congratulations to the winners!"
        if winners
        else "Unfortunately, no one entered this giveaway. 😢"
    )
    announcement_embed = discord.Embed(
        title="🎉 Giveaway Ended!",
        description=desc,
        color=color,
    )
    announcement_embed.add_field(
        name="🎁 Prize", value=prize if prize else "N/A", inline=False
    )
    announcement_embed.add_field(name="👑 Winners", value=winners_value, inline=False)

    thumbnail_url = random_ga_thumbnail_url()
    if thumbnail_url:
        announcement_embed.set_thumbnail(url=thumbnail_url)

    # ✅ Build custom content message
    content = None
    host = message.guild.get_member(host_id) if host_id else None

    if winners and host:
        winner_mentions = ", ".join(w["mention"] for w in winners if "mention" in w)
        if len(winners) == 1:
            content = f"🎉 Congratulations {winner_mentions} for winning {host.mention}'s giveaway!"
        else:
            content = f"🎉 Congratulations {winner_mentions} for winning {host.mention}'s giveaway!"
    elif winners:
        winner_mentions = ", ".join(w["mention"] for w in winners if "mention" in w)
        if len(winners) == 1:
            content = f"🎉 Congratulations {winner_mentions} for winning the giveaway!"
        else:
            content = f"🎉 Congratulations {winner_mentions} for winning the giveaway!"
    elif host:
        content = f"{host.mention}, unfortunately no one entered your giveaway. 😢"

    # ✅ Send announcement
    await channel.send(
        content=content,
        embed=announcement_embed,
        reference=message,
        mention_author=False,
    )

    # ✅ Archive/lock thread
    if thread_id is not None:
        ga_thread = message.channel.get_thread(thread_id)
        if ga_thread:
            ga_thread_name = f"🔒 ID # {giveaway_id} | GA"
            if host:
                ga_thread_name = f"🔒 ID # {giveaway_id} | {host.name} GA"
            await ga_thread.edit(name=ga_thread_name, archived=True, locked=True)

    # ✅ Log result
    if winners:
        pretty_log(
            tag="info",
            message=f"Winners for giveaway {giveaway_id}: {winners_value}",
            label=log_label,
        )
    else:
        pretty_log(
            tag="info",
            message=f"No entries for giveaway {giveaway_id}.",
            label=log_label,
        )


async def end_giveaway_handler(
    bot: discord.Client,
    message_id: int,
    log_label: str = "🎉 GIVEAWAY",
):
    """Handles ending a giveaway, selecting winners, and updating the giveaway message."""
    giveaway_row = await fetch_giveaway_row_by_message_id(bot, message_id)
    if not giveaway_row:
        pretty_log(
            "error",
            f"No giveaway found for message ID {message_id}",
            label="Giveaway End Handler",
        )
        return None

    # Giveaway details
    giveaway_id = giveaway_row["giveaway_id"]
    channel_id = giveaway_row["channel_id"]
    host_id = giveaway_row["host_id"]
    prize = giveaway_row["prize"]
    max_winners = giveaway_row["max_winners"]
    thread_id = giveaway_row["thread_id"]

    # Fetch stuff
    channel = bot.get_channel(channel_id)
    if not channel:
        pretty_log(
            "error",
            f"Channel with ID {channel_id} not found for giveaway ID {giveaway_id}",
            label="Giveaway End Handler",
        )
        return
    try:
        message = await channel.fetch_message(message_id)
    except discord.NotFound:
        pretty_log(
            "error",
            f"Message with ID {message_id} not found in channel {channel_id} for giveaway ID {giveaway_id}",
            label="Giveaway End Handler",
        )
        return
    try:
        await message.edit(view=None)  # Disable buttons
    except Exception as e:
        pass

    # Fetch entries
    entries = await fetch_entries_by_giveaway(bot, giveaway_id)

    # Mark it as ended in the DB to prevent double processing
    await mark_giveaway_as_ended(bot, giveaway_id)

    # No entries case
    if not entries:
        pretty_log(
            "info",
            f"No entries found for giveaway ID {giveaway_id}",
            label="Giveaway End Handler",
        )
        winners = []
        await finalize_giveaway(
            message=message,
            channel=channel,
            giveaway_id=giveaway_id,
            host_id=host_id,
            thread_id=thread_id,
            winners=None,
            prize=prize,
            color=discord.Color.blurple(),
            log_label=log_label,
        )
        return None

    # Pick winners
    winners = await pick_winners(bot, giveaway_id, entries, max_winners)
    # 9 Finalize giveaway
    await finalize_giveaway(
        message=message,
        channel=channel,
        giveaway_id=giveaway_id,
        host_id=host_id,
        thread_id=thread_id,
        winners=winners,  # <-- keep dicts
        prize=prize,  # <-- also pass this in
        color=discord.Color.blurple(),
        log_label=log_label,
    )

    return winners


async def send_rerolled_results(
    *,
    message: discord.Message,
    channel: discord.TextChannel,
    giveaway_id: int,
    host_id: int | None,
    winners,
    prize: str,
    color: discord.Color = discord.Color.blurple(),
    log_label: str = "🎉 GIVEAWAY",
):
    """
    Updates the giveaway message embed, sends announcement,
    archives/locks the thread, and logs the result.
    """

    winners_value = (
        winners[0]["mention"]
        if len(winners) == 1
        else (
            "\n".join(w["mention"] for w in winners) if winners else "No one entered 😢"
        )
    )

    # ✅ Build announcement embed
    desc = (
        "Congratulations to the winners!"
        if winners
        else "Unfortunately, no one entered this giveaway. 😢"
    )
    announcement_embed = discord.Embed(
        title="🎉 Giveaway Rerolled!",
        description=desc,
        color=color,
    )
    announcement_embed.add_field(
        name="🎁 Prize", value=prize if prize else "N/A", inline=False
    )
    announcement_embed.add_field(name="👑 Winners", value=winners_value, inline=False)

    thumbnail_url = random_ga_thumbnail_url()
    if thumbnail_url:
        announcement_embed.set_thumbnail(url=thumbnail_url)

    # ✅ Build custom content message
    content = None
    host = message.guild.get_member(host_id) if host_id else None

    if winners and host:
        winner_mentions = ", ".join(w["mention"] for w in winners if "mention" in w)
        if len(winners) == 1:
            content = f"🎉 Congratulations {winner_mentions} for winning {host.mention}'s giveaway!"
        else:
            content = f"🎉 Congratulations {winner_mentions} for winning {host.mention}'s giveaway!"
    elif winners:
        winner_mentions = ", ".join(w["mention"] for w in winners if "mention" in w)
        if len(winners) == 1:
            content = f"🎉 Congratulations {winner_mentions} for winning the giveaway!"
        else:
            content = f"🎉 Congratulations {winner_mentions} for winning the giveaway!"
    elif host:
        content = f"{host.mention}, unfortunately no one entered your giveaway. 😢"

    # ✅ Send announcement
    await channel.send(
        content=content,
        embed=announcement_embed,
        reference=message,
        mention_author=False,
    )

    # ✅ Log result
    if winners:
        pretty_log(
            tag="info",
            message=f"Winners for giveaway {giveaway_id}: {winners_value}",
            label=log_label,
        )
    else:
        pretty_log(
            tag="info",
            message=f"No entries for giveaway {giveaway_id}.",
            label=log_label,
        )


async def reroll_giveaway_handler(
    bot: discord.Client,
    reroll_count: int,
    giveaway_row: dict,
    entries,
    log_label: str = "🎉 GIVEAWAY",
):
    """Handles rerolling a giveaway, selecting winners, and updating the giveaway message."""

    # Giveaway details
    giveaway_id = giveaway_row["giveaway_id"]
    channel_id = giveaway_row["channel_id"]
    host_id = giveaway_row["host_id"]
    prize = giveaway_row["prize"]

    # Fetch stuff
    channel = bot.get_channel(channel_id)
    if not channel:
        pretty_log(
            "error",
            f"Channel with ID {channel_id} not found for giveaway ID {giveaway_id}",
            label="Giveaway End Handler",
        )
        return False, f"Channel not found for giveaway."

    # Pick winners
    winners = await pick_winners(bot, giveaway_id, entries, reroll_count)

    # Finalize giveaway
    await send_rerolled_results(
        channel=channel,
        giveaway_id=giveaway_id,
        host_id=host_id,
        winners=winners,  # <-- keep dicts
        prize=prize,  # <-- also pass this in
        color=discord.Color.blurple(),
        log_label=log_label,
    )

    return True, None
