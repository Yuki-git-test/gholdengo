from datetime import datetime

import discord
from discord.ext import commands

from Constants.giveaway import GIVEAWAY_ROLES
from Constants.vn_allstars_constants import (
    VN_ALLSTARS_ROLES,
    VN_ALLSTARS_TEXT_CHANNELS,
    VNA_SERVER_ID,
)
from utils.db.ga_db import fetch_all_giveaways
from utils.db.market_alert_db import remove_recent_market_alerts
from utils.db.market_alert_user import fetch_market_alert_user, set_max_alerts
from utils.group_command_func.markert_alert.add import determine_max_alerts
from utils.logs.pretty_log import pretty_log

from .giveaway_role_handler import giveaway_role_remove_handler
from .market_alert_role_handler import market_alert_role_remove_handler

LOG_CHANNEL_ID = VN_ALLSTARS_TEXT_CHANNELS.member_logs

SPECIAL_BOOSTER_ROLES = [
    VN_ALLSTARS_ROLES.server_booster,
    VN_ALLSTARS_ROLES.shiny_donator,
]


# 🍭──────────────────────────────
#   🎀 Event: On Role Remove
# 🍭──────────────────────────────
async def handle_role_remove(
    bot: discord.Client,
    member: discord.Member,
    role: discord.Role,
):
    """Handle role removal events."""
    role_id = role.id

    # ————————————————————————————————
    # 🩵 VNA Server Role Remove Logic
    # ————————————————————————————————

    # ————————————————————————————————
    # 🩵 VNA Member Special Role Removed
    # ————————————————————————————————
    if role_id in SPECIAL_BOOSTER_ROLES or role_id == VN_ALLSTARS_ROLES.staff:
        await market_alert_role_remove_handler(bot, member, role)
    # ————————————————————————————————
    # 🩵 VNA Giveaway Role Remove
    # ————————————————————————————————
    if role_id in GIVEAWAY_ROLES:
        giveaways = await fetch_all_giveaways(bot)
        if not giveaways:
            return
        try:

            await giveaway_role_remove_handler(bot, member, role)
        except Exception as e:
            pretty_log(message=f"Error handling giveaway role remove: {e}", tag="error")
