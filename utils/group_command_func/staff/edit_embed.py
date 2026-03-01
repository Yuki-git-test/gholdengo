import re

import discord
from discord import Embed, Interaction, Message, app_commands
from discord.ext import commands

from Constants.vn_allstars_constants import VNA_SERVER_ID
from utils.essentials.role_checks import *
from utils.logs.pretty_log import pretty_log


class EmbedEditModal(discord.ui.Modal):
    def __init__(self, original_embed: discord.Embed, message: discord.Message):
        super().__init__(title="Edit Embed")
        self.message = message

        # Removed message content input to stay within Discord modal limit

        # 📝 Embed title
        self.title_input = discord.ui.TextInput(
            label="Embed Title",
            style=discord.TextStyle.short,
            max_length=256,
            default=original_embed.title or "",
            required=False,
            placeholder="Edit the embed title (optional).",
        )
        self.add_item(self.title_input)

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

        # 🎨 Embed color
        default_color = (
            f"{original_embed.color.value:06X}" if original_embed.color else ""
        )
        self.color_input = discord.ui.TextInput(
            label="Embed Color (hex)",
            style=discord.TextStyle.short,
            max_length=6,
            default=default_color,
            required=False,
            placeholder="e.g. FFFFFF",
        )
        self.add_item(self.color_input)

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
            await interaction.response.defer(ephemeral=True, thinking=True)

            # Get values from modal
            title = self.title_input.value.strip() or None
            description = self.description_input.value.strip() or None
            color_hex = self.color_input.value.strip()
            image_url = self.image_input.value.strip()
            thumbnail_url = self.thumbnail_input.value.strip()
            # Message content editing removed
            new_content = None

            # Convert color safely
            try:
                color = (
                    discord.Color(int(color_hex, 16))
                    if color_hex
                    else (
                        interaction.message.embeds[0].color
                        if interaction.message.embeds
                        and interaction.message.embeds[0].color
                        else discord.Color.purple()
                    )
                )
            except Exception:
                color = discord.Color.purple()

            # Create new embed and copy fields
            original_embed = self.message.embeds[0] if self.message.embeds else None
            new_embed = discord.Embed(
                title=title,
                description=description,
                color=color,
            )
            if image_url:
                new_embed.set_image(url=image_url)
            if thumbnail_url:
                new_embed.set_thumbnail(url=thumbnail_url)
            # Copy all fields from original embed
            if original_embed:
                for field in original_embed.fields:
                    new_embed.add_field(
                        name=field.name, value=field.value, inline=field.inline
                    )
                # Preserve footer text and icon
                if original_embed.footer and original_embed.footer.text:
                    icon_url = (
                        original_embed.footer.icon_url
                        if hasattr(original_embed.footer, "icon_url")
                        else None
                    )
                    new_embed.set_footer(
                        text=original_embed.footer.text, icon_url=icon_url
                    )

            await self.message.edit(embed=new_embed)
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
