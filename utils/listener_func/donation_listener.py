import re
from datetime import datetime

import discord

from Constants.aesthetic import Thumbnails
from Constants.vn_allstars_constants import (
    CLAN_BANK_ID,
    DEFAULT_EMBED_COLOR,
    KHY_USER_ID,
    MIN_DONATION_AMOUNT,
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
from utils.functions.get_pokemeow_reply import get_pokemeow_reply_member
from utils.functions.webhook_func import send_webhook
from utils.group_command_func.donation.update import (
    check_monthly_and_update_donation_status,
)
from utils.logs.pretty_log import pretty_log
from utils.visuals.design_embed import design_embed

CLAN_BANK_IDS = [CLAN_BANK_ID, YUKI_USER_ID]

LOG_CHANNEL_ID = VN_ALLSTARS_TEXT_CHANNELS.member_logs


def extract_pokecoins_amount_from_donate(text: str) -> int:
    """
    Extracts the donated PokeCoins amount from a message like:
    'You successfully donated <...> **50,000** to ...'
    """
    match = re.search(
        r"donated.*?\*\*(?P<amount>[\d,]+)\*\*",
        text,
        re.IGNORECASE,
    )

    if match:
        amount = int(match.group("amount").replace(",", ""))
        pretty_log(
            "info",
            f"[EXTRACT] Extracted amount {amount} from donation message: {text}",
        )
        return amount

    pretty_log(
        "info",
        f"[EXTRACT] Could not extract amount from donation message: {text}",
    )
    return 0


def extract_any_pokecoins_amount(text: str) -> int:
    """
    Extracts the PokeCoins amount immediately preceding 'PokeCoins'
    and returns it as an int.
    """
    match = re.search(
        r"([\d,]+)\s*PokeCoins?",
        text,
        re.IGNORECASE,
    )

    if match:
        amount = int(match.group(1).replace(",", ""))
        pretty_log(
            "info",
            f"[EXTRACT] Extracted PokeCoins amount: {amount} from message: {text}",
        )
        return amount

    pretty_log(
        "info",
        f"[EXTRACT] Could not extract PokeCoins amount from message: {text}",
    )
    return 0


async def clan_donate_listener(bot: discord.Client, message: discord.Message):
    # Get member
    member = await get_pokemeow_reply_member(message)
    if not member:
        pretty_log(
            "info",
            f"Could not get member from PokéMeow reply for message {message.id}. Ignoring.",
        )
        return
    # Extract donation amount from message content
    content = message.content
    amount = extract_pokecoins_amount_from_donate(content)
    if amount < MIN_DONATION_AMOUNT:
        pretty_log(
            "info",
            f"Extracted amount {amount} is less than minimum donation amount. Ignoring.",
        )
        return
    await process_donation(
        bot, member, amount, context="clan treasury", message=message
    )


async def give_command_listener(bot: discord.Client, message: discord.Message):

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

    # Check if any of the clan bank ids are mentioned in the replied message
    if not any(str(clan_bank_id) in replied_message for clan_bank_id in CLAN_BANK_IDS):
        pretty_log(
            "info",
            f"Message {message.id} does not mention any of the clan bank ids. Ignoring.",
        )
        return
    # Extract amount from the message content using regex
    amount = extract_any_pokecoins_amount(message.content)
    if (
        amount < MIN_DONATION_AMOUNT and member.id != KHY_USER_ID
    ):  # Kyra's donations can be any amount for testing
        pretty_log(
            "info",
            f"Extracted amount {amount} is less than minimum donation amount. Ignoring.",
        )
        return
    await process_donation(bot, member, amount, context="clan bank", message=message)


async def process_donation(
    bot: discord.Client,
    member: discord.Member,
    amount: int,
    context: str,
    message: discord.Message,
):

    # Fetch donation record
    donation_record = await fetch_donation_record(bot, member.id)
    old_total = donation_record["total_donations"] if donation_record else 0
    old_monthly = donation_record["monthly_donations"] if donation_record else 0
    new_total = old_total + amount
    new_monthly = old_monthly + amount

    # Upsert donation record
    await upsert_donation_record(bot, member.id, member.name, total_donations=new_total)

    # Update monthly donations
    await update_monthly_donations(bot, member.id, new_monthly)

    # Log the donation
    if context == "clan bank":
        title = "Clan Bank Donation"
        thumbnail_url = Thumbnails.clan_bank
    else:
        thumbnail_url = Thumbnails.clan_treasury
        title = "Clan Treasury Donation"

    amount_formatted = format_comma_pokecoins(amount)
    embed = discord.Embed(
        title=title,
        url=message.jump_url,
        description=(
            f"- **Member:** {member.mention}\n"
            f"- **Amount:** {amount_formatted}\n"
            f"- **New Total Donations:** {format_comma_pokecoins(new_total)}\n"
            f"- **New Monthly Donations:** {format_comma_pokecoins(new_monthly)}"
        ),
        color=DEFAULT_EMBED_COLOR,
        timestamp=datetime.now(),
    )
    embed = design_embed(embed=embed, user=member, thumbnail_url=thumbnail_url)
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await send_webhook(
            bot=bot,
            channel=log_channel,
            embed=embed,
        )
    # Check and update monthly donator status
    await check_monthly_and_update_donation_status(
        bot=bot,
        member=member,
    )
    pretty_log(
        "info",
        f"Processed donation of {amount} PokeCoins from member {member.name} (ID: {member.id}).",
    )
