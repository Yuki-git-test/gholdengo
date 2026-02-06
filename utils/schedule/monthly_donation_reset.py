from datetime import datetime

import discord

from Constants.vn_allstars_constants import (
    DEFAULT_EMBED_COLOR,
    VN_ALLSTARS_TEXT_CHANNELS,
)
from utils.db.donations_db import reset_monthly_donations, total_monthly_donations
from utils.essentials.format import format_comma_pokecoins
from utils.functions.webhook_func import send_webhook
from utils.group_command_func.donation.update_leaderboard import (

    get_last_month_year,
)
from utils.logs.pretty_log import pretty_log


async def reset_monthly_donation_sched(bot):
    """Reset monthly donations for all users and log the total reset amount."""
    total_reset_amount = await total_monthly_donations(bot)
    total_monthly_donations_formatted = format_comma_pokecoins(total_reset_amount)
    await reset_monthly_donations(bot)
    pretty_log(
        tag="schedule",
        message=f"Monthly donations reset. Total reset amount: {total_monthly_donations_formatted} Pokécoins.",
        bot=bot,
    )
    # Log to Discord channel via webhook
    month, year = get_last_month_year()
    title = f"📅 Total Monthly Donation for {month} {year}"
    embed = discord.Embed(
        title=title,
        description=(
            f"- Total monthly donations: **{total_monthly_donations_formatted}**\n\n"
            f"Monthly donations have been reset for all users."
        ),
        color=DEFAULT_EMBED_COLOR,
        timestamp=datetime.now(),
    )
    log_channel = bot.get_channel(VN_ALLSTARS_TEXT_CHANNELS.server_log)
    if log_channel:
        await send_webhook(bot, log_channel, embed=embed)
