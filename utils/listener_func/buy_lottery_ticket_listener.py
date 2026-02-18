import random
import time

import discord
from discord.ext import commands

from Constants.aesthetic import Emojis, Thumbnails
from Constants.lottery import Lotto_Extra_Entries
from Constants.vn_allstars_constants import (
    KHY_USER_ID,
    VN_ALLSTARS_EMOJIS,
    VN_ALLSTARS_ROLES,
    VN_ALLSTARS_TEXT_CHANNELS,
    YUKI_USER_ID,
)
from utils.cache.cache_list import processing_end_lottery_ids
from utils.cache.global_variables import TESTING_LOTTERY
from utils.db.lottery import (
    add_to_total_tickets,
    fetch_lottery_info_by_lottery_id,
    get_lottery_info_by_thread_id,
    get_total_tickets,
    mark_lottery_ended,
)
from utils.db.lottery_entries import (
    add_tickets_to_entry,
    delete_lottery_entry,
    fetch_all_entries_for_a_lottery,
    fetch_lottery_entry,
    update_lottery_entry,
    upsert_lottery_entry,
    user_has_lottery_entry,
)
from utils.essentials.parsers import parse_compact_number
from utils.essentials.role_checks import *
from utils.functions.get_pokemeow_reply import get_pokemeow_reply_member
from utils.functions.pokemon_func import is_mon_in_game
from utils.functions.webhook_func import send_webhook
from utils.logs.pretty_log import pretty_log
from utils.parsers.duration import parse_total_duration
from utils.visuals.get_pokemon_gif import get_pokemon_gif_from_cache
from utils.visuals.pretty_defer import pretty_defer

from .donation_listener import CLAN_BANK_IDS, extract_any_pokecoins_amount


async def create_and_send_winner_announcement(bot, lottery_info, winners):
    channel_id = lottery_info["channel_id"]
    channel = bot.get_channel(channel_id)
    if not channel:
        pretty_log(
            "error",
            f"Could not find channel {channel_id} for lottery id {lottery_info['lottery_id']} when trying to send winner announcement.",
        )
        return
    lottery_role_mention = f"<@&{VN_ALLSTARS_ROLES.lottery}>"
    if TESTING_LOTTERY:
        lottery_role_mention = ""
    if winners == "No winners":
        announcement = f"{lottery_role_mention} has ended. No one bought tickets."
    else:
        announcement = f"{lottery_role_mention} has ended,🏆 Congratulations {winners}! You won the lottery!"
    await channel.send(announcement)


async def create_lottery_tracker_embed(
    bot,
    user: discord.Member,
    lottery_id: int,
    lottery_type: str,
):
    user_lottery_entry = await fetch_lottery_entry(
        bot, lottery_id=lottery_id, user_id=user.id
    )
    lottery_info = await fetch_lottery_info_by_lottery_id(bot, lottery_id)
    channel_id = lottery_info["channel_id"]
    message_id = lottery_info["message_id"]

    user_entries = user_lottery_entry["entries"] if user_lottery_entry else 0
    base_entries = user_entries
    bonus_lines = []
    total_entries = user_entries
    for role_id, bonus_entry in Lotto_Extra_Entries.items():
        role = user.guild.get_role(role_id)
        if role in user.roles:
            base_entries -= bonus_entry
            if role:
                if bonus_entry == 1:
                    entry_line = f"- **{role.name} Bonus:** +{bonus_entry} Ticket"
                else:
                    entry_line = f"- **{role.name} Bonus:** +{bonus_entry} Tickets"
                bonus_lines.append(entry_line)
            else:
                bonus_lines.append(
                    f"- **Role {role_id} Bonus:** +{bonus_entry} Tickets"
                )

    bonus_text = "\n".join(bonus_lines) if bonus_lines else ""

    # Build tracker text
    if bonus_lines:
        tracker_text = (
            f"**Base Tickets:** {base_entries}\n"
            f"{bonus_text}\n"
            f"- **Total Tickets:** {total_entries}"
        )
    else:
        tracker_text = f"Total Tickets: {total_entries}"
    # Thumbnail based on lottery type
    if lottery_type == "pokemon":
        thumbnail_url = Thumbnails.pokemon_lottery_ticket
        embed_color = 0xFF69B4  # hot pink hex
    elif lottery_type == "coin":
        thumbnail_url = Thumbnails.coin_lottery_ticket
        embed_color = 0xFFD700  # gold hex
    else:
        thumbnail_url = None
    # Set prefix emoji and color based on roles
    prefix = ""
    if bonus_lines:
        prefix = "💎"

    name = f"{prefix} {user.display_name}"
    lottery_link = (
        f"https://discord.com/channels/{user.guild.id}/{channel_id}/{message_id}"
    )
    desc = f"- [Lottery ID: {lottery_id}]({lottery_link})\n- {tracker_text}"

    # Example usage: create embed with prefix and color
    embed = discord.Embed(description=desc, color=embed_color)
    embed.set_author(name=name, icon_url=user.display_avatar.url)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)

    return embed


