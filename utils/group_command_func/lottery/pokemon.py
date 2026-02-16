import discord
from utils.logs.pretty_log import pretty_log
from discord.ext import commands

async def pokemon_lottery_func(
        bot:commands.Bot,
        interaction: discord.Interaction,
        duration: str,
        cost_per_ticket: str,
        max_tickets: str = None,
):
    pass