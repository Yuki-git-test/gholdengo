from datetime import datetime

import discord
from discord.ext import commands

from Constants.aesthetic import *
from Constants.donation_config import DONATION_MILESTONE_MAP
from Constants.vn_allstars_constants import (
    DEFAULT_EMBED_COLOR,
    KHY_USER_ID,
    VN_ALLSTARS_EMOJIS,
    VN_ALLSTARS_ROLES,
    VN_ALLSTARS_TEXT_CHANNELS,
    YUKI_USER_ID,
)
from utils.db.donations_db import (
    fetch_donation_record,
    increment_monthly_donator_streak,
    update_monthly_donations,
    update_monthly_donator_status,
    update_total_donations,
    upsert_donation_record,
)
from utils.essentials.format import format_comma_pokecoins
from utils.essentials.role_checks import *
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log
from utils.logs.server_log import send_log_to_server_log
from utils.visuals.design_embed import design_embed
from utils.visuals.pretty_defer import pretty_defer
from Constants.donation_config import MONTHLY_DONATION_VALUE
from utils.functions.webhook_func import send_webhook

async def check_monthly_and_update_donation_status(
    bot: commands.Bot,
    member: discord.Member,
):
    donation_record = await fetch_donation_record(bot, member.id)
    total_donations = donation_record.get("total_donations", 0)
    monthly_donations = donation_record.get("monthly_donations", 0)
    permanent_monthly_donator = donation_record.get("permanent_monthly_donator", False)
    monthly_donator_streak = donation_record.get("monthly_donator_streak", 0)
    monthly_donator = donation_record.get("monthly_donator", False)

    """Check if the user's monthly donations meet the threshold and update their monthly donator status accordingly."""
    embed = discord.Embed(
        title="🎉 Donation Milestone Update",
        timestamp=datetime.now(),
        color=DEFAULT_EMBED_COLOR,
    )
    log_embed = discord.Embed(
        title="📈 Donation Milestone Update",
        timestamp=datetime.now(),
        color=DEFAULT_EMBED_COLOR,
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    log_embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
    log_embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
    embed.set_footer(
        text="Thank you for your support! Don't forget to checkout the #perks channel for your new role benefits!",
        icon_url=member.guild.icon.url if member.guild.icon else None,
    )
    log_embed.set_footer(
        text=f"User ID: {member.id}",
        icon_url=member.guild.icon.url if member.guild.icon else None,
    )
    confirm_description = (
        f"**Member:** {member.mention}\n"
        f"**Monthly Donations:** {format_comma_pokecoins(monthly_donations)}\n"
        f"**Total Donations:** {format_comma_pokecoins(total_donations)}\n"
    )

    log_description = (
        f"**Member:** {member.mention}\n"
        f"**Monthly Donations:** {format_comma_pokecoins(monthly_donations)}\n"
        f"**Total Donations:** {format_comma_pokecoins(total_donations)}\n"
    )
    milestone_added = False
    if monthly_donations >= MONTHLY_DONATION_VALUE:
        if not permanent_monthly_donator and not monthly_donator:
            milestone_added = True
            await update_monthly_donator_status(bot, member.id, True)
            pretty_log(
                message=f"✅ Updated monthly donator status to True for user ID: {member.id} ({member.name})",
                tag="donation",
            )
            await increment_monthly_donator_streak(bot, member.id)
            monthly_donator_streak += 1

            pretty_log(
                message=f"✅ Incremented monthly donator streak for user ID: {member.id} to {monthly_donator_streak}",
                tag="donation",
            )
            monthly_donator_role = member.guild.get_role(
                VN_ALLSTARS_ROLES.monthly_donator
            )
            if monthly_donator_role and monthly_donator_role not in member.roles:
                try:
                    await member.add_roles(
                        monthly_donator_role,
                        reason="Reached monthly donation threshold",
                    )
                    pretty_log(
                        message=f"✅ Added Monthly Donator role to user ID: {member.id} ({member.name})",
                        tag="donation",
                    )
                except Exception as e:
                    pretty_log(
                        message=f"❌ Failed to add Monthly Donator role to user ID: {member.id} ({member.name}): {e}",
                        tag="error",
                        include_trace=True,
                    )
            if monthly_donator_streak >= 2 and not permanent_monthly_donator:
                await update_monthly_donator_status(
                    bot, member.id, True, permanent=True
                )
                milestone_added = True
                pretty_log(
                    message=f"🏆 User ID: {member.id} ({member.name}) has reached a monthly donator streak of {monthly_donator_streak} and is now a permanent monthly donator!",
                    tag="donation",
                )
                confirm_description += f"\n🏆 You've also reached a monthly donator streak of {monthly_donator_streak} and are now a permanent monthly donator!"
                log_description += f"**Monthly Donator Streak:** {monthly_donator_streak}\n**Permanent Monthly Donator:** Yes\n"

            elif monthly_donator_streak < 2:
                milestone_added = True
                confirm_description += f"\n🔥 Your current monthly donator streak is {monthly_donator_streak}. Keep donating to become a permanent monthly donator!"
                log_description += f"**Monthly Donator Streak:** {monthly_donator_streak}\n**Permanent Monthly Donator:** No\n"

            elif permanent_monthly_donator:
                confirm_description += f"\n🏆 You are already a permanent monthly donator! Your current monthly donator streak is {monthly_donator_streak}."
                log_description += f"**Monthly Donator Streak:** {monthly_donator_streak}\n**Permanent Monthly Donator:** Yes\n"

    # Get roles
    diamond_role = member.guild.get_role(VN_ALLSTARS_ROLES.diamond_donator)
    legendary_role = member.guild.get_role(VN_ALLSTARS_ROLES.legendary_donator)
    shiny_role = member.guild.get_role(VN_ALLSTARS_ROLES.shiny_donator)
    diamond_milestone = DONATION_MILESTONE_MAP["diamond_donator"]["threshold"]
    legendary_milestone = DONATION_MILESTONE_MAP["legendary_donator"]["threshold"]
    shiny_milestone = DONATION_MILESTONE_MAP["shiny_donator"]["threshold"]

    milestone_roles_added_str = "\n\n**New Milestone Roles Added:**\n"

    # Check and assign higher tier roles
    if diamond_role not in member.roles and total_donations >= diamond_milestone:
        milestone_added = True
        try:
            await member.add_roles(
                diamond_role, reason="Reached diamond donation milestone"
            )
            pretty_log(
                message=f"💎 Added Diamond Donator role to user ID: {member.id} ({member.name})",
                tag="donation",
            )
            milestone_roles_added_str += f"- {diamond_role.mention}\n"
        except Exception as e:
            pretty_log(
                message=f"❌ Failed to add Diamond Donator role to user ID: {member.id} ({member.name}): {e}",
                tag="error",
                include_trace=True,
            )
    if legendary_role not in member.roles and total_donations >= legendary_milestone:
        milestone_added = True
        try:
            await member.add_roles(
                legendary_role, reason="Reached legendary donation milestone"
            )
            pretty_log(
                message=f"💎 Added Legendary Donator role to user ID: {member.id} ({member.name})",
                tag="donation",
            )
            milestone_roles_added_str += f"- {legendary_role.mention}\n"
        except Exception as e:
            pretty_log(
                message=f"❌ Failed to add Legendary Donator role to user ID: {member.id} ({member.name}): {e}",
                tag="error",
                include_trace=True,
            )
    if shiny_role not in member.roles and total_donations >= shiny_milestone:
        milestone_added = True
        try:
            await member.add_roles(
                shiny_role, reason="Reached shiny donation milestone"
            )
            pretty_log(
                message=f"💎 Added Shiny Donator role to user ID: {member.id} ({member.name})",
                tag="donation",
            )
            milestone_roles_added_str += f"- {shiny_role.mention}\n"
        except Exception as e:
            pretty_log(
                message=f"❌ Failed to add Shiny Donator role to user ID: {member.id} ({member.name}): {e}",
                tag="error",
                include_trace=True,
            )
    if milestone_added:
        embed.description = confirm_description + milestone_roles_added_str
        log_embed.description = log_description + milestone_roles_added_str
        clan_donation_channel = member.guild.get_channel(
            VN_ALLSTARS_TEXT_CHANNELS.clan_donations
        )
        if clan_donation_channel:
            await clan_donation_channel.send(embed=embed)
        await send_log_to_server_log(
            bot,
            guild=member.guild,
            embed=log_embed,
        )


async def update_donation_func(
    bot: commands.Bot,
    interaction: discord.Interaction,
    member: discord.Member,
    total_donations: int = None,
    monthly_donations: int = None,
):
    """Update the donation record for a user."""
    #  Defer
    loader = await pretty_defer(
        interaction=interaction, content="Updating donation record...", ephemeral=False
    )

    # Check if staff
    if not is_staff_member(interaction.user):
        await loader.error(content="Only staff members can use this command.")
        return

    #  Fetch current donation record
    donation_record = await fetch_donation_record(bot, member.id)
    # Upsert if no record exists
    if not donation_record:
        try:
            await upsert_donation_record(
                bot=bot,
                user_id=member.id,
                user_name=member.name,
                total_donations=0,
                monthly_donations=0,
            )
            # Fetch the newly created record
            donation_record = await fetch_donation_record(bot, member.id)
            pretty_log(
                message=f"✅ Created new donation record for user ID: {member.id}",
            )
        except Exception as e:
            pretty_log(
                message=f"❌ Failed to create donation record for user ID: {member.id}: {e}",
                tag="error",
                include_trace=True,
            )
            await loader.error(
                content="Failed to create donation record. Please try again later."
            )
            return

    # Get old values for logging
    old_total = donation_record.get("total_donations", 0)
    old_monthly = donation_record.get("monthly_donations", 0)
    permanent_monthly_donator = donation_record.get("permanent_monthly_donator", False)
    monthly_donator_streak = donation_record.get("monthly_donator_streak", 0)
    monthly_donator = donation_record.get("monthly_donator", False)

    desc = f"**Member:** {member.mention}\n"
    # Update values
    if total_donations:
        await update_total_donations(bot, member.id, total_donations)
        desc += f"**Total Donations:** {format_comma_pokecoins(old_total)} ➔ {format_comma_pokecoins(total_donations)}\n"

    if monthly_donations:
        await update_monthly_donations(bot, member.id, monthly_donations)
        desc += f"**Monthly Donations:** {format_comma_pokecoins(old_monthly)} ➔ {format_comma_pokecoins(monthly_donations)}\n"

    # Confirmation Embed
    confirm_embed = discord.Embed(
        title="✅ Donation Record Updated",
        color=DEFAULT_EMBED_COLOR,
        description=desc,
        timestamp=datetime.now(),
    )
    confirm_embed.set_thumbnail(url=member.display_avatar.url)
    confirm_embed.set_author(
        name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url
    )
    confirm_embed.set_footer(
        text="User ID: {member.id}",
        icon_url=member.guild.icon.url if member.guild.icon else None,
    )
    await loader.success(embed=confirm_embed, content="")
    log_channel_id = VN_ALLSTARS_TEXT_CHANNELS.member_logs
    log_channel = bot.get_channel(log_channel_id)
    await send_webhook(
        bot=bot,
        channel=log_channel,
        embed=confirm_embed,
    )
    # Check and update monthly donator status
    await check_monthly_and_update_donation_status(
        bot=bot,
        member=member,
    )