def update_lottery_embed_with_winners(embed: discord.Embed, winners):
    # Get the embed description and split into lines
    desc_lines = embed.description.split("\n")
    new_desc_lines = []
    winner_line = f"🏆 **Winner:** {winners}"
    winner_added = False

    for line in desc_lines:
        # Replace the "Ends" line with "Ended"
        if line.strip().startswith("⏰ **Ends:**"):
            new_desc_lines.append("⏰ **Ended**")
            # Insert the winner line right after
            new_desc_lines.append(winner_line)
            winner_added = True
        else:
            new_desc_lines.append(line)

    # If "Ends" line wasn't found, just append winner at the end
    if not winner_added:
        new_desc_lines.append(winner_line)

    # Update the embed description
    embed.description = "\n".join(new_desc_lines)
    return embed


def update_tickets_sold(embed: discord.Embed, tickets: str):
    for field in embed.fields:
        if field.name == "Sold Tickets":
            embed.set_field_at(
                embed.fields.index(field),
                name="Sold Tickets",
                value=tickets,
                inline=False,
            )
            break
    return embed


async def pick_lottery_winners(
    bot: discord.Client, lottery_id: int, entries, max_winners: int = 1
):
    weighted_entries: list[int] = []
    entry_map: dict[int, dict] = {}

    for entry in entries:
        uid = entry["user_id"]
        count = entry["entries"]
        entry_map[uid] = dict(entry)
        weighted_entries.extend([uid] * count)

    # Pick winners
    winners: list[dict] = []
    chosen_ids = set()
    distinct_users = set(weighted_entries)

    while len(winners) < max_winners and len(chosen_ids) < len(distinct_users):
        winner_id = random.choice(weighted_entries)

        if winner_id in chosen_ids:
            weighted_entries = [uid for uid in weighted_entries if uid != winner_id]

        # Valid winner
        chosen_ids.add(winner_id)
        winner_entry = entry_map[winner_id]

        # Get user mention
        winner_entry["mention"] = f"<@{winner_id}>"
        winners.append(winner_entry)

        # Remove entry from db and local pool
        await delete_lottery_entry(bot, lottery_id=lottery_id, user_id=winner_id)
        weighted_entries = [uid for uid in weighted_entries if uid != winner_id]
    winners_str = (
        ", ".join([winner["mention"] for winner in winners])
        if winners
        else "No winners"
    )

    return winners_str


async def calculate_number_of_tickets_and_update_entry(
    bot,
    user: discord.Member,
    lottery_id: int,
    tickets_bought: int,
):
    """Calculates the total number of tickets whether it has bonus entries or not."""
    # Check if user has an entry already to determine if we need to apply bonus entries or not
    user_entry = await fetch_lottery_entry(bot, lottery_id=lottery_id, user_id=user.id)
    if user_entry:
        total_tickets = tickets_bought
        await add_tickets_to_entry(
            bot, lottery_id=lottery_id, user_id=user.id, tickets_to_add=total_tickets
        )
    else:
        for role_id, bonus_entry in Lotto_Extra_Entries.items():
            role = user.guild.get_role(role_id)
            if role in user.roles:
                tickets_bought += bonus_entry
        total_tickets = tickets_bought
        await upsert_lottery_entry(
            bot,
            lottery_id=lottery_id,
            user_id=user.id,
            user_name=user.name,
            entries=total_tickets,
        )
    return total_tickets


