import discord

from Constants.aesthetic import *
from Constants.giveaway import ALLOWED_JOIN_ROLES, BLACKLISTED_ROLES, Extra_Entries
from Constants.vn_allstars_constants import (
    KHY_USER_ID,
    VN_ALLSTARS_EMOJIS,
    VN_ALLSTARS_ROLES,
    VN_ALLSTARS_TEXT_CHANNELS,
    VNA_SERVER_ID,
    YUKI_USER_ID,
)
from utils.cache.cache_list import vna_members_cache
from utils.db.ga_db import fetch_all_giveaway_by_type, fetch_giveaway_by_id
from utils.db.ga_entry_db import (
    delete_all_user_ga_rows,
    delete_ga_entry,
    fetch_all_user_ga_entries,
    update_ga_entry,
)
from utils.logs.debug_log import debug_log, enable_debug
from utils.logs.pretty_log import pretty_log
from utils.visuals.design_embed import design_embed
from utils.visuals.thumbnails import random_ga_thumbnail_url


async def send_ga_info_dm(member: discord.Member, embed: discord.Embed):
    # Try to send DM to user with giveaway info
    try:
        await member.send(embed=embed)
    except discord.Forbidden:
        pretty_log(
            message=(
                f"Could not send giveaway info DM to member '{member.display_name}' "
                f"(ID: {member.id}) due to closed DMs."
            ),
            tag="info",
            label="Giveaway Info DM",
        )
        # Fallback -send message to personal channel or public channel
        vna_member_info = vna_members_cache.get(member.id)
        personal_channel_id = (
            vna_member_info.get("channel_id") if vna_member_info else None
        )
        public_channel_id = VN_ALLSTARS_TEXT_CHANNELS.off_topic
        channel_id = personal_channel_id or public_channel_id
        channel = member.guild.get_channel(channel_id)
        if channel:
            try:
                content = f"{member.mention}, I couldn't DM you the giveaway info, so I'm sending it here instead."
                await channel.send(content=content, embed=embed)
            except Exception as e:
                pretty_log(
                    message=(
                        f"Failed to send giveaway info message in fallback channel for member '{member.display_name}' "
                        f"(ID: {member.id}). Error: {e}"
                    ),
                    tag="error",
                    label="Giveaway Info DM Fallback",
                )


async def giveaway_role_add_handler(
    bot: discord.Client,
    member: discord.Member,
    role: discord.Role,
):
    # Handle blacklisted role - remove giveaway entries and send DM
    if role.id in BLACKLISTED_ROLES:
        giveaways = await delete_all_user_ga_rows(bot, member.id)
        if not giveaways:
            return

        giveaway_links = []
        for giveaway in giveaways:
            ga_info = await fetch_giveaway_by_id(
                bot, giveaway
            )  # Ensure giveaway still exists
            if not ga_info:
                continue
            giveaway_links.append(
                f"[- Giveaway ID {giveaway}](https://discord.com/channels/{VNA_SERVER_ID}/{ga_info['channel_id']}/{ga_info['message_id']})"
            )
        giveaway_links_text = (
            "\n".join(giveaway_links) if giveaway_links else "No active giveaways"
        )
        embed = discord.Embed(
            title="Giveaway Entry Removal",
            description=(
                f"You have been removed from the following giveaways due to receiving the {role.name} role:\n"
                f"{giveaway_links_text}\n\n"
                "If you believe this is a mistake, please contact the staff team."
            ),
            color=discord.Color.red(),
        )
        embed = design_embed(embed=embed, user=member)
        await send_ga_info_dm(member, embed)

    # Handle extra entries role - update giveaway entry with new extra entries
    elif role.id in Extra_Entries:
        entry_number = Extra_Entries[role.id]
        user_giveaway_entries = await fetch_all_user_ga_entries(bot, member.id)
        if not user_giveaway_entries:
            return
        update_line_list = []
        for entry in user_giveaway_entries:
            giveaway_id = entry["giveaway_id"]
            ga_info = await fetch_giveaway_by_id(
                bot, giveaway_id
            )  # Ensure giveaway still exists
            if not ga_info:
                continue
            message_id = ga_info["message_id"]
            channel_id = ga_info["channel_id"]
            message_link = f"https://discord.com/channels/{VNA_SERVER_ID}/{channel_id}/{message_id}"
            old_entry_number = entry["entry_count"]
            new_entry_number = old_entry_number + entry_number
            await update_ga_entry(
                bot, entry["giveaway_id"], member.id, new_entry_number
            )
            update_line = f"- [Giveaway ID {entry['giveaway_id']}]({message_link}): {old_entry_number} entries → {new_entry_number} entries"
            update_line_list.append(update_line)

        desc = f"Your giveaway entries have been updated due to receiving the '{role.name}' role. You now have {entry_number} extra entries in each giveaway you're entered in.\n\n"
        desc += "Updated Giveaways:\n" + "\n".join(update_line_list)
        embed = discord.Embed(
            title="Giveaway Entry Update",
            description=desc,
            color=discord.Color.green(),
        )
        embed = design_embed(
            embed=embed, user=member, thumbnail_url=random_ga_thumbnail_url()
        )
        await send_ga_info_dm(member, embed)
    else:
        return


