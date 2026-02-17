import discord

from utils.cache.cache_list import active_lottery_thread_ids
from utils.logs.pretty_log import pretty_log

# sql script
"""CREATE TABLE lottery (
    lottery_id SERIAL PRIMARY KEY,
    prize VARCHAR(255),
    max_tickets BIGINT,
    ticket_price BIGINT,
    base_pot BIGINT,
    ends_on BIGINT,
    ended BOOLEAN,
    message_id BIGINT,
    thread_id BIGINT,
    image_link VARCHAR(512),
    host_id BIGINT,
    host_name VARCHAR(255),
    total_tickets bigint,
);"""

async def get_total_tickets(bot: discord.Client, lottery_id: int) -> int:
    """Fetch the total tickets sold for a lottery."""
    try:
        async with bot.pg_pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT total_tickets
                FROM lottery
                WHERE lottery_id = $1;
                """,
                lottery_id,
            )
            return result["total_tickets"] if result else 0
    except Exception as e:
        pretty_log(message=f"Error fetching total tickets: {e}", tag="error")
        return 0
    
async def upsert_lottery(
    bot: discord.Client,
    prize: str,
    host_id: int,
    host_name: str,
    max_tickets: int,
    ticket_price: int,
    base_pot: int,
    ends_on: int,
    ended: bool,
    message_id: int,
    thread_id: int,
    channel_id: int,
    image_link: str,
    total_tickets: int,
) -> int | None:
    try:
        async with bot.pg_pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                INSERT INTO lottery (prize, host_id, host_name, max_tickets, ticket_price, base_pot, ends_on, ended, message_id, thread_id, channel_id, image_link, total_tickets)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                RETURNING lottery_id;
                """,
                prize,
                host_id,
                host_name,
                max_tickets,
                ticket_price,
                base_pot,
                ends_on,
                ended,
                message_id,
                thread_id,
                channel_id,
                image_link,
                total_tickets,
            )
            return result["lottery_id"] if result else None
    except Exception as e:
        pretty_log(message=f"Error upserting lottery: {e}", tag="error")
        return None


async def update_message_and_thread(
    bot: discord.Client, lottery_id: int, message_id: int, thread_id: int
):
    """Update the message ID and thread ID for a lottery."""
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE lottery
                SET message_id = $1, thread_id = $2
                WHERE lottery_id = $3;
                """,
                message_id,
                thread_id,
                lottery_id,
            )
            # add to cache too
            active_lottery_thread_ids.add(thread_id)
    except Exception as e:
        pretty_log(message=f"Error updating message and thread IDs: {e}", tag="error")


async def update_total_tickets(
    bot: discord.Client, lottery_id: int, total_tickets: int
):
    """Update the total tickets sold for a lottery."""

    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE lottery
                SET total_tickets = $1
                WHERE lottery_id = $2;
                """,
                total_tickets,
                lottery_id,
            )
    except Exception as e:
        pretty_log(message=f"Error updating total tickets: {e}", tag="error")


async def mark_lottery_ended(bot: discord.Client, lottery_id: int):
    """Mark a lottery as ended in the database."""
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE lottery
                SET ended = TRUE
                WHERE lottery_id = $1;
                """,
                lottery_id,
            )
    except Exception as e:
        pretty_log(message=f"Error marking lottery as ended: {e}", tag="error")


async def get_lottery_id_by_thread_id(
    bot: discord.Client, thread_id: int
) -> int | None:
    """Fetch the lottery ID associated with a given thread ID."""
    try:
        async with bot.pg_pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT lottery_id
                FROM lottery
                WHERE thread_id = $1;
                """,
                thread_id,
            )
            return result["lottery_id"] if result else None
    except Exception as e:
        pretty_log(message=f"Error fetching lottery ID by thread ID: {e}", tag="error")
        return None

async def add_to_total_tickets(bot: discord.Client, lottery_id: int, tickets_to_add: int):
    """Add a certain number of tickets to the total tickets sold for a lottery."""
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE lottery
                SET total_tickets = total_tickets + $1
                WHERE lottery_id = $2;
                """,
                tickets_to_add,
                lottery_id,
            )
    except Exception as e:
        pretty_log(message=f"Error adding to total tickets: {e}", tag="error")

async def get_lottery_info_by_thread_id(
    bot: discord.Client, thread_id: int
) -> dict | None:
    """Fetch the lottery info associated with a given thread ID."""
    try:
        async with bot.pg_pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT *
                FROM lottery
                WHERE thread_id = $1;
                """,
                thread_id,
            )
            return dict(result) if result else None
    except Exception as e:
        pretty_log(
            message=f"Error fetching lottery info by thread ID: {e}", tag="error"
        )
        return None


async def fetch_active_lotteries(bot: discord.Client) -> list[dict]:
    """Fetch all active (not ended) lotteries from the database."""
    try:
        async with bot.pg_pool.acquire() as conn:
            results = await conn.fetch(
                """
                SELECT *
                FROM lottery
                WHERE ended = FALSE;
                """
            )
            return [dict(record) for record in results]
    except Exception as e:
        pretty_log(message=f"Error fetching active lotteries: {e}", tag="error")
        return []


async def fetch_all_due_lotteries(bot: discord.Client):
    """Fetch all lotteries that have ended but are not marked as ended in the database."""
    try:
        async with bot.pg_pool.acquire() as conn:
            results = await conn.fetch(
                """
                SELECT *
                FROM lottery
                WHERE ended = FALSE AND ends_on <= EXTRACT(EPOCH FROM NOW());
                """
            )
            return [dict(record) for record in results]
    except Exception as e:
        pretty_log(message=f"Error fetching due lotteries: {e}", tag="error")
        return []


async def delete_lottery(bot: discord.Client, lottery_id: int):
    """Delete a lottery from the database and removes the thread id from the cache."""
    try:
        async with bot.pg_pool.acquire() as conn:
            # Fetch thread_id before deleting
            result = await conn.fetchrow(
                "SELECT thread_id FROM lottery WHERE lottery_id = $1;",
                lottery_id,
            )
            thread_id = result["thread_id"] if result else None

            # Delete the lottery
            await conn.execute(
                "DELETE FROM lottery WHERE lottery_id = $1;",
                lottery_id,
            )

            # Remove from cache if found
            if thread_id is not None:
                active_lottery_thread_ids.discard(thread_id)
    except Exception as e:
        pretty_log(message=f"Error deleting lottery: {e}", tag="error")


async def load_active_lotteries_into_cache(bot: discord.Client):
    """Load active lottery thread IDs into the in-memory cache on startup."""
    active_lotteries = await fetch_active_lotteries(bot)
    for lottery in active_lotteries:
        thread_id = lottery["thread_id"]
        active_lottery_thread_ids.add(thread_id)
    pretty_log(
        message=f"✅ Loaded {len(active_lottery_thread_ids)} active lottery thread IDs into cache",
        tag="ready",
    )

async def fetch_lottery_info_by_lottery_id(bot: discord.Client, lottery_id: int) -> dict | None:
    """Fetch the lottery info associated with a given lottery ID."""
    try:
        async with bot.pg_pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT *
                FROM lottery
                WHERE lottery_id = $1;
                """,
                lottery_id,
            )
            return dict(result) if result else None
    except Exception as e:
        pretty_log(
            message=f"Error fetching lottery info by lottery ID: {e}", tag="error"
        )
        return None