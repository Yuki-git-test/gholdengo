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
from utils.logs.pretty_log import pretty_log
from utils.visuals.pretty_defer import pretty_defer
from utils.db.lottery_entries import fetch_lottery_entry
from utils.cache.cache_list import processing_lottery_purchase_ids, processing_end_lottery_ids

def is_processing_lottery(message_id: int) -> bool:
    """Checks if a lottery purchase or end lottery is currently being processed for the given message ID."""
    if message_id in processing_lottery_purchase_ids:
        return True, f"Another lottery purchase is currently being processed for this lottery (message ID: {message_id}). Please wait a moment and try again."
    if message_id in processing_end_lottery_ids:
        return True, f"The lottery is currently ending for this lottery (message ID: {message_id}). Please wait a moment and try again."
    return False, None

async def add_lottery_tickets_func(
    bot: commands.Bot,
    interaction: discord.Interaction,
    message_id: str,
    member: discord.Member,
    amount: str,
):
    """Adds lottery tickets to a user's entry in a lottery. If the user doesn't have an entry, it creates one for them."""
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

    # Cap tickets if max_tickets is set and handle refund
    if max_tickets != 0:
        # Get current tickets sold
        current_tickets_sold = await get_total_tickets(bot, lottery_id=lottery_id)
        available_tickets = max_tickets - current_tickets_sold
        if amount > available_tickets:
            await loader.error(
                f"Only {available_tickets} tickets are available for this lottery. Please enter a valid amount."
            )
            return

    # Get lottery entry for the member
    total_tickets = await calculate_number_of_tickets_and_update_entry(
        bot, user=member, lottery_id=lottery_id, tickets_bought=amount
    )

    # Update total tickets in lottery db
    await add_to_total_tickets(bot, lottery_id=lottery_id, tickets_to_add=total_tickets)
    new_tickets_sold = await get_total_tickets(bot, lottery_id=lottery_id)

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
    updated_embed = update_tickets_sold(lottery_embed, str(new_tickets_sold))
    try:
        await lottery_message.edit(embed=updated_embed)
    except Exception as e:
        pretty_log(
            "error",
            f"Could not edit lottery message {message_id} to update tickets sold for lottery id {lottery_id} after ticket purchase. Message id: {message_id}. Error: {e}",
        )
        return

    # Create Tracker ember
    tracker_embed = await create_lottery_tracker_embed(
        bot,
        user=member,
        lottery_id=lottery_id,
        lottery_type=lottery_type,
    )
    tracker_channel_id = VN_ALLSTARS_TEXT_CHANNELS.lottery_tracker
    if TESTING_LOTTERY:
        tracker_channel_id = VN_ALLSTARS_TEXT_CHANNELS.khys_chamber
    tracker_channel = bot.get_channel(tracker_channel_id)
    if tracker_channel:
        await tracker_channel.send(embed=tracker_embed)

    if lottery_type == "coin":
        # Also update the current pot field in the embed
        base_pot = lottery_info["base_pot"]
        ticket_price = lottery_info["ticket_price"]
        updated_embed, new_pot = update_current_pot(
            updated_embed, str(new_tickets_sold), base_pot, ticket_price
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
    # Log embed
    user_lottery_info = await fetch_lottery_entry(bot, lottery_id=lottery_id, user_id=member_id)
    user_new_total_tickets = (
        user_lottery_info["entries"] if user_lottery_info else total_tickets
    )
    lottery_link = f"https://discord.com/channels/{interaction.guild_id}/{channel_id}/{message_id}"
    desc = (
        f"**Lottery ID:** {lottery_id}\n"
        f"**Member:** {member.mention}\n"
        f"**Tickets Added:** {total_tickets}\n"
        f"**Total Tickets:** {user_new_total_tickets}\n"
    )
    log_embed = discord.Embed(
        title="Lottery Ticke(s) Added",
        url=lottery_link,
        description=desc,
        color=discord.Color.green(),
        timestamp=datetime.now(),
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
    # Check if max tickets has been reached and end lottery if so
    if max_tickets != 0 and new_tickets_sold >= max_tickets:
        pretty_log(
            "info",
            f"Max tickets reached for lottery id {lottery_id}. Ending lottery. Message id: {message_id}",
        )
        try:
            await end_lottery(bot, lottery_id)
            pretty_log(
                "info",
                f"Successfully ended lottery id {lottery_id} after max tickets reached. Message id: {message_id}",
            )
        except Exception as e:
            pretty_log(
                "error",
                f"Error ending lottery id {lottery_id} after max tickets reached. Message id: {message_id}. Error: {e}",
            )
