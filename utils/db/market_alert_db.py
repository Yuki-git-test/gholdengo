import discord

from utils.logs.pretty_log import pretty_log


# Upsert a market alert
async def insert_market_alert(
    bot: discord.Client,
    user: discord.Member,
    pokemon: str,
    dex: str,
    max_price: int,
    channel_id: int,
    role_id: int = None,
):
    """
    Inserts a market alert into the database.
    """
    user_id = user.id
    user_name = user.name
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO market_alerts (user_id, user_name, pokemon, dex, max_price, channel_id, role_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                user_id,
                user_name,
                pokemon,
                dex,
                max_price,
                channel_id,
                role_id,
            )
            pretty_log(
                message=f"✅ Inserted market alert for user: {user_name} (ID: {user_id}) - {pokemon} (Dex: {dex}) at max price: {max_price}",
                tag="db",
            )
            # Update cache
            from utils.cache.market_alert_cache import insert_alert_into_cache

            insert_alert_into_cache(
                user_id,
                user_name,
                pokemon,
                dex,
                max_price,
                channel_id,
                role_id,
            )
    except Exception as e:
        pretty_log(
            message=f"❌ Failed to insert market alert for user: {user_name} (ID: {user_id}): {e}",
            tag="error",
            include_trace=True,
        )

# Fetch a specific market alert for user
async def fetch_market_alert(
    bot: discord.Client, user_id: int, pokemon: str
):
    """
    Fetches a specific market alert for a user from the database.
    """
    try:
        async with bot.pg_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, pokemon, dex, max_price, channel_id, role_id
                FROM market_alerts
                WHERE user_id = $1 AND pokemon = $2
                """,
                user_id,
                pokemon,
            )
            if row:
                pretty_log(
                    message=f"✅ Fetched market alert for user ID: {user_id} - {pokemon}",
                    tag="db",
                )
                return row
            else:
                pretty_log(
                    message=f"⚠️ No market alert found for user ID: {user_id} - {pokemon}",
                    tag="db",
                )
                return None
    except Exception as e:
        pretty_log(
            message=f"❌ Failed to fetch market alert for user ID: {user_id} - {pokemon}: {e}",
            tag="error",
            include_trace=True,
        )
        return None
# Fetch all market alerts for a user
async def fetch_market_alerts_for_user(bot: discord.Client, user_id: int):
    """
    Fetches all market alerts for a user from the database.
    """
    try:
        async with bot.pg_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, pokemon, dex, max_price, channel_id, role_id
                FROM market_alerts
                WHERE user_id = $1
                """,
                user_id,
            )
            pretty_log(
                message=f"✅ Fetched {len(rows)} market alerts for user ID: {user_id}",
                tag="db",
            )
            return rows
    except Exception as e:
        pretty_log(
            message=f"❌ Failed to fetch market alerts for user ID: {user_id}: {e}",
            tag="error",
            include_trace=True,
        )
        return []


# Fetch all market alerts
async def fetch_all_market_alerts(bot: discord.Client):
    """
    Fetches all market alerts from the database.
    """
    try:
        async with bot.pg_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, user_name, pokemon, dex, max_price, channel_id, role_id
                FROM market_alerts
                """
            )
            pretty_log(
                message=f"✅ Fetched {len(rows)} total market alerts",
                tag="db",
            )
            return rows
    except Exception as e:
        pretty_log(
            message=f"❌ Failed to fetch all market alerts: {e}",
            tag="error",
            include_trace=True,
        )
        return []


# Update a market alert
async def update_market_alert(
    bot: discord.Client,
    user_id: int,
    pokemon: str,
    new_max_price: int = None,
    new_channel_id: int = None,
    new_role_id: int = None,
):
    """
    Updates a market alert in the database.
    """
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE market_alerts
                SET max_price = COALESCE($2, max_price),
                    channel_id = COALESCE($3, channel_id),
                    role_id = COALESCE($4, role_id)
                WHERE user_id = $1 AND pokemon = $5
                """,
                user_id,
                new_max_price,
                new_channel_id,
                new_role_id,
                pokemon,
            )
            pretty_log(
                message=f"✅ Updated market alert for user ID: {user_id} - {pokemon}",
                tag="db",
            )
            # Update cache
            from utils.cache.market_alert_cache import update_user_alert_in_cache

            update_user_alert_in_cache(
                user_id,
                pokemon,
                new_max_price,
                new_channel_id,
                new_role_id,
            )
    except Exception as e:
        pretty_log(
            message=f"❌ Failed to update market alert for user ID: {user_id} - {pokemon}: {e}",
            tag="error",
            include_trace=True,
        )


# Remove market alert
async def remove_market_alert(bot: discord.Client, user_id: int, pokemon: str):
    """
    Removes a market alert from the database.
    """
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM market_alerts
                WHERE user_id = $1 AND pokemon = $2
                """,
                user_id,
                pokemon,
            )
            pretty_log(
                message=f"✅ Removed market alert for user ID: {user_id} - {pokemon}",
                tag="db",
            )
            # Update cache
            from utils.cache.market_alert_cache import remove_alert_from_user_in_cache

            remove_alert_from_user_in_cache(user_id, pokemon)
    except Exception as e:
        pretty_log(
            message=f"❌ Failed to remove market alert for user ID: {user_id} - {pokemon}: {e}",
            tag="error",
            include_trace=True,
        )


# Remove all market alerts for a user
async def remove_all_market_alerts_for_user(bot: discord.Client, user_id: int):
    """
    Removes all market alerts for a user from the database.
    """
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM market_alerts
                WHERE user_id = $1
                """,
                user_id,
            )
            pretty_log(
                message=f"✅ Removed all market alerts for user ID: {user_id}",
                tag="db",
            )
            # Update cache
            from utils.cache.market_alert_cache import (
                remove_all_alerts_for_user_in_cache,
            )

            remove_all_alerts_for_user_in_cache(user_id)

    except Exception as e:
        pretty_log(
            message=f"❌ Failed to remove all market alerts for user ID: {user_id}: {e}",
            tag="error",
            include_trace=True,
        )
async def remove_recent_market_alerts(bot:discord.Client, user:discord.Member, num_alerts:int):
    """
    Removes the most recent market alerts for a user from the database, then returns what was removed.
    """
    user_id = user.id
    try:
        async with bot.pg_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, pokemon, dex, max_price, channel_id, role_id
                FROM market_alerts
                WHERE user_id = $1
                ORDER BY id DESC
                LIMIT $2
                """,
                user_id,
                num_alerts,
            )
            if not rows:
                pretty_log(
                    message=f"⚠️ No market alerts found to remove for user ID: {user_id}",
                    tag="db",
                )
                return []

            await conn.execute(
                """
                DELETE FROM market_alerts
                WHERE id = ANY($1::int[])
                """,
                [row["id"] for row in rows],
            )
            pretty_log(
                message=f"✅ Removed {len(rows)} recent market alerts for user ID: {user_id}",
                tag="db",
            )
            # Update cache
            from utils.cache.market_alert_cache import (
                remove_alert_from_user_in_cache,
            )

            for row in rows:
                remove_alert_from_user_in_cache(user_id, row["pokemon"])

            return rows

    except Exception as e:
        pretty_log(
            message=f"❌ Failed to remove recent market alerts for user ID: {user_id}: {e}",
            tag="error",
            include_trace=True,
        )
        return []
