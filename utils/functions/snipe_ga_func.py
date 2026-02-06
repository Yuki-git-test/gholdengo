import asyncio
import random
import time
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks

import utils.cache.global_variables as globals
from Constants.aesthetic import Thumbnails as Decor_Thumbnails
from Constants.vn_allstars_constants import DEFAULT_EMBED_COLOR, VN_ALLSTARS_ROLES
from utils.logs.pretty_log import pretty_log
from utils.visuals.pretty_defer import pretty_defer

TESTING = True
ALLOWED_JOIN_ROLES = [
    VN_ALLSTARS_ROLES.vna_member,
]
BLACKLISTED_ROLES = [VN_ALLSTARS_ROLES.probation, VN_ALLSTARS_ROLES.clan_break]


allowed_roles_display = ", ".join(f"<@&{role_id}>" for role_id in ALLOWED_JOIN_ROLES)
blaclisted_roles_display = ", ".join(f"<@&{role_id}>" for role_id in BLACKLISTED_ROLES)


def build_snipe_ga_embed(
    host: discord.Member,
    prize: str,
    entries: int = 0,
    ends_at: datetime = None,
    winner: discord.Member = None,
):
    """Builds the embed for the snipe giveaway."""
    ends_text = f"<t:{int(ends_at.timestamp())}:R>" if ends_at else "Unknown"
    color = DEFAULT_EMBED_COLOR
    desc = f"""## SNIPE GIVEAWAY
- Hosted By: {host.mention}
- Prize: {prize}
- Allowed roles: {allowed_roles_display}
- Blacklisted roles: {blaclisted_roles_display}

- **Entries:** {entries}
- **Ends:** {ends_text}
{f"- **Winner:** {winner.mention}" if winner else ""}
"""
    guild = host.guild
    embed = discord.Embed(description=desc, color=color)
    embed.set_thumbnail(url=Decor_Thumbnails.SNIPE_GA_GIFT)
    return embed


class SnipeGAView(discord.ui.View):
    def __init__(self, bot, prize: str, author=None, embed_color=None, timeout=None):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.prize = prize
        self.author = author
        self.host = author
        self.timeout = timeout  # Explicitly store timeout
        self.ends_at = (
            datetime.now() + timedelta(seconds=timeout or 0) if timeout else None
        )
        self.joined_users = set()
        self.message = None
        self.winner = None
        self.embed_color = embed_color
        self.ended = False
        self._timeout_task = asyncio.create_task(self._auto_end())

    async def _auto_end(self):
        try:
            if self.timeout is None or self.timeout == 0:
                return
            await asyncio.sleep(self.timeout)
            if not self.is_finished():
                await self.end_giveaway()
        except Exception as e:
            pretty_log("error", f"SnipeGAView _auto_end error: {e}")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True

    @discord.ui.button(
        label="Join Giveaway 🎉",
        style=discord.ButtonStyle.green,
        custom_id="snipe_ga_join",
    )
    async def join_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        defer = await pretty_defer(interaction=interaction, content="Please wait....")

        try:
            # Prevent late joins
            if self.ended or self.is_finished():
                await defer.error("This giveaway has already ended.")
                return

            member = interaction.user
            member_roles = {r.id for r in member.roles}

            # Exception: allow seafoam role if TESTING is True
            missing_roles = [
                f"<@&{role_id}>"
                for role_id in ALLOWED_JOIN_ROLES
                if role_id not in member_roles
            ]
            has_seafoam = VN_ALLSTARS_ROLES.seafoam in member_roles
            if missing_roles and not (TESTING and has_seafoam):
                await defer.stop(
                    f"❌ You are missing the required roles to join the giveaway: {', '.join(missing_roles)}"
                )
                return

            blacklisted_roles = [
                f"<@&{role_id}>"
                for role_id in BLACKLISTED_ROLES
                if role_id in member_roles
            ]
            if blacklisted_roles:
                await defer.stop(
                    f"❌ You are blacklisted from joining the giveaway due to: {', '.join(blacklisted_roles)}"
                )
                return

            if member.id in self.joined_users:
                await defer.stop("❌ You already joined the giveaway!")
                return

            self.joined_users.add(member.id)
            await defer.success("You successfully joined the giveaway! Good luck! 🎉")

            if self.message is None:
                pretty_log("warn", "JoinButton pressed but self.message is None.")
                return

            new_embed = build_snipe_ga_embed(
                host=self.host,
                prize=self.prize,
                entries=len(self.joined_users),
                ends_at=self.ends_at,
            )
            await self.message.edit(embed=new_embed)

        except Exception as e:
            pretty_log("error", f"JoinButton error: {e}")
            await defer.stop("❌ Something went wrong joining the giveaway.")

    def stop(self):
        try:
            if hasattr(self, "_timeout_task"):
                self._timeout_task.cancel()
        except Exception as e:
            pretty_log("warn", f"Error cancelling _timeout_task: {e}")

        for child in self.children:
            child.disabled = True
        try:
            if self.message:
                asyncio.create_task(self.message.edit(view=self))
        except Exception as e:
            pretty_log("error", f"SnipeGAView stop error: {e}")

        super().stop()

    async def end_giveaway(self, reroll_view=None):
        if self.ended:
            return
        self.ended = True

        if not self.joined_users:
            await self.message.channel.send("😞 No one joined the snipe giveaway.")
            self.stop()
            return

        guild = self.message.guild

        # Random fair selection
        winner_id = random.choice(list(self.joined_users))
        winner = guild.get_member(winner_id)

        if winner is None:
            pretty_log("warn", "No valid winner could be selected in snipe giveaway.")
            await self.message.channel.send("⚠️ No valid winner could be selected.")
            self.stop()
            return

        # Don't remove winner from joined_users, keep for entry count
        self.winner = winner

        updated_embed = build_snipe_ga_embed(
            host=self.host,
            prize=self.prize,
            entries=len(self.joined_users),  # includes winner
            ends_at=self.ends_at,
            winner=self.winner,
        )
        await self.message.edit(embed=updated_embed)

        # Exclude winner from participant list
        joiners_mentions = [
            guild.get_member(uid).mention
            for uid in self.joined_users
            if guild.get_member(uid) and uid != winner_id
        ]

        content = (
            f"🎊 Congrats {winner.mention} 🎊 for winning the **Snipe Giveaway**! 🏆✨"
        )

        desc = f"""### 🏅 Snipe Giveaway Winner:\n🎉 {winner.mention} 🎉\n"""

        participants_desc = "👥 **Participants:**\n" + "\n".join(joiners_mentions)
        full_description = desc + participants_desc

        embed = discord.Embed(
            description=full_description,
            color=discord.Color.gold(),
            timestamp=datetime.now(),
        )
        embed.set_thumbnail(url=Decor_Thumbnails.CELEBRATE)

        await self.message.channel.send(content=content, embed=embed)

        self.stop()