async def end_lottery(bot: commands.Bot, lottery_id: int):
    """Ends the lottery and picks a winner if there are any tickets sold."""
    if lottery_id in processing_end_lottery_ids:
        pretty_log(
            "info",
            f"Lottery id {lottery_id} is already being processed for ending.",
        )
        return
    processing_end_lottery_ids.add(lottery_id)

    lottery_info = await fetch_lottery_info_by_lottery_id(bot, lottery_id)
    if not lottery_info:
        pretty_log(
            "error",
            f"Could not find lottery info for lottery id {lottery_id} when trying to end lottery",
        )
        return

    # Lock thread first
    thread_id = lottery_info["thread_id"]
    thread = bot.get_channel(thread_id)
    if thread:
        try:
            # Change thread name to use lock emoji
            old_name = thread.name
            # Replace ticket emoji with lock emoji if present, else just prepend lock
            if old_name.startswith("🎟️"):
                new_name = old_name.replace("🎟️", "🔒", 1)
            else:
                new_name = f"🔒 {old_name}"
            await thread.edit(name=new_name, locked=True)
        except Exception as e:
            pretty_log(
                "error",
                f"Could not lock thread {thread_id} for lottery id {lottery_id} when trying to end lottery. Error: {e}",
            )
            processing_end_lottery_ids.remove(lottery_id)
    # Fetch message embed
    message_id = lottery_info["message_id"]
    channel_id = lottery_info["channel_id"]
    channel = bot.get_channel(channel_id)
    if not channel:
        pretty_log(
            "error",
            f"Could not find channel {channel_id} for lottery id {lottery_id} when trying to end lottery",
        )
        processing_end_lottery_ids.remove(lottery_id)
        return
    try:
        message = await channel.fetch_message(message_id)
    except Exception as e:
        pretty_log(
            "error",
            f"Could not fetch message {message_id} for lottery id {lottery_id} when trying to end lottery. Error: {e}",
        )
        processing_end_lottery_ids.remove(lottery_id)
        return

    lottery_embed = message.embeds[0] if message.embeds else None
    if not lottery_embed:
        pretty_log(
            "error",
            f"No embed found in lottery message {message_id} for lottery id {lottery_id} when trying to end lottery",
        )
        processing_end_lottery_ids.remove(lottery_id)
        return

    # Fetch all entries for the lottery
    entries = await fetch_all_entries_for_a_lottery(bot, lottery_id)
    if not entries:
        # Edit embed to show no winners and return
        winners = "Noone bought a ticket 😢"
    winners = await pick_lottery_winners(bot, lottery_id, entries)
    updated_embed = update_lottery_embed_with_winners(lottery_embed, winners)
    try:
        await message.edit(embed=updated_embed)
    except Exception as e:
        pretty_log(
            "error",
            f"Could not edit lottery message {message_id} to show winners for lottery id {lottery_id}. Error: {e}",
        )
        processing_end_lottery_ids.remove(lottery_id)
    # Mark lottery as ended in db
    await mark_lottery_ended(bot, lottery_id)
    await create_and_send_winner_announcement(bot, lottery_info, winners)

    processing_end_lottery_ids.remove(lottery_id)


