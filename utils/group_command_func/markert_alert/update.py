import discord
from discord.ext import commands

from Constants.aesthetic import *
from Constants.vn_allstars_constants import VN_ALLSTARS_EMOJIS, YUKI_USER_ID
from utils.cache.cache_list import market_alert_cache
from utils.db.market_alert_db import update_market_alert
from utils.db.market_alert_user import fetch_user_role
from utils.essentials.parsers import parse_compact_number
from utils.logs.pretty_log import pretty_log
from utils.logs.server_log import send_log_to_server_log
from utils.visuals.design_embed import design_embed
from utils.visuals.pretty_defer import pretty_defer, pretty_error

from .add import resolve_pokemon_input_func


async def update_market_alert_func(
    bot: commands.Bot,
    interaction: discord.Interaction,
    pokemon: str,
    new_max_price: str = None,
    new_channel: discord.TextChannel = None,
    ping_role: str = None,
):
    """
    Updates an existing market alert for a user.
    """

    # Check if there are anything to update
    if not any([new_max_price, new_channel, ping_role]):
        await pretty_error(
            interaction,
            "No update parameters provided. Please specify at least one field to update.",
        )
        return

    user = interaction.user
    user_id = user.id
    user_name = user.name
    guild = interaction.guild

    # Initialize loader
    loader = await pretty_defer(
        interaction=interaction,
        content="Updating your market alert...",
        ephemeral=False,
    )

    # Resolve the pokemon input
    try:
        target_name, dex_number = resolve_pokemon_input_func(pokemon)
    except ValueError as e:
        await loader.error(content=str(e))
        return

    # Validate new price
    if new_max_price:
        parsed_price = parse_compact_number(new_max_price)
        if not parsed_price:
            await loader.error(
                content="Invalid price format. Please enter a valid number."
            )
            return

    # Fetch existing alert from cache
    old_market_alert_info = None
    for alert in market_alert_cache:
        if (
            alert["user_id"] == user_id
            and alert["pokemon"].lower() == target_name.lower()
        ):
            old_market_alert_info = alert
            break
    if not old_market_alert_info:
        await loader.error(
            content=f"No existing market alert found for **{target_name}**. Please add an alert first."
        )
        return

    old_channel_id = old_market_alert_info["channel_id"]
    old_role_id = old_market_alert_info["role_id"]
    old_max_price = old_market_alert_info["max_price"]
    old_role_id = old_market_alert_info["role_id"]
    if ping_role:
        pr = ping_role.lower()
        if not old_role_id and pr == "yes":
            # Fetch custom role for user
            role_id = await fetch_user_role(bot, user)
            new_role = guild.get_role(role_id)
            if not new_role:
                await loader.error(
                    "You do not have a custom market alert role set. Please ask staff to set one for you."
                )
                return
        elif old_role_id and pr == "no":
            new_role = None
        elif old_role_id and pr == "yes":
            # Keep existing role
            new_role = guild.get_role(old_role_id)
        elif old_role_id and not pr:
            # Keep existing role
            new_role = guild.get_role(old_role_id)
        elif not old_role_id and pr == "no":
            new_role = None
        else:
            await loader.error(
                f"Invalid ping_role value: {ping_role}. Please use 'yes' or 'no'."
            )
            return
    else:
        # If ping_role is not provided, keep existing role if present
        new_role = guild.get_role(old_role_id) if old_role_id else None

    # Update in database
    try:
        await update_market_alert(
            bot=bot,
            user_id=user_id,
            pokemon=target_name.lower(),
            new_max_price=int(parsed_price) if new_max_price else None,
            new_channel_id=new_channel.id if new_channel else None,
            new_role_id=new_role.id if new_role else None,
        )
        pretty_log(
            message=f"✅ Updated market alert for {user_name} (ID: {user_id}) - {target_name}",
            tag="db",
        )
        # Build confirmation message
        embed = discord.Embed(
            title="Market Alert Updated!",
            description=f"**Pokemon:** {target_name.title()} #{dex_number}\n",
        )
        if new_max_price:
            embed.description += f"**Max Price:** {VN_ALLSTARS_EMOJIS.vna_pokecoin} {old_max_price} → {VN_ALLSTARS_EMOJIS.vna_pokecoin} {parsed_price}\n"
        if new_channel:
            old_channel_mention = f"<#{old_channel_id}>"
            new_channel_mention = f"<#{new_channel.id}>"
            embed.description += (
                f"**Channel:** {old_channel_mention} → {new_channel_mention}\n"
            )
        if new_role and ping_role:
            old_role_mention = f"<@&{old_role_id}>" if old_role_id else "None"
            new_role_mention = f"<@&{new_role.id}>"
            embed.description += f"**Role:** {old_role_mention} → {new_role_mention}\n"
        footer_text = "You will be notified when a matching market listing is found."
        embed = design_embed(
            embed=embed, user=user, pokemon_name=target_name, footer_text=footer_text
        )
        await loader.success(embed=embed, content="")

        # Send log to server log channel
        log_embed = discord.Embed(
            title="📢 Market Alert Updated",
            description=(
                f"**User:** {user.mention}\n"
                f"**Pokemon:** {target_name.title()} #{dex_number}\n"
            ),
        )
        if new_max_price:
            log_embed.description += f"**Max Price:** {VN_ALLSTARS_EMOJIS.vna_pokecoin} {old_max_price} → {VN_ALLSTARS_EMOJIS.vna_pokecoin} {parsed_price}\n"
        if new_channel:
            old_channel_mention = f"<#{old_channel_id}>"
            new_channel_mention = f"<#{new_channel.id}>"
            log_embed.description += (
                f"**Channel:** {old_channel_mention} → {new_channel_mention}\n"
            )
        if new_role and ping_role:
            old_role_mention = f"<@&{old_role_id}>" if old_role_id else "None"
            new_role_mention = f"<@&{new_role.id}>"
            log_embed.description += (
                f"**Role:** {old_role_mention} → {new_role_mention}\n"
            )
        log_embed = design_embed(embed=log_embed, user=user, pokemon_name=target_name)
        await send_log_to_server_log(bot, embed=log_embed, guild=guild)

    except Exception as e:
        await loader.error(
            content="An error occurred while updating your market alert. Please try again later."
        )
        pretty_log(
            message=f"❌ Failed to update market alert for {user_name} (ID: {user_id}): {e}",
            tag="error",
            include_trace=True,
        )
        return
