import random
import time

import discord
from discord.ext import commands
from datetime import datetime, timedelta
from Constants.vn_allstars_constants import (
    KHY_USER_ID,
    VN_ALLSTARS_EMOJIS,
    VN_ALLSTARS_ROLES,
    VN_ALLSTARS_TEXT_CHANNELS,
    YUKI_USER_ID,
)
from utils.cache.global_variables import TESTING_LOTTERY
from utils.db.lottery import (
    add_to_total_tickets,
    get_total_tickets,
    is_lottery_active,
    update_prize,
    update_total_tickets,
)
from utils.essentials.parsers import parse_compact_number
from utils.essentials.role_checks import *
from utils.functions.webhook_func import send_webhook
from utils.group_command_func.lottery.pokemon import if_testing_lottery
from utils.listener_func.buy_lottery_ticket_listener import (
    calculate_number_of_tickets_and_update_entry,
    create_lottery_tracker_embed,
    end_lottery,
    update_current_pot,
    update_tickets_sold,
)
from utils.functions.pokemon_func import format_price_w_coin
from utils.logs.pretty_log import pretty_log
from utils.visuals.pretty_defer import pretty_defer
from utils.db.lottery_entries import fetch_lottery_entry, update_lottery_entry
from .add import is_processing_lottery
async def remove_lottery_tickets_func(
    bot: commands.Bot,
    interaction: discord.Interaction,
    message_id: str,
    member: discord.Member,
    amount: str,
):
    """Removes lottery tickets from a user's entry in a lottery. If the user doesn't have an entry, it does nothing."""
    message_id = int(message_id)  # Ensure message_id is an integer
    pretty_log(
        message=f"Fetching lottery tickets for lottery with message ID {message_id}...",
        tag="info",
    )
    # Defer
    loader = await pretty_defer(
        interaction=interaction,
        content="Adding lottery tickets...",
        ephemeral=False,
    )

    # Check if active
    lottery_info = await is_lottery_active(bot, message_id)
    if not lottery_info:
        await loader.error("No lottery found with that message ID.")
        return
    # Check if already processing a lottery purchase or end lottery for this message ID
    is_processing, processing_message = is_processing_lottery(message_id)
    if is_processing:
        await loader.error(processing_message)
        return

    # Parse amount
    try:
        amount = parse_compact_number(amount)
    except ValueError:
        await loader.error("Please enter a valid number for the amount of tickets.")
        return

    member_id = member.id
    lottery_id = lottery_info["lottery_id"]
    channel, _ = if_testing_lottery(interaction.guild)
    ticket_cost = lottery_info["ticket_price"]
    max_tickets = lottery_info["max_tickets"]
    total_tickets = lottery_info["total_tickets"]
    lottery_id = lottery_info["lottery_id"]
    channel_id = lottery_info["channel_id"]
    message_id = lottery_info["message_id"]
    lottery_type = lottery_info["lottery_type"]

    # Fetch user's current lottery entry
    user_lottery_info = await fetch_lottery_entry(bot, lottery_id=lottery_id, user_id=member_id)
    if not user_lottery_info:
        await loader.error("That user doesn't have any tickets in this lottery.")
        return

    # Calculate new ticket total and ensure it doesn't go below 0
    current_tickets = user_lottery_info["entries"]
    new_user_ticket_total = max(current_tickets - amount, 0)
    new_lottery_total_tickets = max(total_tickets - amount, 0)

    # Compute new prize pool based on new total tickets
    new_pot = new_lottery_total_tickets * ticket_cost
    # Update the database with the new ticket totals
    await update_total_tickets(bot, lottery_id=lottery_id, new_total_tickets=new_lottery_total_tickets)
    await update_prize(bot, lottery_id=lottery_id, new_prize=str(new_pot))
    await update_lottery_entry(bot, lottery_id=lottery_id, user_id=member_id, entries=new_user_ticket_total)

    # Update the lottery message embed with the new prize pool and total tickets
    # Edit embed
    channel = bot.get_channel(channel_id)
    if not channel:
        pretty_log(
            "error",
            f"Could not find channel {channel_id} for lottery id {lottery_id} when trying to update lottery after ticket purchase. Message id: {message_id}",
        )
        return
    try:
        lottery_message = await channel.fetch_message(message_id)
    except Exception as e:
        pretty_log(
            "error",
            f"Could not fetch lottery message {message_id} for lottery id {lottery_id} when trying to update lottery after ticket purchase. Message id: {message_id}. Error: {e}",
        )
        return
    lottery_embed = lottery_message.embeds[0] if lottery_message.embeds else None
    if not lottery_embed:
        pretty_log(
            "error",
            f"No embed found in lottery message {message_id} for lottery id {lottery_id} when trying to update lottery after ticket purchase. Message id: {message_id}",
        )
        return
    updated_embed = update_tickets_sold(lottery_embed, str(new_lottery_total_tickets))
    try:
        await lottery_message.edit(embed=updated_embed)
    except Exception as e:
        pretty_log(
            "error",
            f"Could not edit lottery message {message_id} to update tickets sold for lottery id {lottery_id} after ticket purchase. Message id: {message_id}. Error: {e}",
        )
        return

    if lottery_type == "coin":
        # Also update the current pot field in the embed
        base_pot = lottery_info["base_pot"]
        ticket_price = lottery_info["ticket_price"]
        updated_embed, new_pot = update_current_pot(
            updated_embed, str(new_lottery_total_tickets), base_pot, ticket_price
        )
        try:
            await lottery_message.edit(embed=updated_embed)
            await update_prize(bot, lottery_id=lottery_id, new_prize=str(new_pot))
        except Exception as e:
            pretty_log(
                "error",
                f"Could not edit lottery message {message_id} to update current pot for lottery id {lottery_id} after ticket purchase. Message id: {message_id}. Error: {e}",
            )
            return
    # Log and send webhook
    lottery_link = f"https://discord.com/channels/{interaction.guild_id}/{channel_id}/{message_id}"
    new_prize_formatted = format_price_w_coin(new_pot) if lottery_type == "coin" else new_pot
    new_prize_pool_str = f"New Prize Pool: {new_prize_formatted}" if lottery_type == "coin" else ""
    desc = (
        f"**Lottery ID:** {lottery_id}\n"
        f"**Member:** {member.mention}\n"
        f"**Tickets Remove:** {total_tickets}\n"
        f"**Total Tickets:** {new_user_ticket_total}\n"
        f"{new_prize_pool_str}\n"
    )
    log_embed = discord.Embed(
        title="Lottery Tickets Removed",
        description=f"{amount} tickets removed from {member.mention} in lottery ID {lottery_id}.",
        color=discord.Color.red(),
        timestamp=datetime.now(),
        url=lottery_link,
    )
    log_embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    log_embed.set_thumbnail(url=member.display_avatar.url)
    log_channel = bot.get_channel(VN_ALLSTARS_TEXT_CHANNELS.server_log)
    if log_channel:
        await send_webhook(
            bot=bot,
            channel=log_channel,
            embed=log_embed,
        )
        


