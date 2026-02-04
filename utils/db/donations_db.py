import discord

from utils.logs.pretty_log import pretty_log

# SQL SCRIPT
"""CREATE TABLE donations (
    user_id BIGINT PRIMARY KEY,
    user_name VARCHAR(255),
    total_donations INT DEFAULT 0,
    monthly_donations INT DEFAULT 0,
    monthly_donator_streak INT DEFAULT 0,
    permanent_monthly_donator BOOLEAN DEFAULT FALSE
);"""


async def upsert_donation_record(
    bot: discord.Client, user_id: int, user_name: str, total_donations: int = 0
):
    """Insert or update a donation record for a user."""
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO donations (user_id, user_name, total_donations)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) DO UPDATE
                SET user_name = EXCLUDED.user_name,
                    total_donations = donations.total_donations + EXCLUDED.total_donations
                """,
                user_id,
                user_name,
                total_donations,
            )
            pretty_log(
                message=f"✅ Upserted donation record for user: {user_name} (ID: {user_id})",
                tag="db",
            )
    except Exception as e:
        pretty_log(
            message=f"❌ Failed to upsert donation record for user: {user_name} (ID: {user_id}): {e}",
            tag="error",
            include_trace=True,
        )


async def fetch_donation_record(bot: discord.Client, user_id: int):
    """Fetch a donation record for a user."""
    try:
        async with bot.pg_pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                SELECT * FROM donations WHERE user_id = $1
                """,
                user_id,
            )
            if record:
                pretty_log(
                    message=f"✅ Fetched donation record for user ID: {user_id}",
                    tag="db",
                )
                return dict(record)
            else:
                pretty_log(
                    message=f"ℹ️ No donation record found for user ID: {user_id}",
                    tag="db",
                )
                return None
    except Exception as e:
        pretty_log(
            message=f"❌ Failed to fetch donation record for user ID: {user_id}: {e}",
            tag="error",
            include_trace=True,
        )
        return None


async def update_total_donations(
    bot: discord.Client, user_id: int, total_donations: int
):
    """Update the total donations for a user."""
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE donations
                SET total_donations = $2
                WHERE user_id = $1
                """,
                user_id,
                total_donations,
            )
            pretty_log(
                message=f"✅ Updated total donations for user ID: {user_id} to {total_donations}",
                tag="db",
            )
    except Exception as e:
        pretty_log(
            message=f"❌ Failed to update total donations for user ID: {user_id}: {e}",
            tag="error",
            include_trace=True,
        )


async def update_monthly_donations(
    bot: discord.Client, user_id: int, monthly_donations: int
):
    """Update the monthly donations for a user."""
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE donations
                SET monthly_donations = $2
                WHERE user_id = $1
                """,
                user_id,
                monthly_donations,
            )
            pretty_log(
                message=f"✅ Updated monthly donations for user ID: {user_id} to {monthly_donations}",
                tag="db",
            )
    except Exception as e:
        pretty_log(
            message=f"❌ Failed to update monthly donations for user ID: {user_id}: {e}",
            tag="error",
        )


async def increment_monthly_donator_streak(bot: discord.Client, user_id: int):
    """Increment the monthly donator streak for a user."""
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE donations
                SET monthly_donator_streak = monthly_donator_streak + 1
                WHERE user_id = $1
                """,
                user_id,
            )
            pretty_log(
                message=f"✅ Incremented monthly donator streak for user ID: {user_id}",
                tag="db",
            )
    except Exception as e:
        pretty_log(
            message=f"❌ Failed to increment monthly donator streak for user ID: {user_id}: {e}",
            tag="error",
            include_trace=True,
        )


async def set_permanent_monthly_donator(
    bot: discord.Client, user_id: int, is_permanent: bool
):
    """Set the permanent monthly donator status for a user."""
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE donations
                SET permanent_monthly_donator = $2
                WHERE user_id = $1
                """,
                user_id,
                is_permanent,
            )
            pretty_log(
                message=f"✅ Set permanent monthly donator status for user ID: {user_id} to {is_permanent}",
                tag="db",
            )
    except Exception as e:
        pretty_log(
            message=f"❌ Failed to set permanent monthly donator status for user ID: {user_id}: {e}",
            tag="error",
            include_trace=True,
        )


async def reset_monthly_donations(bot: discord.Client):
    """Reset monthly donations for all users."""
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE donations
                SET monthly_donations = 0
                """
            )
            pretty_log(
                message="✅ Reset monthly donations and updated donator streaks for all users",
                tag="db",
            )
    except Exception as e:
        pretty_log(
            message=f"❌ Failed to reset monthly donations: {e}",
            tag="error",
            include_trace=True,
        )
