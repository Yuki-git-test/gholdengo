import asyncio
import re

import discord

# If colors are different just check terminal and update the one in rarity_meta
from Constants.paldea_galar_dict import (
    Legendary_icon_url,
    get_rarity_by_color,
    icon_url_map,
    paldean_mons,
    rarity_meta,
)
from Constants.vn_allstars_constants import (
    VN_ALLSTARS_EMOJIS,
    VN_ALLSTARS_ROLES,
    VN_ALLSTARS_TEXT_CHANNELS,
)
from utils.cache.cache_list import (
    _market_alert_index,
    market_alert_cache,
    market_value_cache,
    processed_market_feed_ids,
    processed_market_feed_message_ids,
)
from utils.db.market_value_db import set_market_value
from utils.functions.webhook_func import send_webhook
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log

# enable_debug(f"{__name__}.market_snipe_handler")
# enable_debug(f"{__name__}.handle_market_alert")
# enable_debug(f"{__name__}.market_feeds_listener")
# 🟣────────────────────────────────────────────
#  ⚡ Market Snipe ⚡
# 🟣────────────────────────────────────────────
MH_WEBHOOK_IDS = {
    1425808727793205378,  # Golden
    1425808602722996327,  # Shiny
    1425808333180371088,  # Legendary, Mega , Gmax
    1425808079588425740,  # CURS
}
SNIPE_MAP = {
    "common": {"role": VN_ALLSTARS_ROLES.common_snipe},
    "uncommon": {"role": VN_ALLSTARS_ROLES.uncommon_snipe},
    "rare": {"role": VN_ALLSTARS_ROLES.rare_snipe},
    "superrare": {"role": VN_ALLSTARS_ROLES.super_rare_snipe},
    "legendary": {"role": VN_ALLSTARS_ROLES.legendary_snipe},
    "shiny": {"role": VN_ALLSTARS_ROLES.shiny_snipe},
    "golden": {"role": VN_ALLSTARS_ROLES.golden_snipe},
    "event_exclusive": {"role": VN_ALLSTARS_ROLES.eventexclusives_snipe},
    "gmax": {"role": VN_ALLSTARS_ROLES.gmax_snipe},
    "mega": {"role": VN_ALLSTARS_ROLES.mega_snipe},
    "paldean": {"role": VN_ALLSTARS_ROLES.paldean_snipe},
}

SNIPE_CHANNEL_ID = VN_ALLSTARS_TEXT_CHANNELS.snipe_channel


