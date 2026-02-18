import discord


from utils.cache.cache_list import processing_end_lottery_ids
from utils.db.lottery import (
    delete_lotteries_which_ended_a_week_ago,
    fetch_all_due_lotteries,
)
from utils.listener_func.buy_lottery_ticket_listener import end_lottery
from utils.logs.pretty_log import pretty_log


async def lottery_end_checker(bot: discord.Client):
    """Checks for lottories that have ended and processes them, and deletes lottories that ended over a week ago."""
    await delete_lotteries_which_ended_a_week_ago(bot)
    due_lottories = await fetch_all_due_lotteries(bot)
    if not due_lottories:
        return

    for lottery in due_lottories:
        lottery_id = lottery["lottery_id"]

        try:
            await end_lottery(bot, lottery_id)
        except Exception as e:
            pretty_log(
                "error",
                f"Error processing giveaway end for message ID {lottery_id}: {e}",
            )
            continue  # Continue processing other giveaways even if one fails
