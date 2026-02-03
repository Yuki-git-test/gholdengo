import discord
from discord.ext import commands

from Constants.vn_allstars_constants import VN_ALLSTARS_ROLES
from utils.logs.pretty_log import pretty_log


# Check if user is staff member
def is_staff_member(member: discord.Member) -> bool:
    """
    Checks if a member has any staff roles.
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