# 🟣────────────────────────────────────────────
#           👂 Market Snipe Handler
# 🟣────────────────────────────────────────────
async def market_snipe_handler(
    bot: discord.Client,
    poke_name: str,
    listed_price: int,
    id: str,
    lowest_market: int,
    amount: int,
    listing_seen: str,
    guild: discord.Guild,
    embed: discord.Embed,
):
    debug_log(f"Handling market snipe for {poke_name} with ID {id}")
    embed_color = embed.color.value
    debug_log(f"Embed color: {embed_color}")
    rarity = get_rarity_by_color(embed_color)
    debug_log(f"Initial rarity: {rarity}")
    display_pokemon_name = poke_name.title()

    if rarity == "unknown":
        debug_log(f"Rarity unknown, checking name and author for special cases.")
        if (
            "shiny gigantamax-" in poke_name.lower()
            or "shiny eternamax-" in poke_name.lower()
            or "shiny mega " in poke_name.lower()
        ):
            rarity = "shiny"
            debug_log(f"Set rarity to shiny due to name.")
        elif "mega " in poke_name.lower():
            rarity = "mega"
            debug_log(f"Set rarity to mega due to name.")
        elif "gigantamax-" in poke_name.lower() or "eternamax-" in poke_name.lower():
            rarity = "gmax"
            debug_log(f"Set rarity to gmax due to name.")
        elif embed.author and embed.author.icon_url == Legendary_icon_url:
            rarity = "legendary"
            debug_log(f"Set rarity to legendary due to author icon.")

    debug_log(f"Final rarity: {rarity}")
    ping_role_id = SNIPE_MAP.get(rarity, {}).get("role")
    ping_role_line = f"<@&{ping_role_id}> " if ping_role_id else ""
    if rarity == "event_exclusive":
        icon_url = embed.author.icon_url
        if "shiny" in poke_name.lower():
            shiny_ping_role_id = SNIPE_MAP.get("shiny", {}).get("role")
            ping_role_line += f"<@&{shiny_ping_role_id}> "
        elif poke_name.title() in paldean_mons:
            second_snipe_rarity_role_id = VN_ALLSTARS_ROLES.paldean_snipe
            ping_role_line += f"<@&{second_snipe_rarity_role_id}> "

        else:
            second_snipe_rarity = icon_url_map.get(icon_url)
            second_rarity_role_id = SNIPE_MAP.get(second_snipe_rarity, {}).get("role")
            if second_rarity_role_id:
                ping_role_line += f"<@&{second_rarity_role_id}> "

    debug_log(f"Ping role line: {ping_role_line}")

    snipe_channel = guild.get_channel(SNIPE_CHANNEL_ID)
    if snipe_channel:
        content = f"{ping_role_line} {display_pokemon_name} listed for {VN_ALLSTARS_EMOJIS.vna_pokecoin} {listed_price:,}!"
        debug_log(f"Snipe content: {content}")

        # 🧾 Build embed
        new_embed = discord.Embed(color=embed.color or 0x0855FB)
        debug_log(f"Building new embed for snipe notification.")
        if embed.thumbnail:
            new_embed.set_thumbnail(url=embed.thumbnail.url)
            debug_log(f"Set thumbnail: {embed.thumbnail.url}")
        new_embed.set_author(
            name=embed.author.name if embed.author else "",
            icon_url=embed.author.icon_url if embed.author else None,
        )
        debug_log(
            f"Set author: {embed.author.name if embed.author else ''}, icon: {embed.author.icon_url if embed.author else None}"
        )
        new_embed.add_field(
            name="Buy Command (Android)", value=f";m b {id}", inline=False
        )
        new_embed.add_field(
            name="Buy Command (Iphone)", value=f"`;m b {id}`", inline=False
        )
        new_embed.add_field(name="ID", value=id, inline=True)
        new_embed.add_field(
            name="Listed Price",
            value=f"{VN_ALLSTARS_EMOJIS.vna_pokecoin} {listed_price:,}",
            inline=True,
        )
        new_embed.add_field(name="Amount", value=str(amount), inline=True)
        new_embed.add_field(
            name="Lowest Market",
            value=(
                f"{VN_ALLSTARS_EMOJIS.vna_pokecoin} {int(lowest_market):,}"
                if isinstance(lowest_market, (int, float)) and lowest_market != "?"
                else f"{VN_ALLSTARS_EMOJIS.vna_pokecoin} ?"
            ),
            inline=True,
        )

        new_embed.add_field(
            name="Listing Seen",
            value=listing_seen,
            inline=True,
        )

        new_embed.set_footer(
            text="Kindly check market listing before purchasing.",
            icon_url=guild.icon.url if guild else None,
        )
        debug_log(
            f"Set footer: Kindly check market listing before purchasing. Icon: {guild.icon.url if guild else None}"
        )
        # await snipe_channel.send(content=content, embed=new_embed)
        debug_log(f"Sending webhook for snipe notification.")
        try:
            await send_webhook(
                bot=bot,
                channel=snipe_channel,
                content=content,
                embed=new_embed,
            )
        except Exception as e:
            debug_log(f"Exception in send_webhook for snipe: {e}", highlight=True)
            return

        pretty_log(
            "sent",
            f"Snipe notification sent in channel {snipe_channel.name} for {display_pokemon_name} at {listed_price:,}",
        )


# 🟣────────────────────────────────────────────
#        👂 Market Alert Handler
# 🟣────────────────────────────────────────────
async def handle_market_alert(
    bot: discord.Client,
    user_name: str,
    guild: discord.Guild,
    original_id: str,
    poke_name: str,
    listed_price: int,
    channel_id: int,
    role_id: int,
    amount: int,
    lowest_market: int,
    listing_seen: str,
    embed: discord.Embed,
):

    alert_channel = guild.get_channel(channel_id)
    if not alert_channel:
        pretty_log(
            "error",
            f"Alert channel with ID {channel_id} not found in guild {guild.name}",
        )
        return

    # Build embed
    color = embed.color or 0x00FF00
    alert_embed = discord.Embed(color=color)
    if embed.thumbnail:
        alert_embed.set_thumbnail(url=embed.thumbnail.url)
    alert_embed.set_author(
        name=embed.author.name if embed.author else "",
        icon_url=embed.author.icon_url if embed.author else None,
    )

    # Buy command
    alert_embed.add_field(name="Buy Command", value=f";m b {original_id}", inline=False)
    alert_embed.add_field(name="ID", value=original_id, inline=True)
    alert_embed.add_field(
        name="Listed Price",
        value=f"{VN_ALLSTARS_EMOJIS.vna_pokecoin} {listed_price:,}",
        inline=True,
    )
    alert_embed.add_field(name="Amount", value=amount, inline=True)
    alert_embed.add_field(
        name="Lowest Market",
        value=f"{VN_ALLSTARS_EMOJIS.vna_pokecoin} {lowest_market:,}",
        inline=True,
    )
    alert_embed.add_field(
        name="Listing Seen",
        value=listing_seen,
        inline=True,
    )
    alert_embed.set_footer(
        text="Kindly check market listing before purchasing.",
        icon_url=guild.icon.url if guild else None,
    )
    if role_id:
        content = f"<@&{role_id}> {poke_name.title()} listed for {VN_ALLSTARS_EMOJIS.vna_pokecoin} {listed_price:,} each!"
    else:
        content = f"{poke_name.title()} listed for {VN_ALLSTARS_EMOJIS.vna_pokecoin} {listed_price:,} each!"
    # await alert_channel.send(content=content, embed=alert_embed)
    await send_webhook(
        bot=bot,
        channel=alert_channel,
        content=content,
        embed=alert_embed,
    )

    pretty_log(
        "sent",
        f"Market alert sent in channel {alert_channel.name} for {user_name} {poke_name.title()} at {listed_price:,}",
    )


