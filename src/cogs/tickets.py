from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
import typing as t


class TicketButton(discord.ui.View):
    def __init__(self, bot: commands.Bot, category_id: int | None = None, support_role_id: int | None = None):
        super().__init__(timeout=None)
        self.bot = bot
        self.category_id = category_id
        self.support_role_id = support_role_id

    @discord.ui.button(label="Создать тикет", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        if not guild:
            return await interaction.response.send_message("Эта команда работает только на сервере.", ephemeral=True)

        # Проверяем, есть ли уже открытый тикет у пользователя
        db = self.bot.db  # type: ignore[attr-defined]
        existing = await db.fetchone("SELECT channel_id FROM tickets WHERE owner_id=?", interaction.user.id)
        if existing:
            channel = guild.get_channel(existing[0])
            if channel:
                return await interaction.response.send_message(f"У вас уже есть открытый тикет: {channel.mention}", ephemeral=True)

        # Создаем приватный канал только в заранее заданной категории
        if not self.category_id:
            return await interaction.response.send_message(
                "Категория для тикетов не настроена. Используйте /ticket setup.", ephemeral=True
            )
        category = guild.get_channel(self.category_id)
        if not isinstance(category, discord.CategoryChannel):
            return await interaction.response.send_message(
                "Указанная категория не найдена. Проверьте /ticket setup.", ephemeral=True
            )

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        if self.support_role_id:
            role = guild.get_role(self.support_role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=category,
            overwrites=overwrites,
            reason=f"Ticket for {interaction.user}",
        )

        # Сохраняем в БД
        await db.exec("INSERT OR REPLACE INTO tickets(channel_id, owner_id) VALUES(?, ?)", channel.id, interaction.user.id)

        # Отправляем приветственное сообщение
        embed = discord.Embed(
            title="🎫 Тикет создан",
            description=f"Привет, {interaction.user.mention}!\n\nОпишите вашу проблему, и мы поможем вам как можно скорее.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"ID: {interaction.user.id}")
        embed.timestamp = discord.utils.utcnow()

        close_view = CloseTicketView()
        await channel.send(embed=embed, view=close_view)
        await interaction.response.send_message(f"✅ Тикет создан: {channel.mention}", ephemeral=True)


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Закрыть тикет", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return

        # Проверяем права
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("У вас нет прав для закрытия тикетов.", ephemeral=True)

        await interaction.response.send_message("🔒 Тикет закрывается...", ephemeral=True)

        # подготовим лог и удалим канал через 5 сек
        db = interaction.client.db  # type: ignore[attr-defined]
        guild = interaction.guild
        log_channel_id_row = await db.fetchone("SELECT value FROM settings WHERE key='tickets_closed_channel_id'")
        log_channel = None
        if log_channel_id_row and guild:
            log_channel = guild.get_channel(int(log_channel_id_row[0]))

        embed = discord.Embed(
            title="🔒 Тикет закрыт",
            description=f"Канал: {channel.mention}\nЗакрыл: {interaction.user.mention}",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow(),
        )
        if isinstance(channel, discord.TextChannel):
            last_msgs = []
            try:
                async for m in channel.history(limit=10, oldest_first=False):
                    if m.author.bot:
                        continue
                    last_msgs.append(f"{m.author.display_name}: {m.content[:120]}")
            except Exception:
                pass
            if last_msgs:
                embed.add_field(name="Последние сообщения", value="\n".join(reversed(last_msgs)), inline=False)

        # немедленное закрытие

        # Удаляем из БД
        await db.exec("DELETE FROM tickets WHERE channel_id=?", channel.id)

        # Отправляем лог
        if isinstance(log_channel, discord.TextChannel):
            try:
                await log_channel.send(embed=embed)
            except Exception:
                pass

        # Удаляем канал
        try:
            await channel.delete(reason=f"Ticket closed by {interaction.user}")
        except Exception:
            pass


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.category_id: int | None = None  # optional: preset category
        self.support_role_id: int | None = None

    ticket = app_commands.Group(name="ticket", description="Система тикетов")

    @ticket.command(name="setup", description="Настроить систему тикетов (категория, роль поддержки)")
    @app_commands.default_permissions(manage_channels=True)
    async def setup(self, interaction: discord.Interaction, category: t.Optional[discord.CategoryChannel] = None, support_role: t.Optional[discord.Role] = None):
        if category:
            self.category_id = category.id
        if support_role:
            self.support_role_id = support_role.id
        # persist settings in DB for persistence views
        db = self.bot.db  # type: ignore[attr-defined]
        if self.category_id:
            await db.exec("INSERT OR REPLACE INTO settings(key, value) VALUES('tickets_category_id', ?)", str(self.category_id))
        if self.support_role_id:
            await db.exec("INSERT OR REPLACE INTO settings(key, value) VALUES('tickets_support_role_id', ?)", str(self.support_role_id))
        await interaction.response.send_message("✅ Настройки тикетов сохранены.", ephemeral=True)

    @ticket.command(name="set-closed-channel", description="Указать канал для логов закрытых тикетов")
    @app_commands.default_permissions(manage_channels=True)
    async def set_closed_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        db = self.bot.db  # type: ignore[attr-defined]
        await db.exec("INSERT OR REPLACE INTO settings(key, value) VALUES('tickets_closed_channel_id', ?)", str(channel.id))
        await interaction.response.send_message(f"✅ Канал для закрытых тикетов: {channel.mention}", ephemeral=True)

    @ticket.command(name="close", description="Закрыть тикет")
    async def close(self, interaction: discord.Interaction):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("Эта команда доступна только в текстовом канале.", ephemeral=True)
        db = self.bot.db  # type: ignore[attr-defined]
        row = await db.fetchone("SELECT owner_id FROM tickets WHERE channel_id=?", channel.id)
        if not row:
            return await interaction.response.send_message("Этот канал не является тикетом.", ephemeral=True)
        await db.exec("DELETE FROM tickets WHERE channel_id=?", channel.id)
        await interaction.response.send_message("🔒 Канал будет удалён через 5 секунд.", ephemeral=True)
        await discord.utils.sleep_until(discord.utils.utcnow() + discord.utils.timedelta(seconds=5))
        await channel.delete(reason=f"Ticket closed by {interaction.user}")

    @ticket.command(name="add", description="Добавить участника в тикет")
    async def add(self, interaction: discord.Interaction, user: discord.Member):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("Эта команда доступна только в текстовом канале.", ephemeral=True)
        overwrite = channel.overwrites_for(user)
        overwrite.view_channel = True
        overwrite.send_messages = True
        await channel.set_permissions(user, overwrite=overwrite, reason=f"Ticket add by {interaction.user}")
        await interaction.response.send_message(f"👤 {user.mention} добавлен в тикет.", ephemeral=True)

    @ticket.command(name="remove", description="Убрать участника из тикета")
    async def remove(self, interaction: discord.Interaction, user: discord.Member):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("Эта команда доступна только в текстовом канале.", ephemeral=True)
        await channel.set_permissions(user, overwrite=None, reason=f"Ticket remove by {interaction.user}")
        await interaction.response.send_message(f"🚫 {user.mention} убран из тикета.", ephemeral=True)

    @ticket.command(name="panel", description="Создать панель тикетов с кнопкой")
    @app_commands.default_permissions(manage_channels=True)
    async def create_panel(self, interaction: discord.Interaction, title: str, description: str, channel: t.Optional[discord.TextChannel] = None):
        """Создает красивое embed-сообщение с кнопкой для создания тикетов"""
        target_channel = channel or interaction.channel
        if not isinstance(target_channel, discord.TextChannel):
            return await interaction.response.send_message("Укажите текстовый канал.", ephemeral=True)

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Нажмите кнопку ниже, чтобы создать тикет")
        embed.timestamp = discord.utils.utcnow()

        view = TicketButton(self.bot, self.category_id, self.support_role_id)
        await target_channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ Панель тикетов создана в {target_channel.mention}", ephemeral=True)

    @app_commands.command(name="create", description="Создать тикет")
    async def create_ticket(self, interaction: discord.Interaction, topic: str):
        guild = interaction.guild
        assert guild is not None
        if not self.category_id:
            return await interaction.response.send_message(
                "Категория для тикетов не настроена. Используйте /ticket setup.", ephemeral=True
            )
        category = guild.get_channel(self.category_id)
        if not isinstance(category, discord.CategoryChannel):
            return await interaction.response.send_message(
                "Указанная категория не найдена. Проверьте /ticket setup.", ephemeral=True
            )
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        if self.support_role_id:
            role = guild.get_role(self.support_role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=category,
            overwrites=overwrites,
            reason=f"Ticket for {interaction.user} | {topic}",
        )

        db = self.bot.db  # type: ignore[attr-defined]
        await db.exec("INSERT OR REPLACE INTO tickets(channel_id, owner_id) VALUES(?, ?)", channel.id, interaction.user.id)

        embed = discord.Embed(title="Тикет создан", description=topic, color=discord.Color.green())
        embed.add_field(name="Автор", value=interaction.user.mention)
        close_view = CloseTicketView()
        await channel.send(embed=embed, view=close_view)
        await interaction.response.send_message(f"✅ Создан канал {channel.mention}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))


