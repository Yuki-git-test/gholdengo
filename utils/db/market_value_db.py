# 🟣────────────────────────────────────────────
#        Market Value DB Functions for Mew (bot.pg_pool)
# 🟣────────────────────────────────────────────

import discord
from datetime import datetime
from utils.logs.pretty_log import pretty_log

from utils.cache.cache_list import market_value_cache


# --------------------
#  Upsert market value data
# --------------------
async def set_market_value(
    bot,
    pokemon_name: str,
    dex_number: int,
    rarity: str | None = None,
    lowest_market: int = 0,
    current_listing: int = 0,
    true_lowest: int = 0,
    listing_seen: str | None = None,
):
    """
    Insert or update market value data for a Pokémon.
    """
    try:
        async with bot.pg_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO market_value (
                    pokemon_name, dex_number, rarity, lowest_market,
                    current_listing, true_lowest, listing_seen, last_updated
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (pokemon_name) DO UPDATE SET
                    dex_number = $2,
                    rarity = COALESCE($3, market_value.rarity),
                    lowest_market = $4,
                    current_listing = $5,
                    true_lowest = LEAST($6, market_value.true_lowest),
                    listing_seen = COALESCE($7, market_value.listing_seen),
                    last_updated = $8
                """,
                pokemon_name.lower(),
                dex_number,
                rarity,
                lowest_market,
                current_listing,
                true_lowest,
                listing_seen,
                datetime.utcnow(),
            )

        pretty_log(
            tag="db",
            message=f"Updated market value for {pokemon_name}: true_lowest={true_lowest:,}",
            bot=bot,
        )

    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to set market value for {pokemon_name}: {e}",
            bot=bot,
        )


# --------------------
#  Fetch single Pokémon market value
# --------------------
async def fetch_market_value(bot, pokemon_name: str) -> dict | None:
    """
    Get market value data for a specific Pokémon.
    """
    try:
        async with bot.pg_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM market_value WHERE pokemon_name = $1",
                pokemon_name.lower(),
            )
            return dict(row) if row else None
    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to fetch market value for {pokemon_name}: {e}",
            bot=bot,
        )
        return None


# --------------------
#  Fetch all market values
# --------------------
async def fetch_all_market_values(bot) -> list[dict]:
    """
    Return all market value data as list of dicts.
    """
    try:
        async with bot.pg_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM market_value ORDER BY last_updated DESC"
            )
            return [dict(row) for row in rows]
    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to fetch market values: {e}",
            bot=bot,
        )
        return []


# --------------------
#  Fetch high value Pokémon (above threshold)
# --------------------
async def fetch_high_value_pokemon(bot, min_price: int = 100000) -> list[dict]:
    """
    Get Pokémon with true_lowest above specified threshold.
    """
    try:
        async with bot.pg_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM market_value WHERE true_lowest >= $1 ORDER BY true_lowest DESC",
                min_price,
            )
            return [dict(row) for row in rows]
    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to fetch high value pokemon: {e}",
            bot=bot,
        )
        return []


# --------------------
#  Delete old market data
# --------------------
async def cleanup_old_market_data(bot, days_old: int = 30) -> bool:
    """
    Delete market value records older than specified days.
    """
    try:
        async with bot.pg_pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM market_value WHERE last_updated < NOW() - INTERVAL '%s days'",
                days_old,
            )

        deleted_count = int(result.split()[-1]) if result.split() else 0
        pretty_log(
            tag="db",
            message=f"Cleaned up {deleted_count} old market value records",
            bot=bot,
        )
        return True
    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to cleanup old market data: {e}",
            bot=bot,
        )
        return False


# --------------------
#  Sync cache to database
# --------------------
async def sync_market_cache_to_db(bot, market_cache: dict):
    """
    Sync entire market value cache to database.
    """
    try:
        update_count = 0
        async with bot.pg_pool.acquire() as conn:
            for pokemon_name, data in market_cache.items():
                await conn.execute(
                    """
                    INSERT INTO market_value (
                        pokemon_name, dex_number, rarity, lowest_market,
                        current_listing, true_lowest, listing_seen, last_updated
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (pokemon_name) DO UPDATE SET
                        dex_number = $2,
                        rarity = COALESCE($3, market_value.rarity),
                        lowest_market = $4,
                        current_listing = $5,
                        true_lowest = LEAST($6, market_value.true_lowest),
                        listing_seen = COALESCE($7, market_value.listing_seen),
                        last_updated = $8
                    """,
                    pokemon_name.lower(),
                    data.get("dex", 0),
                    data.get("rarity", "unknown"),
                    data.get("lowest_market", 0),
                    data.get("current_listing", 0),
                    data.get("true_lowest", 0),
                    data.get("listing_seen", "Unknown"),
                    datetime.utcnow(),
                )
                update_count += 1

        pretty_log(
            tag="db",
            message=f"Synced {update_count} market value entries to database",
            bot=bot,
        )
        return True

    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to sync market cache to database: {e}",
            bot=bot,
        )
        return False


# --------------------
#  Load database into cache
# --------------------
async def load_market_cache_from_db(bot) -> dict:
    """
    Load all market value data from database into cache format.
    """
    try:
        cache = {}
        async with bot.pg_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM market_value")

            for row in rows:
                cache[row["pokemon_name"]] = {
                    "pokemon": row["pokemon_name"],
                    "dex": row["dex_number"],
                    "rarity": row["rarity"],
                    "lowest_market": row["lowest_market"],
                    "current_listing": row["current_listing"],
                    "true_lowest": row["true_lowest"],
                    "listing_seen": row["listing_seen"],
                }

        pretty_log(
            tag="",
            message=f"Loaded {len(cache)} market value entries from database",
            label="💎 Market Value Cache",
            bot=bot,
        )
        return market_value_cache.update(cache)  # Update the global cache

    except Exception as e:
        pretty_log(
            tag="error",
            message=f"Failed to load market cache from database: {e}",
            bot=bot,
        )
        return {}
