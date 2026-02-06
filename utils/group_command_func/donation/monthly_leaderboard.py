from datetime import datetime

import discord
from discord.ext import commands
from discord.ui import Button, View

from Constants.aesthetic import *
from Constants.vn_allstars_constants import DEFAULT_EMBED_COLOR, VNA_SERVER_ID
from utils.db.donations_db import fetch_all_donation_records
from utils.essentials.role_checks import *
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log
from utils.visuals.pretty_defer import pretty_defer

from .overall_leaderboard import Donation_Leaderboard_Paginator
from .update_leaderboard import get_current_month_year


async def view_monthly_donation_leaderboard_func(bot, interaction: discord.Interaction):

    guild = interaction.guild
    user = interaction.user

    # Initialize loader
    loader = await pretty_defer(
        interaction=interaction, content="Fetching leaderboard data...", ephemeral=False
    )
    donation_records = await fetch_all_donation_records(bot)
    if not donation_records:
        await loader.error(content="No donation records found.")
        return

    current_month, current_year = get_current_month_year()
    title = f"🏆 Monthly Donations Leaderboard ({current_month} {current_year}) 🏆"
    sorted_records = sorted(
        donation_records, key=lambda x: x["monthly_donations"], reverse=True
    )
    try:
        paginator = Donation_Leaderboard_Paginator(
            bot=bot,
            user=user,
            title=title,
            donation_records=sorted_records,
            per_page=25,
        )
        embed = await paginator.get_embed()
        sent_msg = await loader.success(
            content="",
            embed=embed,
            view=paginator,
        )
        paginator.message = sent_msg
    except Exception as e:
        await loader.error(
            content="An error occurred while generating the leaderboard."
        )
        pretty_log(
            message=f"❌ Error in view_overall_leaderboard: {e}",
            tag="error",
            include_trace=True,
        )
