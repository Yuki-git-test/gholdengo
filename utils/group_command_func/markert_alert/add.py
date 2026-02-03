import discord
from discord.ext import commands

from Constants.aesthetic import *
from Constants.vn_allstars_constants import (
    KHY_USER_ID,
    VN_ALLSTARS_EMOJIS,
    VN_ALLSTARS_ROLES,
    YUKI_USER_ID,
)
from utils.cache.cache_list import market_alert_cache
from utils.db.market_alert_db import insert_market_alert
from utils.db.market_alert_user import (
    fetch_market_alert_user,
    fetch_user_role,
    increment_alerts_used,
    upsert_market_alert_user,
)
from utils.essentials.parsers import (
    parse_compact_number,
    parse_special_mega_input,
    resolve_pokemon_input,
)
from utils.essentials.role_checks import has_special_role
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log
from utils.logs.server_log import send_log_to_server_log
from utils.visuals.design_embed import design_embed
from utils.visuals.pretty_defer import pretty_defer

# enable_debug(f"{__name__}.resolve_pokemon_input_func")


def determine_max_alerts(user: discord.Member) -> int:
    """
    Determines the maximum number of market alerts a user can set based on their roles.
    Special roles grant higher limits.
    """
    SPECIAL_BOOSTER_ROLES = [
        VN_ALLSTARS_ROLES.server_booster,
        VN_ALLSTARS_ROLES.top_monthly_grinder,
        VN_ALLSTARS_ROLES.shiny_donator,
        VN_ALLSTARS_ROLES.legendary_donator,
        VN_ALLSTARS_ROLES.diamond_donator,
    ]
    staff_member_role_id = VN_ALLSTARS_ROLES.staff
    # if staff member default is 4 no matter what
    if any(role.id == staff_member_role_id for role in user.roles):
        return 4

    # If not staff, and they have any 2 special roles, max alerts is 2
    special_roles_count = sum(
        1 for role in user.roles if role.id in SPECIAL_BOOSTER_ROLES
    )
    if special_roles_count >= 2:
        return 2

    if user.id == YUKI_USER_ID:
        return 100

    # If not staff and less than 2 special roles, max alerts is 1
    return 1


def resolve_pokemon_input_func(pokemon: str):
    """
    Converts any user input (name or dex) into a normalized Pokemon name and Dex number.
    Handles:
    - Numeric Dex input (normal, shiny, golden, special forms)
    - Name input (including shiny/golden prefixes, Mega forms)
    Returns: (display_name, dex_number)
    """
    pokemon_title = pokemon.title()
    debug_log(f"Resolving Pokemon input: '{pokemon}'")
    if pokemon.isdigit():
        if len(pokemon) == 4 and not pokemon.startswith(("1", "7", "9")):
            raise ValueError("Invalid 4-digit Dex number.")
        target_name, dex_number = resolve_pokemon_input(pokemon)

    elif any(
        (
            pokemon_title.startswith(f"{prefix}Mega ")
            or pokemon_title.startswith(f"{prefix}Mega-")
        )
        for prefix in ["", "Shiny ", "Golden "]
    ):
        debug_log(f"Detected prefixed Mega form in input: '{pokemon}'")
        dex_number = parse_special_mega_input(pokemon)
        debug_log(f"Parsed dex number for Mega form: {dex_number}")
        target_name = pokemon_title
    else:
        debug_log(f"Assuming name input for Pokemon: '{pokemon}'")
        target_name, dex_number = resolve_pokemon_input(pokemon)
    debug_log(
        f"Resolved Pokemon input '{pokemon}' to Name: '{target_name}', Dex: {dex_number}"
    )
    return target_name, dex_number


