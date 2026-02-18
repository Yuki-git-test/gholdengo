import discord
from discord.ext import commands

from Constants.vn_allstars_constants import (
    POKEMEOW_APPLICATION_ID,
    VN_ALLSTARS_TEXT_CHANNELS,
    VNA_SERVER_ID,
)
from utils.cache.cache_list import active_lottery_thread_ids
from utils.functions.donation_sticky_msg import check_and_send_sticky_msg
from utils.listener_func.buy_lottery_ticket_listener import buy_lottery_ticket_listener
from utils.listener_func.dex_listener import dex_listener
from utils.listener_func.donation_listener import (
    clan_donate_listener,
    give_command_listener,
)

# ————————————————————————————————
# 🩵 Import Listener Functions
# ————————————————————————————————
from utils.listener_func.market_feed_listener import market_feeds_listener
from utils.logs.pretty_log import pretty_log
from utils.prefix_commands.ga import create_ga_prefix
from utils.prefix_commands.snipe_ga import create_snipe_ga_prefix

# ️────────────────────────────────────────────
#     Market Feed Channel IDs Set
# ️────────────────────────────────────────────
MARKET_FEED_CHANNEL_IDS = {
    VN_ALLSTARS_TEXT_CHANNELS.c_u_r_s_feed,
    VN_ALLSTARS_TEXT_CHANNELS.golden_feed,
    VN_ALLSTARS_TEXT_CHANNELS.shiny_feed,
    VN_ALLSTARS_TEXT_CHANNELS.l_m_gmax_feed,
}

CLAN_BANK_USER_NAMES = ["yki.on", "beaterxyz"]


def embed_has_field_name(embed, name_to_match: str) -> bool:
    """
    Returns True if any field name in the embed matches the given string.
    Returns False immediately if the embed has no fields.
    """
    if not hasattr(embed, "fields") or not embed.fields:
        return False
    for field in embed.fields:
        if field.name == name_to_match:
            return True
    return False


# 🐾────────────────────────────────────────────
#        🌸 Message Create Listener Cog
# 🐾────────────────────────────────────────────
class MessageCreateListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # 🦋────────────────────────────────────────────
    #           👂 Message Listener Event
    # 🦋────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        # ————————————————————————————————
        # 🏰 Guild Check — Route by server
        # ————————————————————————————————
        guild = message.guild
        if not guild:
            return  # Skip DMs
        if guild.id != VNA_SERVER_ID:
            return  # Only process messages from VN Allstars server

        try:
            # ————————————————————————————————
            # 🏰 Ignore non-PokéMeow bot messages
            # ————————————————————————————————
            # 🚫 Ignore all bots except PokéMeow to prevent loops
            if (
                message.author.bot
                and message.author.id != POKEMEOW_APPLICATION_ID
                and not message.webhook_id
            ):
                return

            content = message.content
            first_embed = message.embeds[0] if message.embeds else None
            first_embed_author = (
                first_embed.author.name if first_embed and first_embed.author else ""
            )
            first_embed_description = (
                first_embed.description
                if first_embed and first_embed.description
                else ""
            )
            first_embed_footer = (
                first_embed.footer.text if first_embed and first_embed.footer else ""
            )
            first_embed_title = (
                first_embed.title if first_embed and first_embed.title else ""
            )

            # ————————————————————————————————
            # 🩵 VNA Market Snipe
            # ————————————————————————————————
            if message.channel.id in MARKET_FEED_CHANNEL_IDS:
                await market_feeds_listener(self.bot, message)
            # ————————————————————————————————
            # 🩵 Snipe Giveaway Prefix Command
            # ————————————————————————————————
            if content.startswith("sg.c"):
                await create_snipe_ga_prefix(self.bot, message)

            # ————————————————————————————————
            # 🩵 Giveaway Prefix Command
            # ————————————————————————————————
            if content.startswith("g.c"):
                await create_ga_prefix(self.bot, message)

            # ————————————————————————————————
            # 🩵 DEX LISTENER
            # ————————————————————————————————
            if first_embed:
                if embed_has_field_name(first_embed, "Dex Number"):
                    pretty_log(
                        "info",
                        f"Detected dex command embed with 'Dex Number' field. Triggering dex listener.",
                    )
                    await dex_listener(self.bot, message)
            # ————————————————————————————————
            # 🩵 Buy Ticket Listener
            # ————————————————————————————————
            if message.channel.id in active_lottery_thread_ids:

                if (
                    content
                    and "gave" in content
                    and "PokeCoins" in content
                    and any(name in content for name in CLAN_BANK_USER_NAMES)
                ):
                    pretty_log(
                        "info",
                        f"Detected clan bank donation message in lottery thread: {content}",
                        label="DONATION_LISTENER",
                    )
                    await buy_lottery_ticket_listener(self.bot, message)
            # ————————————————————————————————
            # 🩵 Clan Donations
            # ————————————————————————————————
            if message.channel.id == VN_ALLSTARS_TEXT_CHANNELS.clan_donations:
                # Clan Treasury donation
                if (
                    content
                    and "You successfully donated" in content
                    and "VN Allstar" in content
                ):
                    pretty_log(
                        "info",
                        f"Detected clan donation message: {content}",
                        label="DONATION_LISTENER",
                    )
                    await clan_donate_listener(self.bot, message)
            if (
                message.channel.id == VN_ALLSTARS_TEXT_CHANNELS.clan_donations
                or message.channel.id == VN_ALLSTARS_TEXT_CHANNELS.khys_chamber
            ):
                # Clan Bank Donation
                if (
                    content
                    and "gave" in content
                    and "PokeCoins" in content
                    and any(name in content for name in CLAN_BANK_USER_NAMES)
                ):
                    pretty_log(
                        "info",
                        f"Detected clan bank donation message: {content}",
                        label="DONATION_LISTENER",
                    )
                    await give_command_listener(self.bot, message)
            if message.channel.id == VN_ALLSTARS_TEXT_CHANNELS.clan_donations:
                await check_and_send_sticky_msg(self.bot, message)
        except Exception as e:
            # 🛑────────────────────────────────────────────
            #        Unhandled on_message Error Handler
            # 🛑────────────────────────────────────────────
            pretty_log(
                "critical",
                f"Unhandled exception in on_message: {e}",
                label="MESSAGE",
                bot=self.bot,
                include_trace=True,
            )


# 🌈────────────────────────────────────────────
#        🛠️ Setup function to add cog to bot
# 🌈────────────────────────────────────────────
async def setup(bot: commands.Bot):
    await bot.add_cog(MessageCreateListener(bot))
