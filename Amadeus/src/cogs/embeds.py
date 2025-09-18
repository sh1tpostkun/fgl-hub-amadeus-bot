from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class EmbedModal(discord.ui.Modal, title="Создать Embed"):
    title_input = discord.ui.TextInput(label="Заголовок", max_length=256, required=True)
    description_input = discord.ui.TextInput(label="Описание", style=discord.TextStyle.paragraph, required=True)
    color_input = discord.ui.TextInput(label="Цвет HEX (например, #5865F2)", required=False)
    image_url_input = discord.ui.TextInput(label="URL картинки (опционально)", required=False)
    thumbnail_url_input = discord.ui.TextInput(label="URL миниатюры (опционально)", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        color = discord.Color.blurple()
        if self.color_input.value:
            try:
                color = discord.Color(int(self.color_input.value.replace("#", ""), 16))
            except Exception:
                pass
        embed = discord.Embed(title=self.title_input.value, description=self.description_input.value, color=color)
        if self.image_url_input.value:
            embed.set_image(url=self.image_url_input.value)
        if self.thumbnail_url_input.value:
            embed.set_thumbnail(url=self.thumbnail_url_input.value)
        await interaction.response.send_message(embed=embed)


class EditEmbedModal(discord.ui.Modal, title="Редактировать Embed"):
    def __init__(self, message: discord.Message, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        # Заполняем поля текущими значениями
        if message.embeds:
            embed = message.embeds[0]
            self.title_input.default = embed.title or ""
            self.description_input.default = embed.description or ""
            self.color_input.default = f"#{embed.color.value:06x}" if embed.color else ""
            self.image_url_input.default = embed.image.url if embed.image else ""
            self.thumbnail_url_input.default = embed.thumbnail.url if embed.thumbnail else ""

    title_input = discord.ui.TextInput(label="Заголовок", max_length=256, required=True)
    description_input = discord.ui.TextInput(label="Описание", style=discord.TextStyle.paragraph, required=True)
    color_input = discord.ui.TextInput(label="Цвет HEX (например, #5865F2)", required=False)
    image_url_input = discord.ui.TextInput(label="URL картинки (опционально)", required=False)
    thumbnail_url_input = discord.ui.TextInput(label="URL миниатюры (опционально)", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            color = discord.Color.blurple()
            if self.color_input.value:
                try:
                    color = discord.Color(int(self.color_input.value.replace("#", ""), 16))
                except Exception:
                    pass
            
            embed = discord.Embed(title=self.title_input.value, description=self.description_input.value, color=color)
            if self.image_url_input.value:
                embed.set_image(url=self.image_url_input.value)
            if self.thumbnail_url_input.value:
                embed.set_thumbnail(url=self.thumbnail_url_input.value)
            embed.timestamp = discord.utils.utcnow()
            
            # Редактируем сообщение
            await self.message.edit(embed=embed)
            await interaction.response.send_message("✅ Embed сообщение отредактировано!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка при редактировании: {str(e)}", ephemeral=True)


class Embeds(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # удалена команда /embed по запросу (оставлена только /embed-modal)

    @app_commands.command(name="embed-modal", description="Открыть модальное окно для embed")
    async def embed_modal(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EmbedModal())

    @app_commands.command(name="edit-embed", description="Редактировать embed сообщение бота")
    @app_commands.describe(message_id="ID сообщения с embed для редактирования")
    async def edit_embed(self, interaction: discord.Interaction, message_id: str):
        """Редактировать embed сообщение бота по ID сообщения"""
        try:
            # Парсим ID сообщения
            try:
                msg_id = int(message_id)
            except ValueError:
                if interaction.response.is_done():
                    await interaction.followup.send("❌ Неверный формат ID сообщения.", ephemeral=True)
                else:
                    await interaction.response.send_message("❌ Неверный формат ID сообщения.", ephemeral=True)
                return

            # Получаем сообщение
            try:
                message = await interaction.channel.fetch_message(msg_id)
            except discord.NotFound:
                if interaction.response.is_done():
                    await interaction.followup.send("❌ Сообщение не найдено.", ephemeral=True)
                else:
                    await interaction.response.send_message("❌ Сообщение не найдено.", ephemeral=True)
                return
            except discord.Forbidden:
                if interaction.response.is_done():
                    await interaction.followup.send("❌ Нет прав для доступа к сообщению.", ephemeral=True)
                else:
                    await interaction.response.send_message("❌ Нет прав для доступа к сообщению.", ephemeral=True)
                return

            # Проверяем, что это сообщение бота
            if message.author != self.bot.user:
                if interaction.response.is_done():
                    await interaction.followup.send("❌ Можно редактировать только сообщения этого бота.", ephemeral=True)
                else:
                    await interaction.response.send_message("❌ Можно редактировать только сообщения этого бота.", ephemeral=True)
                return

            # Проверяем, что в сообщении есть embed
            if not message.embeds:
                if interaction.response.is_done():
                    await interaction.followup.send("❌ В сообщении нет embed для редактирования.", ephemeral=True)
                else:
                    await interaction.response.send_message("❌ В сообщении нет embed для редактирования.", ephemeral=True)
                return

            # Открываем модальное окно для редактирования
            try:
                await interaction.response.send_modal(EditEmbedModal(message))
            except discord.NotFound:
                # Взаимодействие истекло
                if interaction.response.is_done():
                    await interaction.followup.send("❌ Взаимодействие истекло. Попробуйте снова выполнить команду.", ephemeral=True)
                else:
                    # Если ещё не отвечали, пробуем ответить сообщением
                    await interaction.response.send_message("❌ Взаимодействие истекло. Попробуйте снова выполнить команду.", ephemeral=True)

        except Exception as e:
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ Произошла ошибка: {str(e)}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Произошла ошибка: {str(e)}", ephemeral=True)

    @app_commands.command(name="edit-embed-reply", description="Редактировать embed в ответе на сообщение")
    async def edit_embed_reply(self, interaction: discord.Interaction):
        """Редактировать embed в ответе на сообщение (используйте как ответ на сообщение бота)"""
        try:
            # Получаем сообщение, на которое отвечают
            if not interaction.message:
                if interaction.response.is_done():
                    await interaction.followup.send("❌ Используйте эту команду как ответ на сообщение бота.", ephemeral=True)
                else:
                    await interaction.response.send_message("❌ Используйте эту команду как ответ на сообщение бота.", ephemeral=True)
                return

            message = interaction.message

            # Проверяем, что это сообщение бота
            if message.author != self.bot.user:
                if interaction.response.is_done():
                    await interaction.followup.send("❌ Можно редактировать только сообщения этого бота.", ephemeral=True)
                else:
                    await interaction.response.send_message("❌ Можно редактировать только сообщения этого бота.", ephemeral=True)
                return

            # Проверяем, что в сообщении есть embed
            if not message.embeds:
                if interaction.response.is_done():
                    await interaction.followup.send("❌ В сообщении нет embed для редактирования.", ephemeral=True)
                else:
                    await interaction.response.send_message("❌ В сообщении нет embed для редактирования.", ephemeral=True)
                return

            # Открываем модальное окно для редактирования
            try:
                await interaction.response.send_modal(EditEmbedModal(message))
            except discord.NotFound:
                if interaction.response.is_done():
                    await interaction.followup.send("❌ Взаимодействие истекло. Попробуйте снова выполнить команду.", ephemeral=True)
                else:
                    await interaction.response.send_message("❌ Взаимодействие истекло. Попробуйте снова выполнить команду.", ephemeral=True)

        except Exception as e:
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ Произошла ошибка: {str(e)}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Произошла ошибка: {str(e)}", ephemeral=True)

    # Префикс-команда: создать embed без плашки. Формат: !embed Заголовок | часть1 | часть2 | ...
    @commands.command(name="embed")
    @commands.has_guild_permissions(manage_guild=True)
    async def embed_prefix(self, ctx: commands.Context, *, text: str):
        try:
            # Удаляем исходное сообщение с командой
            try:
                await ctx.message.delete()
            except Exception:
                pass

            parts = [p.strip() for p in text.split("|")] if text else []
            if not parts:
                return

            title = parts[0][:256]
            description = "\n\n".join(parts[1:]).strip() if len(parts) > 1 else ""

            # Лимит Discord: 4096 символов на описание. Если больше — разбиваем на несколько embed.
            chunks: list[str] = []
            if description:
                current = []
                current_len = 0
                for segment in description.split("\n"):
                    # +1 за перенос строки при объединении
                    seg_len = len(segment) + (1 if current else 0)
                    if current_len + seg_len > 4096:
                        chunks.append("\n".join(current))
                        current = [segment]
                        current_len = len(segment)
                    else:
                        if current:
                            current.append(segment)
                            current_len += len(segment) + 1
                        else:
                            current = [segment]
                            current_len = len(segment)
                if current:
                    chunks.append("\n".join(current))
            else:
                chunks = [""]

            color = discord.Color.blurple()

            # Первый embed — с заголовком, последующие — только с продолжением описания
            embeds: list[discord.Embed] = []
            for idx, chunk in enumerate(chunks):
                if idx == 0:
                    e = discord.Embed(title=title, description=chunk, color=color)
                else:
                    e = discord.Embed(description=chunk, color=color)
                embeds.append(e)

            # Отправка одним сообщением, если возможно, иначе по очереди
            if len(embeds) == 1:
                await ctx.send(embed=embeds[0])
            else:
                await ctx.send(embed=embeds[0])
                for e in embeds[1:]:
                    await ctx.send(embed=e)
        except Exception as e:
            await ctx.reply(f"❌ Ошибка: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Embeds(bot))


