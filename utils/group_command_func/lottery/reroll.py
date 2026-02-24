import discord

from utils.db.lottery import (
    fetch_lottery_info_by_lottery_id,
    get_lottery_id_by_message_id,
)
from utils.db.lottery_entries import fetch_all_entries_for_a_lottery
from utils.listener_func.buy_lottery_ticket_listener import end_lottery
from utils.logs.pretty_log import pretty_log
from utils.visuals.pretty_defer import pretty_defer


async def reroll_lottery_func(
    bot: discord.Client,
    interaction: discord.Interaction,
    message_id: int,
):
    """Reroll the lottery with the given message_id."""

    # Defer
    loader = await pretty_defer(
        interaction=interaction, content="Rerolling the lottery...", ephemeral=False
    )
    # Check if lottery is active
    lottery_id = await get_lottery_id_by_message_id(bot, message_id)
    if not lottery_id:
        pretty_log(
            "error",
            f"No active lottery found for message ID {message_id}",
            label="Reroll Lottery Handler",
        )
        await loader.error("No active lottery found with that message ID.")
        return

    # Get the lottery
    lottery_info = await fetch_lottery_info_by_lottery_id(bot, lottery_id)
    if not lottery_info:
        pretty_log(
            "error",
            f"Lottery ID {lottery_id} not found for message ID {message_id}",
            label="Reroll Lottery Handler",
        )
        await loader.error("Lottery not found.")
        return

    # Check if lottery still has entries for reroll
    entries = await fetch_all_entries_for_a_lottery(bot, lottery_id)
    if not entries:
        pretty_log(
            "error",
            f"No entries found for lottery ID {lottery_id}",
            label="Reroll Lottery Handler",
        )
        await loader.error(
            content="No entries found for this lottery. Cannot reroll.",
        )
        return

    try:
        await end_lottery(bot, lottery_id, context="lottery_reroll")
        await loader.success(content="Lottery rerolled successfully!")
    except Exception as e:
        pretty_log(
            "error",
            f"Error processing lottery reroll for message ID {message_id}: {e}",
        )
        await loader.error("An error occurred while rerolling the lottery.")
