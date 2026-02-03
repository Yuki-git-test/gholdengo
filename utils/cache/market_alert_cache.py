import discord

from utils.db.market_alert_db import fetch_all_market_alerts
from utils.logs.pretty_log import pretty_log

from .cache_list import _market_alert_index, market_alert_cache


async def load_market_alert_cache(bot: discord.Client):
    market_alert_cache.clear()
    _market_alert_index.clear()
    try:
        alerts = await fetch_all_market_alerts(bot)
        if not alerts:
            pretty_log(
                message="⚠️ No market alerts found to load into cache.",
                tag="cache",
            )
            return

        for alert in alerts:
            alert_entry = {
                "user_name": alert["user_name"],
                "pokemon": alert["pokemon"],
                "dex": alert["dex"],
                "max_price": alert["max_price"],
                "channel_id": alert["channel_id"],
                "role_id": alert["role_id"],
                "user_id": alert["user_id"],
            }
            market_alert_cache.append(alert_entry)
            key = (
                alert_entry["pokemon"],
                alert_entry["channel_id"],
                alert_entry["user_id"],
            )
            _market_alert_index[key] = alert_entry
        pretty_log(
            message=f"✅ Loaded {len(market_alert_cache)} market alerts into cache.",
            tag="cache",
        )
        """pretty_log(
            message=f"Market Alert Cache Contents: {market_alert_cache}",
            tag="cache",
        )
        pretty_log(
                message=f"_market_alert_index Contents: {_market_alert_index}",
                tag="cache",
            )"""
        if len(market_alert_cache) == 0:
            pretty_log(
                message="⚠️ Market alert cache is empty after loading.",
                tag="cache",
            )
        return market_alert_cache

    except Exception as e:
        pretty_log(
            message=f"❌ Error loading market alert cache: {e}",
            tag="cache",
        )
        raise e


def insert_alert_into_cache(
    user_id: int,
    user_name: str,
    pokemon: str,
    dex: str,
    max_price: int,
    channel_id: int,
    role_id: int,
):
    alert_entry = {
        "user_id": user_id,
        "user_name": user_name,
        "pokemon": pokemon,
        "dex": dex,
        "max_price": max_price,
        "channel_id": channel_id,
        "role_id": role_id,
    }
    market_alert_cache.append(alert_entry)
    key = (pokemon, channel_id, user_id)
    _market_alert_index[key] = alert_entry
    pretty_log(
        message=f"✅ Inserted market alert for {user_name} {pokemon} (User ID: {user_id}) into cache.",
        tag="cache",
    )


def remove_alert_from_user_in_cache(
    user_id: int,
    pokemon: str,
):
    # Fetch channel_id from the cache entry
    channel_id = None
    for alert in market_alert_cache:
        if alert["user_id"] == user_id and alert["pokemon"] == pokemon:
            channel_id = alert["channel_id"]
            break
    if channel_id is None:
        pretty_log(
            message=f"⚠️ Could not find channel_id for User ID: {user_id}, Pokemon: {pokemon} in cache.",
            tag="cache",
        )
        return

    key = (pokemon, channel_id, user_id)
    alert_entry = _market_alert_index.get(key)
    if alert_entry:
        market_alert_cache.remove(alert_entry)
        del _market_alert_index[key]
        pretty_log(
            message=f"✅ Removed market alert for {alert_entry['user_name']} {pokemon} (User ID: {user_id}) from cache.",
            tag="cache",
        )
    else:
        pretty_log(
            message=f"⚠️ Market alert for User ID: {user_id}, Pokemon: {pokemon}, Channel ID: {channel_id} not found in cache.",
            tag="cache",
        )


def remove_all_alerts_for_user_in_cache(user_id: int):
    to_remove = [alert for alert in market_alert_cache if alert["user_id"] == user_id]
    for alert in to_remove:
        market_alert_cache.remove(alert)
        key = (alert["pokemon"], alert["channel_id"], user_id)
        del _market_alert_index[key]
    pretty_log(
        message=f"✅ Removed all market alerts for User ID: {user_id} from cache.",
        tag="cache",
    )


def update_user_alert_in_cache(
    user_id: int,
    pokemon: str,
    new_max_price: int = None,
    new_channel_id: int = None,
    new_role_id: int = None,
):
    # Find the existing entry by searching for (pokemon, any_channel_id, user_id)
    old_key = None
    for key in _market_alert_index:
        if key[0] == pokemon and key[2] == user_id:
            old_key = key
            break

    if old_key:
        alert_entry = _market_alert_index[old_key]
        if new_max_price is not None:
            alert_entry["max_price"] = new_max_price
        if new_channel_id is not None:
            alert_entry["channel_id"] = new_channel_id
        if new_role_id is not None:
            alert_entry["role_id"] = new_role_id

        # If channel_id changed, re-key the index
        if new_channel_id is not None and old_key[1] != new_channel_id:
            del _market_alert_index[old_key]
            new_key = (pokemon, new_channel_id, user_id)
            _market_alert_index[new_key] = alert_entry

        pretty_log(
            message=f"✅ Updated market alert for {alert_entry['user_name']} {pokemon} (User ID: {user_id}) in cache.",
            tag="cache",
        )
    else:
        pretty_log(
            message=f"⚠️ Market alert for User ID: {user_id}, Pokemon: {pokemon} not found in cache for update.",
            tag="cache",
        )


def fetch_user_alerts_from_cache(user_id: int) -> list[dict]:
    user_alerts = [a for a in market_alert_cache if a["user_id"] == user_id]
    return user_alerts
