import re

import discord
from discord import Embed, Interaction, Message, app_commands
from discord.ext import commands

from Constants.vn_allstars_constants import VNA_SERVER_ID
from utils.logs.pretty_log import pretty_log
from utils.essentials.role_checks import *


class EmbedEditModal(discord.ui.Modal):
    def __init__(self, original_embed: discord.Embed, message: discord.Message):
        super().__init__(title="Edit Embed")
        self.message = message

        # ✨ Message content
        self.content_input = discord.ui.TextInput(
            label="Message Content",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            default=message.content or "",
            required=False,
            placeholder="Edit the message text (optional).",
        )
        self.add_item(self.content_input)

        # 📝 Embed description
        self.description_input = discord.ui.TextInput(
            label="Embed Description",
            style=discord.TextStyle.paragraph,
            max_length=4000,
            default=original_embed.description or "",
            required=False,
            placeholder="Edit the embed description (optional).",
        )
        self.add_item(self.description_input)

        # 🎨 Meta: Color, Title, Footer, Author, Icon
        default_color = (
            f"{original_embed.color.value:06X}" if original_embed.color else ""
        )
        default_title = original_embed.title or ""
        default_footer = original_embed.footer.text if original_embed.footer else ""
        default_author = original_embed.author.name if original_embed.author else ""
        default_author_icon = (
            str(original_embed.author.icon_url)
            if (original_embed.author and original_embed.author.icon_url)
            else ""
        )

        # ✅ Always include all fields, empty ones are blank
        default_combo = ",".join(
            [
                default_color,
                default_title,
                default_footer,
                default_author,
                default_author_icon,
            ]
        )

        self.meta_input = discord.ui.TextInput(
            label="Color, Title, Footer, Author, Icon",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            default=default_combo,
            required=False,
            placeholder="Example: C084FC, Giveaway Time!, Don’t miss out!, Wooper, https://example.com/icon.png",
        )
        self.add_item(self.meta_input)

        # 🖼️ Image URL
        self.image_input = discord.ui.TextInput(
            label="Embed Image URL",
            style=discord.TextStyle.short,
            max_length=500,
            default=(
                original_embed.image.url
                if (original_embed.image and original_embed.image.url)
                else ""
            ),
            required=False,
            placeholder="Paste the image URL here (optional).",
        )
        self.add_item(self.image_input)

        # 🖼️ Thumbnail URL
        self.thumbnail_input = discord.ui.TextInput(
            label="Embed Thumbnail URL",
            style=discord.TextStyle.short,
            max_length=500,
            default=(
                original_embed.thumbnail.url
                if (original_embed.thumbnail and original_embed.thumbnail.url)
                else ""
            ),
            required=False,
            placeholder="Paste the thumbnail URL here (optional).",
        )
        self.add_item(self.thumbnail_input)

    async def on_submit(self, interaction: discord.Interaction):
        import traceback

        try:
            # ⏱ Defer response to prevent "application did not respond"
            await interaction.response.defer(ephemeral=True, thinking=True)

            # Split meta input into all 5 fields
            meta_parts = [p.strip() for p in (self.meta_input.value or "").split(",")]
            # Fill missing parts with None
            while len(meta_parts) < 5:
                meta_parts.append(None)

            color_hex, title, footer, author_name, author_icon = meta_parts[:5]

            # Convert color safely
            try:
                color = (
                    discord.Color(int(color_hex, 16))
                    if color_hex
                    else discord.Color.purple()
                )
            except ValueError:
                color = discord.Color.purple()

            new_embed = discord.Embed(
                title=title or None,
                description=(self.description_input.value or "").strip() or None,
                color=color,
            )

            if footer:
                new_embed.set_footer(text=footer)
            if author_name:
                new_embed.set_author(name=author_name, icon_url=author_icon or None)
            if self.image_input.value.strip():
                new_embed.set_image(url=self.image_input.value.strip())
            if self.thumbnail_input.value.strip():
                new_embed.set_thumbnail(url=self.thumbnail_input.value.strip())

            new_content = (self.content_input.value or "").strip() or None

            await self.message.edit(content=new_content, embed=new_embed)
            jump_link = f"https://discord.com/channels/{interaction.guild.id}/{self.message.channel.id}/{self.message.id}"
            await interaction.followup.send(
                f"✅ Message and embed updated successfully! [Jump to message]({jump_link})",
                ephemeral=True,
            )

        except Exception as e:
            traceback.print_exc()
            if interaction.response.is_done():
                await interaction.followup.send(
                    f"❌ Unexpected error: `{e}`", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"❌ Unexpected error: `{e}`", ephemeral=True
                )


async def edit_embed_func(
    bot: commands.Bot, interaction: discord.Interaction, message_link: str
):
    import traceback

    try:
        match = re.search(
            r"https?://(?:canary\.|ptb\.)?discord(?:app)?\.com/channels/\d+/(\d+)/(\d+)",
            message_link,
        )
        if not match:
            await interaction.response.send_message(
                "❌ Invalid message link format.", ephemeral=True
            )
            return

        channel_id = int(match.group(1))
        message_id = int(match.group(2))

        channel = interaction.guild.get_channel(
            channel_id
        ) or await interaction.guild.fetch_channel(channel_id)
        if channel is None:
            await interaction.response.send_message(
                "❌ Could not find the channel from that link.", ephemeral=True
            )
            return

        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            await interaction.response.send_message(
                "❌ Message not found.", ephemeral=True
            )
            return
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to fetch that message.", ephemeral=True
            )
            return

        if not message.embeds:
            await interaction.response.send_message(
                "❌ That message has no embeds.", ephemeral=True
            )
            return

        original_embed = message.embeds[0]

        modal = EmbedEditModal(original_embed=original_embed, message=message)
        await interaction.response.send_modal(modal)

    except Exception as e:
        # Log full traceback to console for debugging
        traceback.print_exc()
        # Ensure the user always gets a response
        if interaction.response.is_done():
            await interaction.followup.send(
                f"❌ Unexpected error while opening modal: `{e}`", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ Unexpected error while opening modal: `{e}`", ephemeral=True
            )