async def buy_lottery_ticket_listener(bot: commands.Bot, message: discord.Message):
    """Listens to buy lottery ticket command output and updates the lottery message with the new ticket buyer and pot amount."""

    # Get replied message
    if not message.reference:
        return
    replied_message = (
        message.reference.resolved.content if message.reference.resolved else None
    )
    if not replied_message:
        return
    # Get member
    member = await get_pokemeow_reply_member(message)
    if not member:
        pretty_log(
            "info",
            f"Could not get member from PokéMeow reply for message {message.id}. Ignoring.",
        )
        return
    replied_message_object = message.reference.resolved if message.reference else None
    if replied_message_object:
        # React a loading emoji to the replied message to indicate we're processing the ticket purchase
        try:
            await replied_message_object.add_reaction(Emojis.loading)
        except Exception as e:
            pretty_log(
                "error",
                f"Could not add loading reaction to message {replied_message_object.id} when processing lottery ticket purchase for message {message.id}. Error: {e}",
            )
    # Check if any of the clan bank ids are mentioned in the replied message
    if not any(str(clan_bank_id) in replied_message for clan_bank_id in CLAN_BANK_IDS):
        pretty_log(
            "info",
            f"Message {message.id} does not mention any of the clan bank ids. Ignoring.",
        )
        return
    # Get lottery info based on current channel/thread id
    thread_id = message.channel.id
    lottery_info = await get_lottery_info_by_thread_id(bot, thread_id)
    if not lottery_info:
        pretty_log(
            "info",
            f"No lottery found for thread id {thread_id}. Ignoring.",
        )
        return
    ticket_cost = lottery_info["ticket_price"]
    max_tickets = lottery_info["max_tickets"]
    total_tickets = lottery_info["total_tickets"]
    lottery_id = lottery_info["lottery_id"]
    user_id = member.id
    guild = message.guild

    # Extract amount from the message content using regex
    amount = extract_any_pokecoins_amount(message.content)

    # Calculate how many tickets were bought based on the amount and ticket cost
    if ticket_cost == 0:
        tickets_bought = 1
    else:
        tickets_bought = amount // ticket_cost

    if tickets_bought <= 0:
        pretty_log(
            "info",
            f"Could not determine any tickets bought from message {message.id}. Ignoring.",
        )
        return

    # Cap tickets if max_tickets is set and handle refund
    if max_tickets != 0:
        # Get current tickets sold
        current_tickets_sold = await get_total_tickets(bot, lottery_id=lottery_id)
        available_tickets = max_tickets - current_tickets_sold
        if available_tickets <= 0:
            # No tickets left
            await message.channel.send(f"All tickets for this lottery are sold out!")
            return
        if tickets_bought > available_tickets:
            # Cap tickets and calculate refund
            excess_tickets = tickets_bought - available_tickets
            refund_amount = excess_tickets * ticket_cost
            tickets_bought = available_tickets
            # Ask bank account to refund excess
            await message.channel.send(
                f"You requested more tickets than available. Only {available_tickets} ticket(s) were purchased. Please ask for a refund {refund_amount:,} Pokécoins for the excess {excess_tickets} ticket(s)."
            )

    # Get lottery entry for the member
    total_tickets = await calculate_number_of_tickets_and_update_entry(
        bot, user=member, lottery_id=lottery_id, tickets_bought=tickets_bought
    )
    # Update total tickets in lottery db
    await add_to_total_tickets(bot, lottery_id=lottery_id, tickets_to_add=total_tickets)
    new_tickets_sold = await get_total_tickets(bot, lottery_id=lottery_id)
    # Edit lottery message embed to show new ticket buyer and updated pot amount
    channel_id = lottery_info["channel_id"]
    message_id = lottery_info["message_id"]
    channel = bot.get_channel(channel_id)
    if not channel:
        pretty_log(
            "error",
            f"Could not find channel {channel_id} for lottery id {lottery_id} when trying to update lottery after ticket purchase. Message id: {message.id}",
        )
        return
    try:
        lottery_message = await channel.fetch_message(message_id)
    except Exception as e:
        pretty_log(
            "error",
            f"Could not fetch lottery message {message_id} for lottery id {lottery_id} when trying to update lottery after ticket purchase. Message id: {message.id}. Error: {e}",
        )
        return
    lottery_embed = lottery_message.embeds[0] if lottery_message.embeds else None
    if not lottery_embed:
        pretty_log(
            "error",
            f"No embed found in lottery message {message_id} for lottery id {lottery_id} when trying to update lottery after ticket purchase. Message id: {message.id}",
        )
        return
    updated_embed = update_tickets_sold(lottery_embed, str(new_tickets_sold))
    try:
        await lottery_message.edit(embed=updated_embed)
    except Exception as e:
        pretty_log(
            "error",
            f"Could not edit lottery message {message_id} to update tickets sold for lottery id {lottery_id} after ticket purchase. Message id: {message.id}. Error: {e}",
        )
        return

    # Determine lottery type based on embed description
    embed_description = lottery_embed.description
    if "Pokemon Lottery" in embed_description:
        lottery_type = "pokemon"
    elif "Coin Lottery" in embed_description:
        lottery_type = "coin"
    else:
        lottery_type = "unknown"
    # Create tracker embed for the user
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

    # React to the user's message with a ticket emoji to indicate successful purchase
    try:
        if replied_message_object:
            await replied_message_object.add_reaction("🎟️")
            await replied_message_object.remove_reaction(Emojis.loading, bot.user)
        purchase_message = f"**{member.name}** bought {tickets_bought} ticket(s) for Lottery ID {lottery_id}."
        await message.channel.send(purchase_message)
    except Exception as e:
        pretty_log(
            "error",
            f"Could not add reaction to message {message.id} after lottery ticket purchase. Error: {e}",
        )
    # Check if max tickets has been reached and end lottery if so
    if max_tickets != 0 and new_tickets_sold >= max_tickets:
        pretty_log(
            "info",
            f"Max tickets reached for lottery id {lottery_id}. Ending lottery. Message id: {message.id}",
        )
        try:
            await end_lottery(bot, lottery_id)
            pretty_log(
                "info",
                f"Successfully ended lottery id {lottery_id} after max tickets reached. Message id: {message.id}",
            )
        except Exception as e:
            pretty_log(
                "error",
                f"Error ending lottery id {lottery_id} after max tickets reached. Message id: {message.id}. Error: {e}",
            )