async def giveaway_role_remove_handler(
    bot: discord.Client,
    member: discord.Member,
    role: discord.Role,
):
    # Handle if allowed join role is removed - send DM to user
    if role.id in ALLOWED_JOIN_ROLES:
        if role.id == VN_ALLSTARS_ROLES.vna_member:
            giveaway_type = "clan"
        elif role.id == VN_ALLSTARS_ROLES.server_booster:
            giveaway_type = "server_booster"
        type_giveaways = await fetch_all_giveaway_by_type(bot, giveaway_type)
        if not type_giveaways:
            return

        giveaway_links = []
        for giveaway in type_giveaways:
            giveaway_id = giveaway["giveaway_id"]
            channel_id = giveaway["channel_id"]
            message_id = giveaway["message_id"]
            message_link = f"https://discord.com/channels/{VNA_SERVER_ID}/{channel_id}/{message_id}"
            await delete_ga_entry(bot, giveaway_id, member.id)

            giveaway_line = f"[- Giveaway ID {giveaway['giveaway_id']}](https://discord.com/channels/{VNA_SERVER_ID}/{giveaway['channel_id']}/{giveaway['message_id']})"
            giveaway_links.append(giveaway_line)

        giveaway_links_text = (
            "\n".join(giveaway_links) if giveaway_links else "No active giveaways"
        )
        embed = discord.Embed(
            title="Giveaway Entry Removal",
            description=(
                f"You have been removed from the following giveaways due to losing the {role.name} role:\n"
                f"{giveaway_links_text}\n\n"
                "If you believe this is a mistake, please contact the staff team."
            ),
            color=discord.Color.red(),
        )
        embed = design_embed(embed=embed, user=member)
        await send_ga_info_dm(member, embed)

    # Handle extra entries role removed - update giveaway entry with new reduced entries
    elif role.id in Extra_Entries:
        entry_number = Extra_Entries[role.id]
        user_giveaway_entries = await fetch_all_user_ga_entries(bot, member.id)
        if not user_giveaway_entries:
            return
        update_line_list = []
        for entry in user_giveaway_entries:
            giveaway_id = entry["giveaway_id"]
            ga_info = await fetch_giveaway_by_id(
                bot, giveaway_id
            )  # Ensure giveaway still exists
            if not ga_info:
                continue
            message_id = ga_info["message_id"]
            channel_id = ga_info["channel_id"]
            message_link = f"https://discord.com/channels/{VNA_SERVER_ID}/{channel_id}/{message_id}"
            old_entry_number = entry["entry_count"]
            new_entry_number = max(0, old_entry_number - entry_number)
            await update_ga_entry(
                bot, entry["giveaway_id"], member.id, new_entry_number
            )
            update_line = f"- [Giveaway ID {entry['giveaway_id']}]({message_link}): {old_entry_number} entries → {new_entry_number} entries"
            update_line_list.append(update_line)

        desc = f"Your giveaway entries have been updated due to losing the '{role.name}' role. You have lost {entry_number} extra entries in each giveaway you're entered in.\n\n"
        desc += "Updated Giveaways:\n" + "\n".join(update_line_list)
        embed = discord.Embed(
            title="Giveaway Entry Update",
            description=desc,
            color=discord.Color.orange(),
        )
        embed = design_embed(
            embed=embed, user=member, thumbnail_url=random_ga_thumbnail_url()
        )
        await send_ga_info_dm(member, embed)
    else:
        return
