import discord

from utils.db.lottery import is_lottery_active
from utils.db.lottery_entries import fetch_all_entries_for_a_lottery
from utils.listener_func.buy_lottery_ticket_listener import end_lottery
from utils.logs.pretty_log import pretty_log
from utils.visuals.pretty_defer import pretty_defer


async def reroll_lottery_func(
    bot: discord.Client,
    interaction: discord.Interaction,
    message_id: int,
):
    """Ends the lottery with the given message_id."""

    # Defer
    loader = await pretty_defer(
        interaction=interaction, content="Rerolling the lottery...", ephemeral=False
    )
    # Check if lottery is active
    lottery_info = is_lottery_active(bot, message_id)
    if not lottery_info:
        await loader.error("This lottery has already ended or does not exist.")
        return

    # Get the lottery
    lottery_id = lottery_info["lottery_id"]

    # Check if lottery still has entries for reroll
    try:
        await end_lottery(bot, lottery_id)
        await loader.success(content="Lottery ended successfully!")
    except Exception as e:
        pretty_log(
            "error",
            f"Error processing lottery end for message ID {message_id}: {e}",
        )
        await loader.error("An error occurred while ending the lottery.")
