import discord

from utils.logs.pretty_log import pretty_log

# SQL SCRIPT
"""CREATE TABLE lottery_entries (
    lottery_id INT,
    user_id BIGINT,
    user_name VARCHAR(255),
    entries BIGINT,
    PRIMARY KEY (lottery_id, user_id),
    FOREIGN KEY (lottery_id) REFERENCES lottery(lottery_id) ON DELETE CASCADE
);"""

async def upsert_lottery_entry(
    bot: discord.Client,
    lottery_id: int,
    user_id: int,
    user_name: str,
    entries: int,
):
    """Insert or update a lottery entry in the database."""
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO lottery_entries (lottery_id, user_id, user_name, entries)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (lottery_id, user_id) DO UPDATE SET
                    user_name = EXCLUDED.user_name,
                    entries = EXCLUDED.entries;
                """,
                lottery_id,
                user_id,
                user_name,
                entries,
            )
    except Exception as e:
        pretty_log(message=f"Error upserting lottery entry: {e}", tag="error")

async def delete_lottery_entry(bot: discord.Client, lottery_id: int, user_id: int):
    """Delete a lottery entry from the database."""
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM lottery_entries
                WHERE lottery_id = $1 AND user_id = $2;
                """,
                lottery_id,
                user_id,
            )
    except Exception as e:
        pretty_log(message=f"Error deleting lottery entry: {e}", tag="error")

async def fetch_all_entries_for_lottery(bot: discord.Client, lottery_id: int) -> list[dict]:
    """Fetch all entries for a specific lottery."""
    try:
        async with bot.pg_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT user_id, user_name, entries
                FROM lottery_entries
                WHERE lottery_id = $1;
                """,
                lottery_id,
            )
            return [dict(row) for row in rows]
    except Exception as e:
        pretty_log(message=f"Error fetching lottery entries: {e}", tag="error")
        return []

async def update_lottery_entry(bot: discord.Client, lottery_id: int, user_id: int, entries: int):
    """Update the number of entries for a specific lottery entry."""
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE lottery_entries
                SET entries = $1
                WHERE lottery_id = $2 AND user_id = $3;
                """,
                entries,
                lottery_id,
                user_id,
            )
    except Exception as e:
        pretty_log(message=f"Error updating lottery entry: {e}", tag="error")
async def add_tickets_to_entry(bot: discord.Client, lottery_id: int, user_id: int, tickets_to_add: int):
    """Add a certain number of tickets to a user's lottery entry."""
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE lottery_entries
                SET entries = entries + $1
                WHERE lottery_id = $2 AND user_id = $3;
                """,
                tickets_to_add,
                lottery_id,
                user_id,
            )
    except Exception as e:
        pretty_log(message=f"Error adding tickets to lottery entry: {e}", tag="error")
        
async def fetch_lottery_entry(bot: discord.Client, lottery_id: int, user_id: int) -> dict | None:
    """Fetch a specific lottery entry for a user."""
    try:
        async with bot.pg_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT user_id, user_name, entries
                FROM lottery_entries
                WHERE lottery_id = $1 AND user_id = $2;
                """,
                lottery_id,
                user_id,
            )
            return dict(row) if row else None
    except Exception as e:
        pretty_log(message=f"Error fetching lottery entry: {e}", tag="error")
        return None

async def fetch_user_all_lottery_entries(bot: discord.Client, user_id: int) -> list[dict]:
    """Fetch all lottery entries for a specific user across all lotteries."""
    try:
        async with bot.pg_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT lottery_id, user_name, entries
                FROM lottery_entries
                WHERE user_id = $1;
                """,
                user_id,
            )
            return [dict(row) for row in rows]
    except Exception as e:
        pretty_log(message=f"Error fetching user's lottery entries: {e}", tag="error")
        return []

async def fetch_all_entries_for_a_lottery(bot: discord.Client, lottery_id: int) -> list[dict]:
    """Fetch all entries for a specific lottery."""
    try:
        async with bot.pg_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT user_id, user_name, entries
                FROM lottery_entries
                WHERE lottery_id = $1;
                """,
                lottery_id,
            )
            return [dict(row) for row in rows]
    except Exception as e:
        pretty_log(message=f"Error fetching lottery entries: {e}", tag="error")
        return []

async def user_has_lottery_entry(bot: discord.Client, lottery_id: int, user_id: int) -> bool:
    """Check if a user has an entry in a specific lottery."""
    try:
        async with bot.pg_pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT 1
                FROM lottery_entries
                WHERE lottery_id = $1 AND user_id = $2;
                """,
                lottery_id,
                user_id,
            )
            return bool(result)
    except Exception as e:
        pretty_log(message=f"Error checking lottery entry existence: {e}", tag="error")
        return False

