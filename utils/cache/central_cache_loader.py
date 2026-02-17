import discord

from utils.logs.pretty_log import pretty_log

from .cache_list import market_alert_cache
from .market_alert_cache import load_market_alert_cache
from .vna_members_cache import load_vna_members_cache
from .webhook_url_cache import load_webhook_url_cache
from utils.db.market_value_db import load_market_cache_from_db
from utils.db.lottery import load_active_lotteries_into_cache

async def load_all_cache(bot: discord.Client):
    """
    Loads all caches used by the bot.
    Currently loads:
    - Market Alert Cache
    """
    try:

        # Load VNA Members Cache
        await load_vna_members_cache(bot)

        # Load Market Alert Cache
        await load_market_alert_cache(bot)

        # Load Webhook URL Cache
        await load_webhook_url_cache(bot)

        # Load Market Value Cache from database
        await load_market_cache_from_db(bot)

        # Load active lottery thread IDs into cache
        await load_active_lotteries_into_cache(bot)

    except Exception as e:
        pretty_log(
            message=f"❌ Error loading caches: {e}",
            tag="cache",
        )
        return
    pretty_log(
        message="✅ All caches loaded successfully.",
        tag="cache",
    )
