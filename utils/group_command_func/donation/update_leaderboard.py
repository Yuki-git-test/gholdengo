from datetime import datetime

import discord
from discord.ext import commands

from Constants.aesthetic import *
from Constants.donation_config import DONATION_MILESTONE_MAP, MONTHLY_DONATION_VALUE
from Constants.vn_allstars_constants import (
    DEFAULT_EMBED_COLOR,
    KHY_USER_ID,
    VN_ALLSTARS_EMOJIS,
    VN_ALLSTARS_ROLES,
    VN_ALLSTARS_TEXT_CHANNELS,
    YUKI_USER_ID,
)
from utils.db.donations_db import (
    fetch_all_donation_records,
    fetch_donation_record,
    increment_monthly_donator_streak,
    update_monthly_donations,
    update_monthly_donator_status,
    update_total_donations,
    upsert_donation_record,
)
from utils.db.leaderboard_info_db import (
    delete_leaderboard_msg_id,
    fetch_leaderboard_msg_id,
    upsert_leaderboard_msg_id,
)
from utils.essentials.format import format_comma_pokecoins
from utils.essentials.role_checks import *
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log
from utils.logs.server_log import send_log_to_server_log
from utils.visuals.design_embed import design_embed
from utils.visuals.pretty_defer import pretty_defer

MONTH_MAP = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}


def get_current_month_year():
    now = datetime.now()
    month = MONTH_MAP.get(now.month, "Unknown").title()
    return month, now.year


def get_last_month_year():
    now = datetime.now()
    if now.month == 1:
        last_month = 12
        year = now.year - 1
    else:
        last_month = now.month - 1
        year = now.year
    month = MONTH_MAP.get(last_month, "Unknown").title()
    return month, year


async def create_leaderboard_embed(
    bot, guild: discord.Guild, context: str, user: discord.Member = None
):
    """Create the trophy leaderboard embed."""
    # Fetch all donation records
    donation_records = await fetch_all_donation_records(bot)
    description = ""
    # Sort records by context (total or monthly donations) highest first
    if context == "total":
        sorted_records = sorted(
            donation_records, key=lambda x: x["total_donations"], reverse=True
        )
        title = "🏆 Overall Donation Leaderboard"
    elif context == "monthly":
        sorted_records = sorted(
            donation_records, key=lambda x: x["monthly_donations"], reverse=True
        )
        month, year = get_current_month_year()
        title = f"🏆 Monthly Donation Leaderboard ({month} {year})"
    else:
        pretty_log(
            message=f"❌ Invalid leaderboard context: {context}",
            tag="error",
        )
        return None
    # Create the embed
    embed = discord.Embed(title=title, color=DEFAULT_EMBED_COLOR, timestamp=datetime.now())
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    total_donators = len(donation_records)
    embed.set_footer(
        text=f"Total Donators: {total_donators}",
        icon_url=guild.icon.url if guild.icon else None,
    )
    for index, donation_info in enumerate(sorted_records[:10], start=1):
        user_id = donation_info["user_id"]
        member = guild.get_member(user_id)
        total_donations = donation_info.get("total_donations", 0)
        monthly_donations = donation_info.get("monthly_donations", 0)
        if context == "total":
            display_amount = format_comma_pokecoins(total_donations)
        else:
            display_amount = format_comma_pokecoins(monthly_donations)

        if member is None:
            try:
                member = await bot.fetch_user(user_id)
            except Exception:
                member = None
                continue

        if member:
            prefix = f"{index}. "
            if index == 1:
                prefix = f"🥇 {index}. "
            elif index == 2:
                prefix = f"🥈 {index}. "
            elif index == 3:
                prefix = f"🥉 {index}. "
            else:
                prefix = f"{index}. "
            user_name_str = f"{prefix}{member.display_name}"
            field_value = f"> - **{display_amount}**"
            embed.add_field(name=user_name_str, value=field_value, inline=False)
        if user:
            # Fetch donation record for the specified user
            user_donation = await fetch_donation_record(bot, user.id)
            if not user_donation:
                description = "You have not made any donations yet."
            else:
                user_donations = (
                    user_donation.get("total_donations", 0)
                    if context == "total"
                    else user_donation.get("monthly_donations", 0)
                )
                # Get user's position in the leaderboard
                user_position = next(
                    (
                        idx + 1
                        for idx, record in enumerate(sorted_records)
                        if record["user_id"] == user.id
                    ),
                    None,
                )
                if user_position:
                    description = f"You are currently ranked **#{user_position}** with **{format_comma_pokecoins(user_donations)}** in donations."

        embed.description = description

    note = """If you want to enable any of the perks available in <#910166647917117440> . Donate to `@beaterxyz` or `@yki.on` in **this channel only**
-# - Don't do any troll donations
-# - Minimum donation value is 500k
-# - Don't ping to ask for perks will be automatically given when seen by mods
-# - We dont really require `;clan donations`
"""
    embed.add_field(name="Notes:", value=note, inline=False)
    embed.set_footer(
        text="Updated on",
        icon_url=guild.icon.url if guild.icon else None,
    )
    return embed


async def update_leaderboard_func(
    bot,
    guild: discord.Guild,
):
    """Update the trophy leaderboard message in the specified channel."""
    leaderboard_channel = guild.get_channel(VN_ALLSTARS_TEXT_CHANNELS.clan_donations)
    # Fetch the trophy leaderboard msg id
    leaderboard_msg_id = await fetch_leaderboard_msg_id(bot, leaderboard_channel)
    # Get Message object for the leaderboard message
    leaderboard_message = None
    is_there_leadboard_message = False
    if leaderboard_msg_id:
        try:
            leaderboard_message = await leaderboard_channel.fetch_message(
                leaderboard_msg_id
            )
            leaderboard_embed = await create_leaderboard_embed(
                bot, guild, context="total"
            )
            await leaderboard_message.edit(embed=leaderboard_embed)
            is_there_leadboard_message = True
            pretty_log(
                tag="success",
                message="Updated trophy leaderboard message.",
                label="Trophy Leaderboard Update",
            )
        except discord.NotFound:
            pretty_log(
                tag="error",
                message="Leaderboard message not found. Creating a new one.",
                label="Trophy Leaderboard Update",
            )
            is_there_leadboard_message = False
    else:
        # No existing leaderboard message ID found, will create a new one
        is_there_leadboard_message = False

    if not is_there_leadboard_message:
        leaderboard_embed = await create_leaderboard_embed(bot, guild, context="total")
        leaderboard_message = await leaderboard_channel.send(embed=leaderboard_embed)
        await upsert_leaderboard_msg_id(
            bot, leaderboard_message.id, leaderboard_channel
        )
        pretty_log(
            tag="success",
            message="Created new trophy leaderboard message.",
            label="Trophy Leaderboard Update",
        )
