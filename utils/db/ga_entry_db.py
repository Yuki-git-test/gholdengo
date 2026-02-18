import discord

from utils.logs.pretty_log import pretty_log

# SQL Script
"""CREATE TABLE giveaway_entries (
    giveaway_id INT,
    user_id BIGINT,
    user_name TEXT,
    entry_count INT,
    joined_at BIGINT,
    PRIMARY KEY (giveaway_id, user_id)
);

-- Migration script to add joined_at column
ALTER TABLE giveaway_entries ADD COLUMN joined_at BIGINT;
"""


async def upsert_ga_entry(
    bot: discord.Client,
    giveaway_id: int,
    user_id: int,
    user_name: str,
    entry_count: int = 1,
    joined_at: int = None,
):
    try:
        async with bot.pg_pool.acquire() as conn:
            if joined_at is None:
                import time

                joined_at = int(time.time())
            await conn.execute(
                """
                INSERT INTO giveaway_entries (giveaway_id, user_id, user_name, entry_count, joined_at)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (giveaway_id, user_id) DO UPDATE
                SET entry_count = giveaway_entries.entry_count + EXCLUDED.entry_count,
                    user_name = EXCLUDED.user_name,
                    joined_at = EXCLUDED.joined_at;
                """,
                giveaway_id,
                user_id,
                user_name,
                entry_count,
                joined_at,
            )
            pretty_log(
                "info",
                f"Upserted giveaway entry for user {user_name} ({user_id}) in giveaway {giveaway_id} with {entry_count} entries (joined_at={joined_at})",
                label="Giveaway Entry DB",
            )
    except Exception as e:
        pretty_log(
            "error",
            f"Error upserting giveaway entry for user {user_name} ({user_id}) in giveaway {giveaway_id}: {e}",
            label="Giveaway Entry DB",
            include_trace=True,
        )


async def fetch_entries_by_giveaway(bot: discord.Client, giveaway_id: int):
    try:
        async with bot.pg_pool.acquire() as conn:
            records = await conn.fetch(
                """
                SELECT user_id, user_name, entry_count, joined_at FROM giveaway_entries
                WHERE giveaway_id = $1
                """,
                giveaway_id,
            )
            entries = [
                {
                    "user_id": record["user_id"],
                    "user_name": record["user_name"],
                    "entry_count": record["entry_count"],
                    "joined_at": record["joined_at"],
                }
                for record in records
            ]
            pretty_log(
                "info",
                f"Fetched {len(entries)} entries for giveaway {giveaway_id}",
                label="Giveaway Entry DB",
            )
            return entries
    except Exception as e:
        pretty_log(
            "error",
            f"Error fetching entries for giveaway {giveaway_id}: {e}",
            label="Giveaway Entry DB",
            include_trace=True,
        )
        return []


async def fetch_all_user_ga_entries(bot: discord.Client, user_id: int):
    try:
        async with bot.pg_pool.acquire() as conn:
            records = await conn.fetch(
                """
                SELECT giveaway_id, entry_count, joined_at FROM giveaway_entries
                WHERE user_id = $1
                """,
                user_id,
            )
            entries = [
                {
                    "giveaway_id": record["giveaway_id"],
                    "entry_count": record["entry_count"],
                    "joined_at": record["joined_at"],
                }
                for record in records
            ]
            pretty_log(
                "info",
                f"Fetched {len(entries)} giveaway entries for user ID {user_id}",
                label="Giveaway Entry DB",
            )
            return entries
    except Exception as e:
        pretty_log(
            "error",
            f"Error fetching giveaway entries for user ID {user_id}: {e}",
            label="Giveaway Entry DB",
            include_trace=True,
        )
        return []


async def fetch_ga_entry(bot: discord.Client, giveaway_id: int, user_id: int):
    try:
        async with bot.pg_pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                SELECT entry_count, joined_at FROM giveaway_entries
                WHERE giveaway_id = $1 AND user_id = $2
                """,
                giveaway_id,
                user_id,
            )
            if record:
                pretty_log(
                    "info",
                    f"Fetched giveaway entry for user ID {user_id} in giveaway {giveaway_id}: {record['entry_count']} entries (joined_at={record['joined_at']})",
                    label="Giveaway Entry DB",
                )
                return record["entry_count"], record["joined_at"]
            else:
                pretty_log(
                    "info",
                    f"No giveaway entry found for user ID {user_id} in giveaway {giveaway_id}",
                    label="Giveaway Entry DB",
                )
                return 0
    except Exception as e:
        pretty_log(
            "error",
            f"Error fetching giveaway entry for user ID {user_id} in giveaway {giveaway_id}: {e}",
            label="Giveaway Entry DB",
            include_trace=True,
        )
        return 0


async def fetch_all_ga_entries_for_a_ga(bot: discord.Client, giveaway_id: int):
    try:
        async with bot.pg_pool.acquire() as conn:
            records = await conn.fetch(
                """
                SELECT user_id, user_name, entry_count, joined_at FROM giveaway_entries
                WHERE giveaway_id = $1
                """,
                giveaway_id,
            )
            entries = [
                {
                    "user_id": record["user_id"],
                    "user_name": record["user_name"],
                    "entry_count": record["entry_count"],
                    "joined_at": record["joined_at"],
                }
                for record in records
            ]
            pretty_log(
                "info",
                f"Fetched {len(entries)} giveaway entries for giveaway {giveaway_id}",
                label="Giveaway Entry DB",
            )
            return entries
    except Exception as e:
        pretty_log(
            "error",
            f"Error fetching giveaway entries for giveaway {giveaway_id}: {e}",
            label="Giveaway Entry DB",
            include_trace=True,
        )
        return []


async def update_ga_entry(
    bot: discord.Client, giveaway_id: int, user_id: int, new_entry_count: int
):
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE giveaway_entries
                SET entry_count = $1
                WHERE giveaway_id = $2 AND user_id = $3
                """,
                new_entry_count,
                giveaway_id,
                user_id,
            )
            pretty_log(
                "info",
                f"Updated giveaway entry for user ID {user_id} in giveaway {giveaway_id} to {new_entry_count} entries",
                label="Giveaway Entry DB",
            )
    except Exception as e:
        pretty_log(
            "error",
            f"Error updating giveaway entry for user ID {user_id} in giveaway {giveaway_id}: {e}",
            label="Giveaway Entry DB",
            include_trace=True,
        )


