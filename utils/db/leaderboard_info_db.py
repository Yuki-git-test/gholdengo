import discord

from utils.logs.pretty_log import pretty_log


async def upsert_leaderboard_msg_id(bot, message_id: int, channel: discord.TextChannel):
    """
    Upsert the trophy leaderboard message ID.
    """
    channel_name = channel.name
    channel_id = channel.id
    async with bot.pg_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO current_trophy_leaderboard (message_id, channel_id, channel_name)
            VALUES ($1, $2, $3)
            ON CONFLICT (message_id) DO UPDATE
            SET channel_id = EXCLUDED.channel_id,
                channel_name = EXCLUDED.channel_name;
            """,
            message_id,
            channel_id,
            channel_name,
        )
        pretty_log(
            "info",
            f"Upserted leaderboard message ID: {message_id} in channel {channel_name} ({channel_id})",
            label="Trophy Leaderboard DB",
        )

async def fetch_leaderboard_msg_id(bot, channel: discord.TextChannel):
    """
    Fetch the trophy leaderboard message ID for a given channel.
    """
    async with bot.pg_pool.acquire() as conn:
        record = await conn.fetchrow(
            """
            SELECT message_id FROM current_trophy_leaderboard
            WHERE channel_id = $1
            """,
            channel.id,
        )
        if record:
            pretty_log(
                "info",
                f"Fetched leaderboard message ID: {record['message_id']} for channel {channel.name} ({channel.id})",
                label="Trophy Leaderboard DB",
            )
            return record["message_id"]
        else:
            pretty_log(
                "warning",
                f"No leaderboard message ID found for channel {channel.name} ({channel.id})",
                label="Trophy Leaderboard DB",
            )
            return None

async def delete_leaderboard_msg_id(bot, channel: discord.TextChannel):
    """
    Delete the trophy leaderboard message ID for a given channel.
    """
    async with bot.pg_pool.acquire() as conn:
        await conn.execute(
            """
            DELETE FROM current_trophy_leaderboard
            WHERE channel_id = $1
            """,
            channel.id,
        )
        pretty_log(
            "info",
            f"Deleted leaderboard message ID for channel {channel.name} ({channel.id})",
            label="Trophy Leaderboard DB",
        )