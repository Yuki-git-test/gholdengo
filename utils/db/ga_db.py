import discord

from utils.logs.pretty_log import pretty_log

# SQL SCRIPT
"""CREATE TABLE giveaways (
    giveaway_id SERIAL,
    message_id BIGINT,
    channel_id BIGINT,
    host_id BIGINT,
    host_name TEXT,
    ends_at BIGINT,
    max_winners INT,
    prize TEXT,
    ended BOOLEAN DEFAULT FALSE,
    image_link TEXT,
    thumbnail_link TEXT,
    thread_id BIGINT,
    PRIMARY KEY (giveaway_id, message_id)
);"""
async def fetch_all_giveaways(bot: discord.Client):
    """Fetch all giveaways with ended = false."""
    try:
        async with bot.pg_pool.acquire() as conn:
            records = await conn.fetch(
                """
                SELECT * FROM giveaways
                WHERE ended = FALSE
                """,
            )
            giveaways = [record for record in records]
            pretty_log(
                "info",
                f"Fetched {len(giveaways)} active giveaways",
                label="Giveaway DB",
            )
            return giveaways
    except Exception as e:
        pretty_log(
            "error",
            f"Error fetching active giveaways: {e}",
            label="Giveaway DB",
            include_trace=True,
        )
        return []

async def upsert_giveaway(
    bot: discord.Client,
    message_id: int,
    channel_id: int,
    host_id: int,
    host_name: str,
    ends_at: int,
    max_winners: int,
    prize: str,
    ended: bool = False,
    image_link: str = None,
    giveaway_type: str = None,
    thread_id: int = None,
):
    """Upsert a giveaway record, and return the giveaway ID."""
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO giveaways (message_id, channel_id, host_id, host_name, ends_at, max_winners, prize, ended, image_link, giveaway_type, thread_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (message_id) DO UPDATE
                SET channel_id = EXCLUDED.channel_id,
                    host_id = EXCLUDED.host_id,
                    host_name = EXCLUDED.host_name,
                    ends_at = EXCLUDED.ends_at,
                    max_winners = EXCLUDED.max_winners,
                    prize = EXCLUDED.prize,
                    ended = EXCLUDED.ended,
                    image_link = EXCLUDED.image_link,
                    giveaway_type = EXCLUDED.giveaway_type,
                    thread_id = EXCLUDED.thread_id;
                """,
                message_id,
                channel_id,
                host_id,
                host_name,
                ends_at,
                max_winners,
                prize,
                ended,
                image_link,
                giveaway_type,
                thread_id,
            )
            # Fetch giveaway_id after upsert
            record = await conn.fetchrow(
                """
                SELECT giveaway_id FROM giveaways WHERE message_id = $1
                """,
                message_id,
            )
            pretty_log(
                "info",
                f"Upserted giveaway with message ID {message_id} in channel ID {channel_id}",
                label="Giveaway DB",
            )
            return record["giveaway_id"] if record else None
    except Exception as e:
        pretty_log(
            "error",
            f"Error upserting giveaway with message ID {message_id} in channel ID {channel_id}: {e}",
            label="Giveaway DB",
            include_trace=True,
        )
        return None


async def update_giveaway_thread_id(
    bot: discord.Client, giveaway_id: int, thread_id: int
):
    """Update the thread ID for a giveaway."""
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE giveaways
                SET thread_id = $1
                WHERE giveaway_id = $2
                """,
                thread_id,
                giveaway_id,
            )
            pretty_log(
                "info",
                f"Updated thread ID {thread_id} for giveaway ID {giveaway_id}",
                label="Giveaway DB",
            )
    except Exception as e:
        pretty_log(
            "error",
            f"Error updating thread ID {thread_id} for giveaway ID {giveaway_id}: {e}",
            label="Giveaway DB",
            include_trace=True,
        )


async def update_giveaway_message_id(
    bot: discord.Client, giveaway_id: int, message_id: int
):
    """Update the message ID for a giveaway."""
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE giveaways
                SET message_id = $1
                WHERE giveaway_id = $2
                """,
                message_id,
                giveaway_id,
            )
            pretty_log(
                "info",
                f"Updated message ID {message_id} for giveaway ID {giveaway_id}",
                label="Giveaway DB",
            )
    except Exception as e:
        pretty_log(
            "error",
            f"Error updating message ID {message_id} for giveaway ID {giveaway_id}: {e}",
            label="Giveaway DB",
            include_trace=True,
        )


async def fetch_giveaway_id_by_message_id(bot: discord.Client, message_id: int):
    """Fetch giveaway ID by message ID."""
    try:
        async with bot.pg_pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                SELECT giveaway_id FROM giveaways
                WHERE message_id = $1
                """,
                message_id,
            )
            if record:
                pretty_log(
                    "info",
                    f"Fetched giveaway ID {record['giveaway_id']} for message ID {message_id}",
                    label="Giveaway DB",
                )
                return record["giveaway_id"]
            else:
                pretty_log(
                    "info",
                    f"No giveaway found for message ID {message_id}",
                    label="Giveaway DB",
                )
                return None
    except Exception as e:
        pretty_log(
            "error",
            f"Error fetching giveaway ID for message ID {message_id}: {e}",
            label="Giveaway DB",
            include_trace=True,
        )
        return None