# 🟣────────────────────────────────────────────
#           👂 Market Feeds Listener
# 🟣────────────────────────────────────────────
async def market_feeds_listener(bot: discord.Client, message: discord.Message):
    """
    Listens for market listings and detects potential snipes.
    """
    debug_log(
        f"Received message with ID: {message.id} from webhook: {message.webhook_id}"
    )
    if message.webhook_id not in MH_WEBHOOK_IDS:
        debug_log(f"Message from unallowed webhook: {message.webhook_id}")
        return

    if not message.embeds:
        debug_log("Message has no embeds")
        return

    if message.id in processed_market_feed_message_ids:
        debug_log(f"Message ID {message.id} already processed")
        return
    processed_market_feed_message_ids.add(message.id)

    for embed in message.embeds:
        try:
            embed_author_name = embed.author.name if embed.author else ""
            debug_log(f"Processing embed with author: {embed_author_name}")

            match = re.match(r"(.+?)\s+#(\d+)", embed_author_name)
            if not match:
                debug_log(f"Could not parse embed author name: {embed_author_name}")
                continue

            poke_name = match.group(1)
            poke_dex = int(match.group(2))
            debug_log(f"Parsed poke_name: {poke_name}, poke_dex: {poke_dex}")

            fields = {f.name: f.value for f in embed.fields}
            debug_log(f"Embed fields: {fields}")

            # Extract Listed Price and Lowest Market, removing any emojis
            listed_price_str = re.sub(
                r"<a?:\w+:\d+>", "", fields.get("Listed Price", "0")
            )
            match_price = re.search(r"(\d[\d,]*)", listed_price_str)
            listed_price = (
                int(match_price.group(1).replace(",", "")) if match_price else 0
            )
            debug_log(f"Parsed listed_price: {listed_price}")

            lowest_market_str = re.sub(
                r"<a?:\w+:\d+>", "", fields.get("Lowest Market", "0")
            )
            lowest_market_match = re.search(r"(\d[\d,]*)", lowest_market_str)
            lowest_market = (
                int(lowest_market_match.group(1).replace(",", ""))
                if lowest_market_match
                else 0
            )
            debug_log(f"Parsed lowest_market: {lowest_market}")

            listing_seen = fields.get("Listing Seen", "N/A")
            amount = fields.get("Amount", "1")
            debug_log(f"Parsed listing_seen: {listing_seen}, amount: {amount}")

            original_id = fields.get("ID", "0")
            embed_color = embed.color.value
            is_exclusive = True if embed_color == 0xEA260B else False
            display_pokemon_name = poke_name.title()
            thumbnail_url = embed.thumbnail.url if embed.thumbnail else None

            if original_id in processed_market_feed_ids:
                debug_log(f"Market Feed ID {original_id} already processed")
                continue
            debug_log(f"Market Feed ID {original_id}")
            processed_market_feed_ids.add(original_id)

            # If Listed Price is 30% or more below Lowest Market, it's a snipe
            if lowest_market > 0 and listed_price <= lowest_market * 0.7:
                debug_log(
                    f"Snipe detected for {poke_name} at price {listed_price} (lowest market: {lowest_market})"
                )

                try:
                    await market_snipe_handler(
                        bot=bot,
                        poke_name=poke_name,
                        listed_price=listed_price,
                        id=original_id,
                        lowest_market=lowest_market,
                        amount=int(amount),
                        listing_seen=listing_seen,
                        guild=message.guild,
                        embed=embed,
                    )
                except Exception as e:
                    debug_log(f"Exception in market_snipe_handler: {e}", highlight=True)
            elif lowest_market == 0:
                # First listing, no lowest market to compare
                pretty_log(
                    "info",
                    f"First listing detected for {display_pokemon_name} with ID {original_id}. Treating as potential snipe.",
                )
                lowest_market = "?"
                try:
                    await market_snipe_handler(
                        bot=bot,
                        poke_name=poke_name,
                        listed_price=listed_price,
                        id=original_id,
                        lowest_market=lowest_market,
                        amount=int(amount),
                        listing_seen=listing_seen,
                        guild=message.guild,
                        embed=embed,
                    )
                except Exception as e:
                    debug_log(f"Exception in market_snipe_handler: {e}", highlight=True)
                    pretty_log(
                        "error",
                        f"Error handling market snipe for {display_pokemon_name} with ID {original_id}: {e}",
                    )

            # Check for market alerts
            if not market_alert_cache:
                debug_log("Market alert cache is empty, skipping alert checks.")
                continue  # Skip if cache is empty

            # ✅ O(1) lookup using indexed cache
            alerts_to_check = [
                alert
                for key, alert in _market_alert_index.items()
                if key[0].lower() == poke_name.lower()
            ]
            debug_log(f"Alerts to check: {alerts_to_check}")

            for alert in alerts_to_check:
                if not isinstance(alert, dict):
                    debug_log(f"Skipping alert (not a dict): {alert}")
                    continue
                debug_log(
                    f"Checking alert for user {alert['user_name']} and pokemon {alert['pokemon']}"
                )
                debug_log(f"Alert type: {type(alert)}, value: {alert}")
                if (
                    alert["pokemon"].lower() == poke_name.lower()
                    and listed_price <= alert["max_price"]
                ):
                    role_id = alert["role_id"]
                    channel_id = alert["channel_id"]
                    user_name = alert["user_name"]

                    debug_log(
                        f"Triggering market alert for {user_name} on {poke_name} at price {listed_price}"
                    )
                    await handle_market_alert(
                        bot=bot,
                        user_name=user_name,
                        guild=message.guild,
                        original_id=original_id,
                        poke_name=poke_name,
                        listed_price=listed_price,
                        channel_id=channel_id,
                        role_id=role_id,
                        amount=amount,
                        lowest_market=lowest_market,
                        listing_seen=listing_seen,
                        embed=embed,
                    )
            # 💎────────────────────────────────────────────
            #           🏪 Update Market Value Cache & DB
            # 💎────────────────────────────────────────────
            # Update market value cache with new listing data
            # Extract additional market data
            lowest_market_str = re.sub(
                r"<a?:\w+:\d+>", "", fields.get("Lowest Market", "0")
            )
            lowest_market_match = re.search(r"(\d[\d,]*)", lowest_market_str)
            lowest_market = (
                int(lowest_market_match.group(1).replace(",", ""))
                if lowest_market_match
                else 0
            )

            listing_seen = fields.get("Listing Seen", "Unknown")

            # Upsert into market value cache
            cache_key = poke_name.lower()

            # Get existing data to preserve true lowest price
            existing_data = market_value_cache.get(cache_key, {})
            existing_lowest = existing_data.get("true_lowest", float("inf"))

            # Ensure all values are not None for min/max
            price_candidates = [listed_price, lowest_market, existing_lowest]
            price_candidates = [p for p in price_candidates if p is not None]
            if price_candidates:
                true_lowest = min(price_candidates)
            else:
                true_lowest = 0

            # Only update if we have a valid price (not 0)
            if true_lowest == float("inf") or true_lowest == 0:
                max_candidates = [listed_price, lowest_market]
                max_candidates = [p for p in max_candidates if p is not None]
                if max_candidates and max(max_candidates) > 0:
                    true_lowest = max(max_candidates)
                else:
                    true_lowest = 0

            # Only update DB if any value has changed
            cache_update = {
                "pokemon": poke_name,
                "dex": poke_dex,
                "is_exclusive": is_exclusive,
                "lowest_market": lowest_market,
                "current_listing": listed_price,
                "true_lowest": true_lowest,
                "listing_seen": listing_seen,
                "image_link": thumbnail_url,
            }
            prev = market_value_cache.get(cache_key, {})
            needs_update = (
                prev.get("lowest_market") != lowest_market
                or prev.get("current_listing") != listed_price
                or prev.get("true_lowest") != true_lowest
                or prev.get("listing_seen") != listing_seen
                or prev.get("dex") != poke_dex
                or prev.get("is_exclusive") != is_exclusive
                or prev.get("image_link") != thumbnail_url
            )
            market_value_cache[cache_key] = cache_update
            if needs_update:
                await set_market_value(
                    bot,
                    pokemon_name=poke_name,
                    dex_number=poke_dex,
                    is_exclusive=is_exclusive,
                    lowest_market=lowest_market,
                    current_listing=listed_price,
                    true_lowest=true_lowest,
                    listing_seen=listing_seen,
                    image_link=thumbnail_url,
                )
                pretty_log(
                    "debug",
                    f"Updated market cache & DB for {poke_name}: embed_lowest={lowest_market:,}, current={listed_price:,}, true_lowest={true_lowest:,}, seen={listing_seen}",
                )

        except Exception as e:
            debug_log(f"Exception in embed processing: {e}", highlight=True, force=True)
