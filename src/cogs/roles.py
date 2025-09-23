from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class Roles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.autorole_id: int | None = None

    async def cog_load(self) -> None:
        """Load persisted settings when the cog is loaded."""
        try:
            db = self.bot.db  # type: ignore[attr-defined]
            row = await db.fetchone("SELECT value FROM settings WHERE key='autorole_role_id'")
            if row and str(row[0]).isdigit():
                self.autorole_id = int(row[0])
        except Exception:
            # ignore load errors
            pass

    @app_commands.command(name="role-add", description="Выдать роль пользователю")
    @app_commands.default_permissions(manage_roles=True)
    async def role_add(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        guild = interaction.guild
        if not guild:
            return await interaction.response.send_message("Команда работает только на сервере.", ephemeral=True)

        me = guild.me
        if not me or not me.guild_permissions.manage_roles:
            return await interaction.response.send_message("У меня нет права Manage Roles.", ephemeral=True)

        if me.top_role <= role:
            return await interaction.response.send_message("Моя роль ниже выдаваемой. Поднимите роль бота выше.", ephemeral=True)

        if isinstance(interaction.user, discord.Member) and interaction.user.top_role <= role and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Нельзя выдавать роль, которая не ниже вашей.", ephemeral=True)

        try:
            await user.add_roles(role, reason=f"by {interaction.user}")
            await interaction.response.send_message(f"✅ Роль {role.mention} выдана {user.mention}", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Недостаточно прав для выдачи этой роли.", ephemeral=True)
        except Exception:
            await interaction.response.send_message("Не удалось выдать роль. Проверьте иерархию и права.", ephemeral=True)

    @app_commands.command(name="role-remove", description="Убрать роль у пользователя")
    @app_commands.default_permissions(manage_roles=True)
    async def role_remove(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        guild = interaction.guild
        if not guild:
            return await interaction.response.send_message("Команда работает только на сервере.", ephemeral=True)

        me = guild.me
        if not me or not me.guild_permissions.manage_roles:
            return await interaction.response.send_message("У меня нет права Manage Roles.", ephemeral=True)

        if me.top_role <= role:
            return await interaction.response.send_message("Моя роль ниже снимаемой. Поднимите роль бота выше.", ephemeral=True)

        try:
            await user.remove_roles(role, reason=f"by {interaction.user}")
            await interaction.response.send_message(f"✅ Роль {role.mention} снята с {user.mention}", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Недостаточно прав для снятия этой роли.", ephemeral=True)
        except Exception:
            await interaction.response.send_message("Не удалось снять роль. Проверьте иерархию и права.", ephemeral=True)

    @app_commands.command(name="autorole-set", description="Установить роль для авто-выдачи при входе")
    @app_commands.default_permissions(manage_roles=True)
    async def autorole_set(self, interaction: discord.Interaction, role: discord.Role):
        self.autorole_id = role.id
        try:
            db = self.bot.db  # type: ignore[attr-defined]
            await db.exec("INSERT OR REPLACE INTO settings(key, value) VALUES('autorole_role_id', ?)", str(role.id))
        except Exception:
            pass
        await interaction.response.send_message(f"✅ Установлена авто-роль: {role.mention}", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if self.autorole_id:
            role = member.guild.get_role(self.autorole_id)
            if role:
                try:
                    await member.add_roles(role, reason="Autorole")
                except Exception:
                    pass

    # Reaction roles (simplified via one message setup)
    # удалена команда /reaction-role по запросу, функционал оставлен через /reaction-bind

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        db = self.bot.db  # type: ignore[attr-defined]
        row = await db.fetchone("SELECT role_id FROM reaction_roles WHERE message_id=? AND emoji=?", payload.message_id, str(payload.emoji))
        if not row:
            return
        role_id = int(row[0])
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        role = guild.get_role(role_id)
        member = guild.get_member(payload.user_id)
        if role and member and not member.bot:
            try:
                await member.add_roles(role, reason="Reaction role")
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        db = self.bot.db  # type: ignore[attr-defined]
        row = await db.fetchone("SELECT role_id FROM reaction_roles WHERE message_id=? AND emoji=?", payload.message_id, str(payload.emoji))
        if not row:
            return
        role_id = int(row[0])
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        role = guild.get_role(role_id)
        member = guild.get_member(payload.user_id)
        if role and member and not member.bot:
            try:
                await member.remove_roles(role, reason="Reaction role remove")
            except Exception:
                pass

    @app_commands.command(name="reaction-bind", description="Привязать роль к СУЩЕСТВУЮЩЕМУ сообщению по эмодзи")
    @app_commands.default_permissions(manage_roles=True)
    async def reaction_bind(self, interaction: discord.Interaction, message_id: str, emoji: str, role: discord.Role):
        try:
            mid = int(message_id)
        except ValueError:
            return await interaction.response.send_message("Неверный ID сообщения.", ephemeral=True)

        # Проверим сообщение доступно ли реакциям
        channel = interaction.channel
        try:
            msg = await channel.fetch_message(mid) if isinstance(channel, discord.TextChannel) else None
        except Exception:
            msg = None
        if not msg:
            return await interaction.response.send_message("Сообщение не найдено в этом канале.", ephemeral=True)

        try:
            await msg.add_reaction(emoji)
        except Exception:
            return await interaction.response.send_message("Не удалось добавить реакцию. Проверьте эмодзи.", ephemeral=True)

        db = self.bot.db  # type: ignore[attr-defined]
        await db.exec("INSERT OR REPLACE INTO reaction_roles(message_id, emoji, role_id) VALUES(?, ?, ?)", msg.id, str(emoji), role.id)
        await interaction.response.send_message("✅ Привязка создана: реакция выдаёт роль.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Roles(bot))