async def fetch_giveaway_row_by_message_id(bot: discord.Client, message_id: int):
    try:
        async with bot.pg_pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                SELECT * FROM giveaways
                WHERE message_id = $1
                """,
                message_id,
            )
            if record:
                pretty_log(
                    "info",
                    f"Fetched giveaway row for message ID {message_id}: giveaway ID {record['giveaway_id']}",
                    label="Giveaway Entry DB",
                )
                return record
            else:
                pretty_log(
                    "info",
                    f"No giveaway row found for message ID {message_id}",
                    label="Giveaway Entry DB",
                )
                return None
    except Exception as e:
        pretty_log(
            "error",
            f"Error fetching giveaway row for message ID {message_id}: {e}",
            label="Giveaway Entry DB",
            include_trace=True,
        )
        return None


async def mark_giveaway_as_ended(bot: discord.Client, giveaway_id: int):
    """Mark a giveaway as ended."""
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE giveaways
                SET ended = TRUE
                WHERE giveaway_id = $1
                """,
                giveaway_id,
            )
            pretty_log(
                "info",
                f"Marked giveaway ID {giveaway_id} as ended",
                label="Giveaway DB",
            )
    except Exception as e:
        pretty_log(
            "error",
            f"Error marking giveaway ID {giveaway_id} as ended: {e}",
            label="Giveaway DB",
            include_trace=True,
        )


async def delete_giveaway(bot: discord.Client, giveaway_id: int):
    """Delete a giveaway record."""
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM giveaways
                WHERE giveaway_id = $1
                """,
                giveaway_id,
            )
            pretty_log(
                "info",
                f"Deleted giveaway ID {giveaway_id}",
                label="Giveaway DB",
            )
    except Exception as e:
        pretty_log(
            "error",
            f"Error deleting giveaway ID {giveaway_id}: {e}",
            label="Giveaway DB",
            include_trace=True,
        )


async def fetch_giveaway_by_id(bot: discord.Client, giveaway_id: int):
    """Fetch a giveaway record by giveaway ID."""
    try:
        async with bot.pg_pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                SELECT * FROM giveaways
                WHERE giveaway_id = $1
                """,
                giveaway_id,
            )
            if record:
                pretty_log(
                    "info",
                    f"Fetched giveaway ID {giveaway_id} with message ID {record['message_id']}",
                    label="Giveaway DB",
                )
                return record
            else:
                pretty_log(
                    "info",
                    f"No giveaway found for giveaway ID {giveaway_id}",
                    label="Giveaway DB",
                )
                return None
    except Exception as e:
        pretty_log(
            "error",
            f"Error fetching giveaway for giveaway ID {giveaway_id}: {e}",
            label="Giveaway DB",
            include_trace=True,
        )
        return None


async def fetch_all_due_giveaways(bot: discord.Client):
    """ "Fetch all due giveaways that have not ended yet with the ended flag set to false. then update the ended flag to true for all the fetched giveaways."""
    try:
        async with bot.pg_pool.acquire() as conn:
            records = await conn.fetch(
                """
                SELECT * FROM giveaways
                WHERE ends_at <= EXTRACT(EPOCH FROM NOW()) AND ended = FALSE
                """,
            )
            giveaways = [record for record in records]
            if giveaways:
                giveaway_ids = [record["giveaway_id"] for record in giveaways]
                await conn.execute(
                    f"""
                    UPDATE giveaways
                    SET ended = TRUE
                    WHERE giveaway_id = ANY($1)
                    """,
                    giveaway_ids,
                )
                pretty_log(
                    "info",
                    f"Marked {len(giveaway_ids)} due giveaways as ended",
                    label="Giveaway DB",
                )
            """pretty_log(
                "info",
                f"Fetched {len(giveaways)} due giveaways that have not ended yet",
                label="Giveaway DB",
            )"""
            return giveaways
    except Exception as e:
        pretty_log(
            "error",
            f"Error fetching due giveaways: {e}",
            label="Giveaway DB",
            include_trace=True,
        )
        return []


async def delete_giveaways_which_ended_a_week_ago(bot: discord.Client):
    """Delete giveaways that ended more than a week ago."""
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM giveaways
                WHERE ended = TRUE AND ends_at <= EXTRACT(EPOCH FROM NOW()) - 604800
                """,
            )
            """pretty_log(
                "info",
                f"Deleted giveaways that ended more than a week ago",
                label="Giveaway DB",
            )"""
    except Exception as e:
        pretty_log(
            "error",
            f"Error deleting old ended giveaways: {e}",
            label="Giveaway DB",
            include_trace=True,
        )

async def fetch_all_giveaway_by_type(bot: discord.Client, giveaway_type: str):
    """Fetch all giveaways of a specific type and ended = false."""
    try:
        async with bot.pg_pool.acquire() as conn:
            records = await conn.fetch(
                """
                SELECT * FROM giveaways
                WHERE giveaway_type = $1 AND ended = FALSE
                """,
                giveaway_type,
            )
            giveaways = [record for record in records]
            pretty_log(
                "info",
                f"Fetched {len(giveaways)} active giveaways of type {giveaway_type}",
                label="Giveaway DB",
            )
            return giveaways
    except Exception as e:
        pretty_log(
            "error",
            f"Error fetching active giveaways of type {giveaway_type}: {e}",
            label="Giveaway DB",
            include_trace=True,
        )
        return []