import discord

from utils.cache.global_variables import bank_msg_count
from utils.group_command_func.donation.update_leaderboard import (
    create_leaderboard_embed,
)
from utils.logs.pretty_log import pretty_log

BANK_MSG_THRESHOLD = 2
STICKY_MSG_DELAY = 10  # seconds


async def check_and_send_sticky_msg(bot: discord.Client, message: discord.Message):
    bank_msg_count.append(message.channel.id)
    total_messages = len(bank_msg_count)

    if total_messages >= BANK_MSG_THRESHOLD:
        pretty_log(
            message=f"Channel {message.channel.name} has reached {total_messages} messages. Sending sticky message.",
            tag="donation_sticky_msg",
        )
        # Reset the count for the channel
        bank_msg_count.clear()
        # Create and send the sticky message
        embed = await create_leaderboard_embed(bot, message.guild, context="total")

        # Delete the old sticky message if it exists
        async for msg in message.channel.history(limit=100):
            if (
                msg.author == bot.user
                and msg.embeds
                and msg.embeds[0].title == "🏆 Overall Donation Leaderboard"
            ):
                await msg.delete()
                pretty_log(
                    message=f"Deleted old sticky message in channel {message.channel.name}.",
                    tag="donation_sticky_msg",
                )
                break
        await message.channel.send(embed=embed)
        pretty_log(
            message=f"Sent new sticky message in channel {message.channel.name}.",
            tag="success",
        )