async def update_all_ga_entries_for_a_user(
    bot: discord.Client, user_id: int, new_entry_count: int
):
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE giveaway_entries
                SET entry_count = $1
                WHERE user_id = $2
                """,
                new_entry_count,
                user_id,
            )
            pretty_log(
                "info",
                f"Updated all giveaway entries for user ID {user_id} to {new_entry_count} entries",
                label="Giveaway Entry DB",
            )
    except Exception as e:
        pretty_log(
            "error",
            f"Error updating giveaway entries for user ID {user_id}: {e}",
            label="Giveaway Entry DB",
            include_trace=True,
        )


async def delete_all_user_ga_entries(bot: discord.Client, user_id: int):
    """Removes all giveaway entries for a user."""
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM giveaway_entries
                WHERE user_id = $1
                """,
                user_id,
            )
            pretty_log(
                "info",
                f"Deleted all giveaway entries for user ID {user_id}",
                label="Giveaway Entry DB",
            )
    except Exception as e:
        pretty_log(
            "error",
            f"Error deleting giveaway entries for user ID {user_id}: {e}",
            label="Giveaway Entry DB",
            include_trace=True,
        )


async def delete_ga_entry(bot: discord.Client, giveaway_id: int, user_id: int):
    """Removes a user's giveaway row."""
    
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM giveaway_entries
                WHERE giveaway_id = $1 AND user_id = $2
                """,
                giveaway_id,
                user_id,
            )
            pretty_log(
                "info",
                f"Deleted giveaway entry for user ID {user_id} in giveaway {giveaway_id}",
                label="Giveaway Entry DB",
            )
    except Exception as e:
        pretty_log(
            "error",
            f"Error deleting giveaway entry for user ID {user_id} in giveaway {giveaway_id}: {e}",
            label="Giveaway Entry DB",
            include_trace=True,
        )


async def delete_all_user_ga_rows(bot: discord.Client, user_id: int):
    """Removes all giveaway rows for a user and returns a list of giveaway ids that user got removed from."""
    try:
        async with bot.pg_pool.acquire() as conn:
            records = await conn.fetch(
                """
                SELECT giveaway_id FROM giveaway_entries
                WHERE user_id = $1
                """,
                user_id,
            )
            giveaway_ids = [record["giveaway_id"] for record in records]
            await conn.execute(
                """
                DELETE FROM giveaway_entries
                WHERE user_id = $1
                """,
                user_id,
            )
            pretty_log(
                "info",
                f"Deleted giveaway entries for user ID {user_id} in giveaways {giveaway_ids}",
                label="Giveaway Entry DB",
            )
            return giveaway_ids
    except Exception as e:
        pretty_log(
            "error",
            f"Error deleting giveaway entries for user ID {user_id}: {e}",
            label="Giveaway Entry DB",
            include_trace=True,
        )
        return []
async def fetch_all_user_ga_rows(bot: discord.Client, user_id: int):
    """Fetches all giveaway rows for a user and returns a list of giveaway ids that user is entered in."""
    try:
        async with bot.pg_pool.acquire() as conn:
            records = await conn.fetch(
                """
                SELECT giveaway_id FROM giveaway_entries
                WHERE user_id = $1
                """,
                user_id,
            )
            giveaway_ids = [record["giveaway_id"] for record in records]
            pretty_log(
                "info",
                f"Fetched giveaway entries for user ID {user_id} in giveaways {giveaway_ids}",
                label="Giveaway Entry DB",
            )
            return giveaway_ids
    except Exception as e:
        pretty_log(
            "error",
            f"Error fetching giveaway entries for user ID {user_id}: {e}",
            label="Giveaway Entry DB",
            include_trace=True,
        )
        return []

