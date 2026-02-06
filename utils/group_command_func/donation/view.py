from datetime import datetime

import discord
from discord.ext import commands

from Constants.aesthetic import *
from Constants.vn_allstars_constants import DEFAULT_EMBED_COLOR
from utils.db.donations_db import fetch_donation_record
from utils.essentials.format import format_comma_pokecoins
from utils.essentials.role_checks import *
from utils.visuals.design_embed import design_embed
from utils.visuals.pretty_defer import pretty_defer


async def view_donation_func(
    bot: commands.Bot,
    interaction: discord.Interaction,
    member: discord.Member = None,
):
    """View donation stats of a member."""
    if member is None:
        member = interaction.user
        user_str = "You"
    else:
        user_str = f"{member.display_name}"

    # Defer the interaction to allow more time for processing
    loader = await pretty_defer(
        interaction, content="Fetching donation data...", ephemeral=False
    )

    donation_info = await fetch_donation_record(bot, member.id)
    if not donation_info:
        await loader.error(content=f"{user_str} have no donation records yet.")
        return

    total_donated = donation_info.get("total_donations", 0)
    monthly_donated = donation_info.get("monthly_donations", 0)
    monthly_donator_streak = donation_info.get("monthly_donator_streak", 0)
    permanent_donator = donation_info.get("permanent_monthly_donator", False)
    monthly_donator = donation_info.get("monthly_donator", False)

    desc = (
        f"**Member:** {member.mention}\n"
        f"**Total Donations:** {format_comma_pokecoins(total_donated)}\n"
        f"**Monthly Donations:** {format_comma_pokecoins(monthly_donated)}\n"
        f"**Monthly Donator Streak:** {monthly_donator_streak} months\n"
        f"**Permanent Monthly Donator:** {'Yes' if permanent_donator else 'No'}\n"
        f"**Current Monthly Donator:** {'Yes' if monthly_donator else 'No'}\n"
    )
    embed = discord.Embed(
        title=f"Donation Stats for {member.display_name}",
        color=DEFAULT_EMBED_COLOR,
        description=desc,
        timestamp=datetime.now(),
    )
    embed = design_embed(embed=embed, user=member)
    await loader.success(embed=embed, content="")
