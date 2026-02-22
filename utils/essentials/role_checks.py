import discord
from discord.ext import commands
from discord import app_commands
from Constants.vn_allstars_constants import VN_ALLSTARS_ROLES, KHY_USER_ID
from utils.logs.pretty_log import pretty_log


# 🌸──────────────────────────────────────────────────────
# ✨ Custom Exceptions (Sparkles & Cute!) ✨
# ───────────────────────────────────────────────────────
class AuctioneerCheckFailure(app_commands.CheckFailure):
    pass


class VNAStaffCheckFailure(app_commands.CheckFailure):
    pass


# 🌸──────────────────────────────────────────────────────
# 🐾💫 Cute Error Messages by Server — Cottagecore Style 💫🌿
# ───────────────────────────────────────────────────────
ERROR_MESSAGES = {
    "auctioneer": "Only Auctioneers can use this command! If you think this is a mistake, please contact a Staff member.",
    "vna_staff": "Only VNA Staff can use this command! If you think this is a mistake, please contact a Staff member.",
}

# 🌸──────────────────────────────────────────────────────
# 🔹 Helper function
# ───────────────────────────────────────────────────────
def has_role(user_roles, role_id):
    """Check if user has a role ID"""
    return role_id in [role.id for role in user_roles]


# 🌸──────────────────────────────────────────────────────
# 🔹 Slash command decorators
# ───────────────────────────────────────────────────────
def vna_staff():
    async def predicate(interaction: discord.Interaction):
        # Allow khy (user id: 952071312124313611)
        if getattr(interaction.user, "id", None) == KHY_USER_ID:
            return True
        if not has_role(interaction.user.roles, VN_ALLSTARS_ROLES.staff):
            raise VNAStaffCheckFailure(ERROR_MESSAGES["vna_staff"])
        return True

    return app_commands.check(predicate)


# Check if user is staff member
def is_staff_member(member: discord.Member) -> bool:
    """
    Checks if a member has any vna staff roles.
    """
    staff_role_ids = [VN_ALLSTARS_ROLES.staff, VN_ALLSTARS_ROLES.seafoam]
    if any(role.id in staff_role_ids for role in member.roles):
        return True
    return False


# Check if user has special roles
def has_special_role(member: discord.Member) -> bool:
    """
    Checks if a member has any special roles.
    """
    special_role_ids = [
        VN_ALLSTARS_ROLES.staff,
        VN_ALLSTARS_ROLES.seafoam,
        VN_ALLSTARS_ROLES.server_booster,
        VN_ALLSTARS_ROLES.top_monthly_grinder,
        VN_ALLSTARS_ROLES.shiny_donator,
        VN_ALLSTARS_ROLES.legendary_donator,
        VN_ALLSTARS_ROLES.diamond_donator,
    ]
    if any(role.id in special_role_ids for role in member.roles):
        return True
    return False
