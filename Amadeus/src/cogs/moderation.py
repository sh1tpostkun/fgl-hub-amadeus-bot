from __future__ import annotations

import discord
from datetime import timedelta
from discord import app_commands
from discord.ext import commands
import logging


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log = logging.getLogger(__name__)

    @app_commands.command(name="kick", description="Исключить участника")
    @app_commands.describe(user="Кого кикнуть", reason="Причина")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str | None = None):
        await user.kick(reason=reason)
        await interaction.response.send_message(f"✅ {user.mention} кикнут. Причина: {reason or 'не указана'}", ephemeral=True)
        await self._log_action("kick", user.id, interaction.user.id, reason)

    @app_commands.command(name="ban", description="Забанить участника")
    @app_commands.describe(user="Кого забанить", reason="Причина", delete_message_days="Удалить сообщения за N дней")
    @app_commands.default_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str | None = None,
        delete_message_days: app_commands.Range[int, 0, 7] = 0,
    ):
        await interaction.guild.ban(user, reason=reason, delete_message_days=delete_message_days)
        await interaction.response.send_message(
            f"🔨 {user.mention} забанен. Причина: {reason or 'не указана'}", ephemeral=True
        )
        await self._log_action("ban", user.id, interaction.user.id, reason)

    @app_commands.command(name="mute", description="Временный мут участника")
    @app_commands.describe(user="Кого замьютить", minutes="На сколько минут", reason="Причина")
    @app_commands.default_permissions(moderate_members=True)
    async def mute(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        minutes: app_commands.Range[int, 1, 10080],
        reason: str | None = None,
    ):
        duration = discord.utils.utcnow() + timedelta(minutes=minutes)
        await user.edit(timed_out_until=duration, reason=reason)
        await interaction.response.send_message(
            f"🤐 {user.mention} замьючен на {minutes} минут. Причина: {reason or 'не указана'}",
            ephemeral=True,
        )
        await self._log_action("mute", user.id, interaction.user.id, reason)

    @app_commands.command(name="warn", description="Выдать предупреждение участнику")
    @app_commands.describe(user="Кому выдать", reason="Причина")
    @app_commands.default_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str | None = None):
        db = self.bot.db  # type: ignore[attr-defined]
        row = await db.fetchone("SELECT count FROM warns WHERE user_id=?", user.id)
        current = row[0] if row else 0
        new_count = current + 1
        if row:
            await db.exec("UPDATE warns SET count=? WHERE user_id=?", new_count, user.id)
        else:
            await db.exec("INSERT INTO warns(user_id, count) VALUES(?, ?)", user.id, new_count)
        await interaction.response.send_message(
            f"⚠️ {user.mention} получил предупреждение ({new_count}). Причина: {reason or 'не указана'}",
            ephemeral=True,
        )
        await self._log_action("warn", user.id, interaction.user.id, reason)

    @app_commands.command(name="warns", description="Показать количество предупреждений")
    async def warns(self, interaction: discord.Interaction, user: discord.Member):
        db = self.bot.db  # type: ignore[attr-defined]
        row = await db.fetchone("SELECT count FROM warns WHERE user_id=?", user.id)
        count = row[0] if row else 0
        await interaction.response.send_message(f"{user.mention} имеет предупреждений: {count}", ephemeral=True)

    async def _log_action(self, action: str, target_id: int, moderator_id: int, reason: str | None):
        try:
            db = self.bot.db  # type: ignore[attr-defined]
            await db.exec(
                "INSERT INTO moderation_logs(action, target_id, moderator_id, reason) VALUES(?, ?, ?, ?)",
                action,
                target_id,
                moderator_id,
                reason,
            )
        except Exception:
            self.log.exception("Failed to log moderation action")


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))


