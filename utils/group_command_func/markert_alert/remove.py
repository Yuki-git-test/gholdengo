import discord
from discord.ext import commands

from Constants.aesthetic import *
from Constants.vn_allstars_constants import VN_ALLSTARS_EMOJIS, KHY_USER_ID
from utils.cache.cache_list import market_alert_cache
from utils.db.market_alert_db import (
    remove_all_market_alerts_for_user,
    remove_market_alert,
)
from utils.db.market_alert_user import fetch_market_alert_user, update_alerts_used
from utils.logs.pretty_log import pretty_log
from utils.logs.server_log import send_log_to_server_log
from utils.visuals.design_embed import design_embed
from utils.visuals.pretty_defer import pretty_defer

from .add import resolve_pokemon_input_func


async def remove_market_alert_func(
    bot: commands.Bot,
    interaction: discord.Interaction,
    pokemon: str,
):
    """
    Removes an/all existing market alert(s) for a user.
    """

    user = interaction.user
    user_id = user.id
    user_name = user.name
    guild = interaction.guild

    # Initialize loader
    loader = await pretty_defer(
        interaction=interaction,
        content="Removing your market alert...",
        ephemeral=False,
    )
    if pokemon.lower() == "all":
        # Check if user has any alerts
        existing_alerts = [
            alert for alert in market_alert_cache if alert["user_id"] == user_id
        ]
        if not existing_alerts:
            await loader.error(content="You have no market alerts to remove.")
            return

        # Get count of alerts to be removed
        alert_count = len(existing_alerts)

        # Remove all alerts for the user
        await remove_all_market_alerts_for_user(bot, user_id)

        # Send success message
        embed = discord.Embed(
            title="✅ Market Alerts Removed",
            description=f"All ({alert_count}) of your market alerts have been removed.",
        )
        footer_text = "You can add new alerts using the /market-alert add command."
        embed = design_embed(embed=embed, user=user, footer_text=footer_text)
        await loader.success(embed=embed, content="")
        pretty_log(
            message=f"✅ Removed all ({alert_count}) market alerts for user {user_name} ({user_id}).",
            tag="market_alert",
        )
        # Fetch max alerts for logging
        alert_user = await fetch_market_alert_user(bot, user_id)
        max_alerts = alert_user["max_alerts"] if alert_user else "N/A"

        # Send log to server log
        embed = discord.Embed(
            title="🗑️ All Market Alerts Removed",
            description=(
                f"**User:** {user.mention}\n"
                f"**Alerts Removed:** {alert_count}\n"
                f"**Max Alerts Allowed:** {max_alerts}\n"
            ),
        )
        embed = design_embed(embed=embed, user=user)
        await send_log_to_server_log(bot, guild, embed)
        # Update alerts used in db
        await update_alerts_used(bot, user_id, 0)
        return

    else:
        # Resolve Pokemon input
        try:
            target_name, dex_number = resolve_pokemon_input_func(pokemon)
        except ValueError as e:
            pretty_log(
                "error",
                f"Failed to resolve Pokemon input '{pokemon}' for user {user_name} (ID: {user_id}): {e}",
                label="MARKET ALERT ADD",
            )
            await loader.error(str(e))
            return

        # Check if user has an existing alert for this pokemon
        existing_alert = None
        for alert in market_alert_cache:
            if (
                alert["user_id"] == user_id
                and alert["pokemon"].lower() == target_name.lower()
            ):
                existing_alert = alert
                break
        if not existing_alert:
            await loader.error(
                content=f"You do not have an existing market alert for **{target_name}**."
            )
            return

        # Get values before removal for logging
        channel_id = existing_alert["channel_id"]
        role_id = existing_alert["role_id"] if existing_alert["role_id"] else "None"
        max_price = existing_alert["max_price"]

        role_str = f"<@&{role_id}>" if role_id != "None" else "None"

        # Remove the specific market alert
        await remove_market_alert(bot, user_id, target_name.lower())

        # Update alerts used in db

        # Get updated alerts used count
        alert_user = await fetch_market_alert_user(bot, user_id)
        max_alerts = alert_user["max_alerts"] if alert_user else 0
        old_alerts_used = alert_user["alerts_used"] if alert_user else 0
        if old_alerts_used > 0:
            new_alerts_used = old_alerts_used - 1
            await update_alerts_used(bot, user_id, new_alerts_used)
        else:
            new_alerts_used = 0

        # Send success message
        desc = (
            f"**Alerts Used:** {new_alerts_used}/{max_alerts}\n"
            f"**Pokemon:** {target_name.title()} #{dex_number}\n"
            f"**Max Price:** {VN_ALLSTARS_EMOJIS.vna_pokecoin} {max_price:,}\n"
            f"**Channel:** <#{channel_id}>\n"
            f"**Role:** {role_str}\n"
        )
        embed = discord.Embed(
            title="✅ Market Alert Removed",
            description=desc,
        )
        footer_text = "You can add a new alert using the /market-alert add command."
        embed = design_embed(
            embed=embed, user=user, footer_text=footer_text, pokemon_name=target_name
        )
        await loader.success(embed=embed, content="")
        pretty_log(
            message=f"✅ Removed market alert for {target_name} for user {user_name} ({user_id}).",
            tag="market_alert",
        )
        desc = (
            f"**User:** {user.mention}\n"
            f"**Alerts Used:** {new_alerts_used}/{max_alerts}\n"
            f"**Pokemon:** {target_name.title()} #{dex_number}\n"
            f"**Max Price:** {VN_ALLSTARS_EMOJIS.vna_pokecoin} {max_price:,}\n"
            f"**Channel:** <#{channel_id}>\n"
            f"**Role:** {role_str}\n"
        )
        # Send log to server log channel
        embed = discord.Embed(
            title="🗑️ Market Alert Removed",
            description=desc,
        )
        embed = design_embed(embed=embed, user=user, pokemon_name=target_name)
        if interaction.user.id != KHY_USER_ID:
            await send_log_to_server_log(bot, guild, embed)
