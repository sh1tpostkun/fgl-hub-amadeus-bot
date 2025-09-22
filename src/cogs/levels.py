from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timedelta

import discord
from discord.ext import commands

log = logging.getLogger(__name__)


class Levels(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.xp_cooldown = 60  # секунды между начислением XP
        self.xp_range = (15, 25)  # диапазон XP за сообщение
        self.level_multiplier = 1.2  # множитель для расчета следующего уровня

    def calculate_level(self, xp: int) -> int:
        """Вычисляет уровень на основе опыта"""
        level = 0
        required_xp = 100
        while xp >= required_xp:
            xp -= required_xp
            level += 1
            required_xp = int(required_xp * self.level_multiplier)
        return level

    def calculate_xp_for_level(self, level: int) -> int:
        """Вычисляет общий опыт, необходимый для достижения уровня"""
        total_xp = 0
        required_xp = 100
        for _ in range(level):
            total_xp += required_xp
            required_xp = int(required_xp * self.level_multiplier)
        return total_xp

    def calculate_xp_to_next_level(self, current_xp: int) -> int:
        """Вычисляет опыт до следующего уровня"""
        current_level = self.calculate_level(current_xp)
        next_level_xp = self.calculate_xp_for_level(current_level + 1)
        return next_level_xp - current_xp

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Начисляет опыт за сообщения"""
        if message.author.bot or not message.guild:
            return

        try:
            db = self.bot.db
            user_id = message.author.id

            # Проверяем кулдаун
            result = await db.fetchone(
                "SELECT last_message_time FROM user_levels WHERE user_id = ?", user_id
            )
            
            if result:
                last_message_time = datetime.fromisoformat(result[0])
                if datetime.now() - last_message_time < timedelta(seconds=self.xp_cooldown):
                    return
            else:
                # Создаем запись для нового пользователя
                await db.exec(
                    "INSERT INTO user_levels (user_id, xp, level, last_message_time) VALUES (?, 0, 0, ?)",
                    user_id, datetime.now().isoformat()
                )

            # Начисляем случайный опыт
            xp_gained = random.randint(*self.xp_range)
            
            # Обновляем опыт и время последнего сообщения
            await db.exec(
                "UPDATE user_levels SET xp = xp + ?, last_message_time = ? WHERE user_id = ?",
                xp_gained, datetime.now().isoformat(), user_id
            )

            # Получаем обновленные данные
            result = await db.fetchone(
                "SELECT xp, level FROM user_levels WHERE user_id = ?", user_id
            )
            if not result:
                return

            old_xp, old_level = result
            new_level = self.calculate_level(old_xp)

            # Проверяем, повысился ли уровень
            if new_level > old_level:
                await db.exec(
                    "UPDATE user_levels SET level = ? WHERE user_id = ?",
                    new_level, user_id
                )
                
                # Выдаем награды за уровень
                await self._give_level_rewards(message.guild, message.author, new_level)
                
                # Уведомления о повышении уровня отключены
                # await self._send_level_up_message(message, message.author, new_level, old_level)

        except Exception as e:
            log.exception("Error in level system: %s", e)

    async def _send_level_up_message(self, message: discord.Message, user: discord.Member, new_level: int, old_level: int):
        """Отправляет уведомление о повышении уровня"""
        try:
            embed = discord.Embed(
                title="🎉 Поздравляем!",
                description=f"{user.mention} повысил уровень с **{old_level}** до **{new_level}**!",
                color=discord.Color.gold()
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.add_field(
                name="Текущий опыт",
                value=f"{await self._get_user_xp(user.id)} XP",
                inline=True
            )
            embed.add_field(
                name="До следующего уровня",
                value=f"{self.calculate_xp_to_next_level(await self._get_user_xp(user.id))} XP",
                inline=True
            )
            embed.timestamp = discord.utils.utcnow()
            
            await message.channel.send(embed=embed)
        except Exception as e:
            log.exception("Failed to send level up message: %s", e)

    async def _get_user_xp(self, user_id: int) -> int:
        """Получает опыт пользователя"""
        try:
            db = self.bot.db
            result = await db.fetchone("SELECT xp FROM user_levels WHERE user_id = ?", user_id)
            return result[0] if result else 0
        except Exception:
            return 0

    async def _get_user_level(self, user_id: int) -> int:
        """Получает уровень пользователя"""
        try:
            db = self.bot.db
            result = await db.fetchone("SELECT level FROM user_levels WHERE user_id = ?", user_id)
            return result[0] if result else 0
        except Exception:
            return 0

    async def _give_level_rewards(self, guild: discord.Guild, user: discord.Member, level: int):
        """Выдает награды за достижение уровня"""
        try:
            db = self.bot.db
            # Получаем все награды для этого уровня и ниже
            rewards = await db.fetchall(
                "SELECT role_id, role_name FROM level_rewards WHERE level <= ? ORDER BY level DESC",
                level
            )
            
            if not rewards:
                return
                
            # Получаем роли, которые уже есть у пользователя
            user_role_ids = {role.id for role in user.roles}
            
            for role_id, role_name in rewards:
                if role_id not in user_role_ids:
                    role = guild.get_role(role_id)
                    if role and role not in user.roles:
                        try:
                            await user.add_roles(role, reason=f"Награда за достижение {level} уровня")
                            log.info(f"Gave reward role {role_name} to {user} for level {level}")
                        except Exception as e:
                            log.exception(f"Failed to give role {role_name} to {user}: {e}")
                            
        except Exception as e:
            log.exception(f"Error giving level rewards to {user}: {e}")

    async def _remove_level_rewards(self, guild: discord.Guild, user: discord.Member, level: int):
        """Удаляет награды выше указанного уровня"""
        try:
            db = self.bot.db
            # Получаем награды выше указанного уровня
            rewards = await db.fetchall(
                "SELECT role_id, role_name FROM level_rewards WHERE level > ?",
                level
            )
            
            if not rewards:
                return
                
            # Получаем роли, которые есть у пользователя
            user_role_ids = {role.id for role in user.roles}
            
            for role_id, role_name in rewards:
                if role_id in user_role_ids:
                    role = guild.get_role(role_id)
                    if role and role in user.roles:
                        try:
                            await user.remove_roles(role, reason=f"Снижение уровня до {level}")
                            log.info(f"Removed reward role {role_name} from {user} due to level {level}")
                        except Exception as e:
                            log.exception(f"Failed to remove role {role_name} from {user}: {e}")
                            
        except Exception as e:
            log.exception(f"Error removing level rewards from {user}: {e}")

    @commands.hybrid_command(name="lvl", description="Показать уровень и опыт пользователя")
    async def lvl(self, ctx: commands.Context, user: discord.Member | None = None):
        """Показать уровень и опыт пользователя"""
        target_user = user or ctx.author
        
        try:
            xp = await self._get_user_xp(target_user.id)
            level = self.calculate_level(xp)
            xp_to_next = self.calculate_xp_to_next_level(xp)
            
            # Создаем прогресс-бар
            current_level_xp = self.calculate_xp_for_level(level)
            next_level_xp = self.calculate_xp_for_level(level + 1)
            progress = xp - current_level_xp
            total_needed = next_level_xp - current_level_xp
            
            # Создаем визуальный прогресс-бар
            bar_length = 10
            filled_length = int((progress / total_needed) * bar_length) if total_needed > 0 else bar_length
            bar = "█" * filled_length + "░" * (bar_length - filled_length)
            
            embed = discord.Embed(
                title=f"📊 Уровень {target_user.display_name}",
                color=discord.Color.blurple()
            )
            embed.set_thumbnail(url=target_user.display_avatar.url)
            embed.add_field(
                name="Уровень",
                value=f"**{level}**",
                inline=True
            )
            embed.add_field(
                name="Опыт",
                value=f"**{xp:,}** XP",
                inline=True
            )
            embed.add_field(
                name="До следующего уровня",
                value=f"**{xp_to_next:,}** XP",
                inline=True
            )
            embed.add_field(
                name="Прогресс",
                value=f"`{bar}` {progress}/{total_needed}",
                inline=False
            )
            embed.timestamp = discord.utils.utcnow()
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            log.exception("Error in level command: %s", e)
            await ctx.reply("❌ Произошла ошибка при получении информации об уровне.")

    @commands.hybrid_command(name="leaderboard", description="Показать топ пользователей по уровню")
    async def leaderboard(self, ctx: commands.Context, limit: int = 10):
        """Показать топ пользователей по уровню"""
        if limit < 1 or limit > 25:
            await ctx.reply("❌ Лимит должен быть от 1 до 25.")
            return
            
        try:
            db = self.bot.db
            results = await db.fetchall(
                "SELECT user_id, xp, level FROM user_levels ORDER BY xp DESC LIMIT ?",
                limit
            )
            
            if not results:
                await ctx.reply("📊 Пока нет данных об уровнях.")
                return
            
            embed = discord.Embed(
                title="🏆 Топ пользователей по уровню",
                color=discord.Color.gold()
            )
            
            description = ""
            for i, (user_id, xp, level) in enumerate(results, 1):
                user = ctx.guild.get_member(user_id)
                if user:
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
                    description += f"{medal} {user.mention} - Уровень **{level}** ({xp:,} XP)\n"
            
            embed.description = description
            embed.timestamp = discord.utils.utcnow()
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            log.exception("Error in leaderboard command: %s", e)
            await ctx.reply("❌ Произошла ошибка при получении топа пользователей.")

    @commands.hybrid_command(name="level-reset", description="Сбросить уровень пользователя")
    @commands.has_guild_permissions(administrator=True)
    async def level_reset(self, ctx: commands.Context, user: discord.Member):
        """Сбросить уровень пользователя"""
        try:
            db = self.bot.db
            # Удаляем награды перед сбросом
            await self._remove_level_rewards(ctx.guild, user, 0)
            
            await db.exec(
                "UPDATE user_levels SET xp = 0, level = 0 WHERE user_id = ?",
                user.id
            )
            await ctx.reply(f"✅ Уровень пользователя {user.mention} сброшен.")
        except Exception as e:
            log.exception("Error in level reset: %s", e)
            await ctx.reply("❌ Произошла ошибка при сбросе уровня.")

    @commands.hybrid_command(name="reward-add", description="Добавить награду-роль за уровень")
    @commands.has_guild_permissions(administrator=True)
    async def reward_add(self, ctx: commands.Context, level: int, role: discord.Role):
        """Добавить награду-роль за достижение уровня"""
        if level < 1:
            await ctx.reply("❌ Уровень должен быть больше 0.")
            return
            
        try:
            db = self.bot.db
            await db.exec(
                "INSERT OR REPLACE INTO level_rewards (level, role_id, role_name) VALUES (?, ?, ?)",
                level, role.id, role.name
            )
            await ctx.reply(f"✅ Награда {role.mention} добавлена за {level} уровень.")
        except Exception as e:
            log.exception("Error adding level reward: %s", e)
            await ctx.reply("❌ Произошла ошибка при добавлении награды.")

    @commands.hybrid_command(name="reward-remove", description="Удалить награду-роль за уровень")
    @commands.has_guild_permissions(administrator=True)
    async def reward_remove(self, ctx: commands.Context, level: int):
        """Удалить награду-роль за уровень"""
        try:
            db = self.bot.db
            result = await db.fetchone("SELECT role_name FROM level_rewards WHERE level = ?", level)
            if not result:
                await ctx.reply(f"❌ Награда за {level} уровень не найдена.")
                return
                
            await db.exec("DELETE FROM level_rewards WHERE level = ?", level)
            await ctx.reply(f"✅ Награда за {level} уровень удалена.")
        except Exception as e:
            log.exception("Error removing level reward: %s", e)
            await ctx.reply("❌ Произошла ошибка при удалении награды.")

    @commands.hybrid_command(name="rewards-list", description="Показать список наград за уровни")
    async def rewards_list(self, ctx: commands.Context):
        """Показать список наград за уровни"""
        try:
            db = self.bot.db
            rewards = await db.fetchall(
                "SELECT level, role_name FROM level_rewards ORDER BY level ASC"
            )
            
            if not rewards:
                await ctx.reply("📋 Награды за уровни не настроены.")
                return
                
            embed = discord.Embed(
                title="🏆 Награды за уровни",
                color=discord.Color.gold()
            )
            
            description = ""
            for level, role_name in rewards:
                description += f"**Уровень {level}:** {role_name}\n"
                
            embed.description = description
            embed.timestamp = discord.utils.utcnow()
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            log.exception("Error listing rewards: %s", e)
            await ctx.reply("❌ Произошла ошибка при получении списка наград.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Levels(bot))