# Add a market alert for a user
async def add_market_alert_func(
    bot: commands.Bot,
    interaction: discord.Interaction,
    pokemon: str,
    max_price: str,
    channel: discord.TextChannel,
    ping_role: str,
):
    """
    Adds a market alert for a user.
    """
    # Log pokemon
    pretty_log(
        "info",
        f"Attempting to add market alert for Pokemon input '{pokemon}' by user {interaction.user.name} (ID: {interaction.user.id})",
        label="MARKET ALERT ADD",
    )

    try:
        # Initialize loader
        loader = await pretty_defer(
            interaction=interaction,
            content="Setting up your market alert...",
            ephemeral=False,
        )
        user = interaction.user
        user_id = user.id
        user_name = user.name
        guild = interaction.guild
        role = None

        # Check if user has special role
        if not has_special_role(user):
            await loader.error("You do not have permission to set market alerts.")
            return

        if ping_role.lower() == "yes":
            # Fetch custom role for user
            role_id = await fetch_user_role(bot, user)
            role = guild.get_role(role_id)
            if not role and not role_id:
                await loader.error(
                    "You do not have a custom market alert role set. Please ask staff to set one for you."
                )
                return

        # Fetch user info from market_alert_users table
        user_info = await fetch_market_alert_user(bot, user_id)
        if not user_info:
            max_alerts = determine_max_alerts(user)
            await upsert_market_alert_user(bot, user, max_alerts=max_alerts)
        else:
            max_alerts = user_info["max_alerts"]
            alerts_used = user_info["alerts_used"]
            if alerts_used >= max_alerts:
                await loader.error(
                    f"You have reached your maximum number of market alerts ({max_alerts})."
                )
                return

        # Validate max price
        parse_price = parse_compact_number(max_price)
        if not parse_price:
            await loader.error(
                content="Invalid max price. Use formats like '1000', '1k', '1.5m'. Max is 10 billion.",
            )
            return
        max_price = int(parse_price)

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

        # Insert market alert into database
        try:
            await insert_market_alert(
                bot=bot,
                user=user,
                pokemon=target_name.lower(),
                dex=dex_number,
                max_price=max_price,
                channel_id=channel.id,
                role_id=role.id if role else None,
            )
            pretty_log(
                "info",
                f"✅ Added market alert for {target_name} (Dex: {dex_number}) at max price {max_price} for user {user_name} (ID: {user_id})",
                label="MARKET ALERT ADD",
            )
            await increment_alerts_used(bot, user_id)

            # Fetch updated user info
            updated_user_info = await fetch_market_alert_user(bot, user_id)
            current_alerts_used = updated_user_info["alerts_used"]
            current_max_alerts = updated_user_info["max_alerts"]

            embed = discord.Embed(
                title="✅ Market Alert Added",
                description=(
                    f"**Alerts:** {current_alerts_used}/{current_max_alerts}\n"
                    f"**Pokemon:** {target_name.title()} #{dex_number}\n"
                    f"**Max Price:** {VN_ALLSTARS_EMOJIS.vna_pokecoin} {max_price:,}\n"
                    f"**Channel:** {channel.mention}\n"
                    f"**Role:** {role.mention if role else 'None'}\n\n"
                ),
            )
            footer_text = (
                "You will be notified when a matching market listing is found."
            )
            embed = design_embed(
                embed=embed,
                user=user,
                footer_text=footer_text,
                pokemon_name=target_name,
            )
            pretty_log(
                "sucess",
                f"✅ Successfully set market alert for user {user_name} (ID: {user_id})",
                label="MARKET ALERT ADD",
            )
            await loader.success(embed=embed, content="")

            # Send log to server log channel
            log_embed = discord.Embed(
                title="📢 New Market Alert Set",
                description=(
                    f"**User:** {user.mention}\n"
                    f"**Alerts:** {current_alerts_used}/{current_max_alerts}\n"
                    f"**Pokemon:** {target_name.title()} #{dex_number}\n"
                    f"**Max Price:** {VN_ALLSTARS_EMOJIS.vna_pokecoin} {max_price:,}\n"
                    f"**Channel:** {channel.mention}\n"
                    f"**Role:** {role.mention if role else 'None'}\n"
                ),
            )
            log_embed = design_embed(
                embed=log_embed, user=user, pokemon_name=target_name
            )

            if interaction.user.id != KHY_USER_ID:
                await send_log_to_server_log(bot, guild, log_embed)

        except Exception as e:
            pretty_log(
                "error",
                f"Failed to set market alert for user {user_name} (ID: {user_id}): {e}",
                label="MARKET ALERT ADD",
            )
            await loader.error(f"Failed to set market alert: {e}")
            return
    except Exception as e:
        pretty_log(
            "error",
            f"Unexpected error in add_market_alert_func for user {user_name} (ID: {user_id}): {e}",
            label="MARKET ALERT ADD",
        )
