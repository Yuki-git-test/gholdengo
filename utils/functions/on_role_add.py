from datetime import datetime

import discord
from discord.ext import commands

from Constants.vn_allstars_constants import (
    VN_ALLSTARS_ROLES,
    VN_ALLSTARS_TEXT_CHANNELS,
    VNA_SERVER_ID,
)
from utils.db.market_alert_user import fetch_market_alert_user, set_max_alerts
from utils.group_command_func.markert_alert.add import determine_max_alerts
from utils.logs.pretty_log import pretty_log

from .market_alert_role_handler import market_alert_role_add_handler

LOG_CHANNEL_ID = VN_ALLSTARS_TEXT_CHANNELS.member_logs
SPECIAL_BOOSTER_ROLES = [
    VN_ALLSTARS_ROLES.server_booster,
    VN_ALLSTARS_ROLES.top_monthly_grinder,
    VN_ALLSTARS_ROLES.shiny_donator,
    VN_ALLSTARS_ROLES.legendary_donator,
    VN_ALLSTARS_ROLES.diamond_donator,
]


# 🍭──────────────────────────────
#   🎀 Event: On Role Add
# 🍭──────────────────────────────
async def handle_role_add(
    bot: discord.Client,
    member: discord.Member,
    role: discord.Role,
):
    """Handle role addition events."""
    role_id = role.id

    # ————————————————————————————————
    # 🩵 VNA Market Alert Role Add
    # ————————————————————————————————
    if role_id in SPECIAL_BOOSTER_ROLES or role_id == VN_ALLSTARS_ROLES.staff:
        await market_alert_role_add_handler(bot, member, role)
