from utils.logs.pretty_log import pretty_log

processed_market_feed_message_ids = set()
processed_market_feed_ids = set()
processing_end_giveaway_message_ids = set()
snipe_ga_active = False

active_lottery_thread_ids: set[int] = set()
processing_end_lottery_ids: set[int] = set()

def clear_processed_messages_cache():
    """Clears all processed message ID caches."""
    processed_market_feed_message_ids.clear()
    processed_market_feed_ids.clear()

    pretty_log(message="✅ Cleared all processed message ID caches", tag="cache")


market_alert_cache: list[dict] = []
# Structure: {
#     "user_id": int,
#     "pokemon": str,
#     "dex": str,
#     "max_price": int,
#     "channel_id": int,
#     "role_id": int
# }

_market_alert_index: dict[tuple[str, int], dict] = (
    {}
)  # key = (pokemon.lower(), channel_id)
# Structure
# _market_alert_index = {
#     ("pikachu", 987654321): {
#         "user_id": 123456789,
#         "pokemon": "Pikachu",
#         "dex_number": 25,
#         "max_price": 5000,
#         "channel_id": 987654321,
#         "role_id": 192837465
#     },

webhook_url_cache: dict[tuple[int, int], dict[str, str]] = {}
#     ...
#
# }
# key = (bot_id, channel_id)
# Structure:
# webhook_url_cache = {
# (bot_id, channel_id): {
#     "url": "https://discord.com/api/webhooks/..."
#     "channel_name": "alerts-channel",
# },
#


vna_members_cache: dict[int, dict] = {}
# Structure
# user_id: {
# "user_name": str,
# "pokemeow_name": str,
# "channel_id": int,
# "perks": str,
# "faction": str,
# }

market_value_cache: dict[str, dict] = {}
