import discord

from utils.logs.pretty_log import pretty_log

#vna_members_cache: dict[int, dict] = {}
# Structure
# user_id: {
# "user_name": str,
# "pokemeow_name": str,
# "channel_id": int,
# "perks": str,
# "faction": str,
# }

# Fetch one member entry for a user
async def fetch_vna_member(bot, user: discord.Member):
    """
    Returns the VNA member entry for a user from the database.
    """
    user_id = user.id
    try:
        async with bot.pg_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT user_name, pokemeow_name, channel_id, perks, faction
                FROM vna_members
                WHERE user_id = $1
                """,
                user_id,
            )
            if row:
                pretty_log(
                    message=f"✅ Fetched VNA member entry for user: {user.name} (ID: {user_id})",
                    tag="db",
                )
                return dict(row)
            else:
                pretty_log(
                    message=f"ℹ️ No VNA member entry found for user: {user.name} (ID: {user_id})",
                    tag="db",
                )
                return None
    except Exception as e:
        pretty_log(
            message=f"❌ Failed to fetch VNA member entry for user: {user.name} (ID: {user_id}): {e}",
            tag="error",
            include_trace=True,
        )
        return None

# Fetch one custom role entry for a user
async def fetch_user_role(bot, user: discord.Member):
    """
    Returns the custom role ID for a user from the database.
    """
    user_id = user.id
    try:
        async with bot.pg_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT role_id
                FROM custom_roles
                WHERE user_id = $1
                """,
                user_id,
            )
            if row:
                pretty_log(
                    message=f"✅ Fetched custom role for user: {user.name} (ID: {user_id})",
                    tag="db",
                )
                return row["role_id"]
            else:
                pretty_log(
                    message=f"ℹ️ No custom role found for user: {user.name} (ID: {user_id})",
                    tag="db",
                )
                return None
    except Exception as e:
        pretty_log(
            message=f"❌ Failed to fetch custom role for user: {user.name} (ID: {user_id}): {e}",
            tag="error",
            include_trace=True,
        )
        return None


# Upsert a market alert user into the database
async def upsert_market_alert_user(
    bot: discord.Client, user: discord.Member, max_alerts: int
):
    """
    Upserts a market alert user into the database.
    """
    user_id = user.id
    user_name = user.name
    alerts_used = 0
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO market_alert_users (user_id, user_name, max_alerts, alerts_used)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id) DO UPDATE
                SET user_name = EXCLUDED.user_name,
                    max_alerts = EXCLUDED.max_alerts
                """,
                user_id,
                user_name,
                max_alerts,
                alerts_used,
            )
            pretty_log(
                message=f"✅ Upserted market alert user: {user_name} (ID: {user_id}) with max alerts: {max_alerts}",
                tag="db",
            )
    except Exception as e:
        pretty_log(
            message=f"❌ Failed to upsert market alert user: {user_name} (ID: {user_id}): {e}",
            tag="error",
            include_trace=True,
        )

# Fetch a market alert user from the database
async def fetch_market_alert_user(bot: discord.Client, user_id: int):
    """
    Fetches a market alert user from the database.
    """
    try:
        async with bot.pg_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT user_id, user_name, max_alerts, alerts_used
                FROM market_alert_users
                WHERE user_id = $1
                """,
                user_id,
            )
            if row:
                pretty_log(
                    message=f"✅ Fetched market alert user: {row['user_name']} (ID: {row['user_id']})",
                    tag="db",
                )
                return dict(row)
            else:
                pretty_log(
                    message=f"ℹ️ Market alert user with ID: {user_id} not found.",
                    tag="db",
                )
                return None
    except Exception as e:
        pretty_log(
            message=f"❌ Failed to fetch market alert user with ID: {user_id}: {e}",
            tag="error",
            include_trace=True,
        )
        return None

# Increment alerts used for a market alert user
async def increment_alerts_used(bot: discord.Client, user_id: int):
    """
    Increments the alerts used for a market alert user.
    """
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE market_alert_users
                SET alerts_used = alerts_used + 1
                WHERE user_id = $1
                """,
                user_id,
            )
            pretty_log(
                message=f"✅ Incremented alerts used for market alert user with ID: {user_id}",
                tag="db",
            )
    except Exception as e:
        pretty_log(
            message=f"❌ Failed to increment alerts used for market alert user with ID: {user_id}: {e}",
            tag="error",
            include_trace=True,
        )

# Subtract max alerts for a market alert user
async def subtract_max_alerts(bot: discord.Client, user_id: int, amount: int):
    """
    Subtracts from the max alerts for a market alert user.
    """
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE market_alert_users
                SET max_alerts = GREATEST(max_alerts - $2, 0)
                WHERE user_id = $1
                """,
                user_id,
                amount,
            )
            pretty_log(
                message=f"✅ Subtracted {amount} from max alerts for market alert user with ID: {user_id}",
                tag="db",
            )
    except Exception as e:
        pretty_log(
            message=f"❌ Failed to subtract max alerts for market alert user with ID: {user_id}: {e}",
            tag="error",
            include_trace=True,
        )

async def set_max_alerts(
    bot: discord.Client, user_id: int, new_max_alerts: int
):
    """
    Sets the max alerts for a market alert user to a specific value.
    """
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE market_alert_users
                SET max_alerts = $2
                WHERE user_id = $1
                """,
                user_id,
                new_max_alerts,
            )
            pretty_log(
                message=f"✅ Set max alerts to {new_max_alerts} for market alert user with ID: {user_id}",
                tag="db",
            )
    except Exception as e:
        pretty_log(
            message=f"❌ Failed to set max alerts for market alert user with ID: {user_id}: {e}",
            tag="error",
            include_trace=True,
        )

async def update_alerts_used(
    bot: discord.Client, user_id: int, new_alerts_used: int
):
    """
    Updates the alerts used for a market alert user to a specific value.
    """
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE market_alert_users
                SET alerts_used = $2
                WHERE user_id = $1
                """,
                user_id,
                new_alerts_used,
            )
            pretty_log(
                message=f"✅ Updated alerts used to {new_alerts_used} for market alert user with ID: {user_id}",
                tag="db",
            )
    except Exception as e:
        pretty_log(
            message=f"❌ Failed to update alerts used for market alert user with ID: {user_id}: {e}",
            tag="error",
            include_trace=True,
        )
async def remove_market_alert_user(
    bot: discord.Client, user_id: int
):
    """
    Removes a market alert user from the database.
    """
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM market_alert_users
                WHERE user_id = $1
                """,
                user_id,
            )
            pretty_log(
                message=f"✅ Removed market alert user with ID: {user_id}",
                tag="db",
            )
    except Exception as e:
        pretty_log(
            message=f"❌ Failed to remove market alert user with ID: {user_id}: {e}",
            tag="error",
            include_trace=True,
        )