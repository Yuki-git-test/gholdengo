# 🧹─────────────────────────────────────────────
# Mini Helper: Cleanup first matching message (log only)
# 🧹─────────────────────────────────────────────
import discord
from discord.ext import commands

from utils.logs.pretty_log import pretty_log


async def cleanup_first_match(
    bot: commands.Bot,
    channel: discord.TextChannel,
    phrase: str,
    component: str,
):
    """
    Scans the last 50 messages of the bot in the given channel.
    If a message matches the phrase in the specified component,
    removes its view and breaks early.

    Logs whether a view was removed or skipped.

    Args:
        bot (commands.Bot): The bot instance.
        channel (discord.TextChannel): Channel to scan.
        phrase (str): Text/phrase to look for.
        component (str): "content", "title", "description", or "footer".
    """
    async for message in channel.history(limit=50, oldest_first=False):
        if message.author != bot.user:
            pretty_log(
                tag="debug",
                message=f"Skipped message {message.id} in {channel.id}: not sent by bot.",
                label="BUTTON CLEANUP",
            )
            continue

        # ✨ Check content/embed for match
        match_found = False
        if component == "content" and phrase in message.content:
            match_found = True
        elif message.embeds:
            for embed in message.embeds:
                if component == "title" and embed.title and phrase in embed.title:
                    match_found = True
                    break
                elif (
                    component == "description"
                    and embed.description
                    and phrase in embed.description
                ):
                    match_found = True
                    break
                elif (
                    component == "footer"
                    and embed.footer
                    and embed.footer.text
                    and phrase in embed.footer.text
                ):
                    match_found = True
                    break

        if match_found:
            try:
                await message.edit(view=None)
                pretty_log(
                    tag="info",
                    message=f"🧹 Removed view from message {message.id} (matched '{phrase}'). Breaking early.",
                    label="BUTTON CLEANUP",
                )
            except Exception as e:
                pretty_log(
                    tag="warn",
                    message=f"⚠️ Failed to remove view from message {message.id}: {e}",
                    label="BUTTON CLEANUP",
                )
            break  # stop after first match
    else:
        pretty_log(
            tag="debug",
            message=f"No matching message found for phrase '{phrase}' in channel {channel.id}.",
            label="BUTTON CLEANUP",
        )
