from __future__ import annotations

import logging

import discord
from discord.ext import commands

log = logging.getLogger(__name__)


class Logs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log_channel_id: int | None = None
        self.welcome_channel_id: int | None = None
        self.welcome_image_url: str | None = None

    async def cog_load(self):
        """Загружается при инициализации кога"""
        await self._load_welcome_settings()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        log.info("Member joined: %s (%s)", member, member.id)
        await self._send_log(
            embed=discord.Embed(title="👋 Присоединился", description=f"{member.mention}", color=discord.Color.green())
        )
        
        # Отправка приветственного embed в отдельный канал, если настроен
        if self.welcome_channel_id:
            channel = member.guild.get_channel(self.welcome_channel_id)
            if isinstance(channel, discord.TextChannel):
                try:
                    # Создаем красивое приветственное сообщение как на картинке
                    embed = discord.Embed(
                        color=0x00BFFF,  # Голубой цвет как на картинке
                    )
                    
                    # Основной текст с пингом пользователя
                    embed.description = f"**{member.mention}** Welcome new member~!!\n\n"
                    
                    # Получаем ссылки на каналы
                    rules_channel = await self._get_channel_link("rules", member.guild.id)
                    roles_channel = await self._get_channel_link("roles", member.guild.id)
                    general_channel = await self._get_channel_link("general", member.guild.id)
                    
                    # Добавляем инструкции с эмодзи и ссылками
                    instructions = [        
                        f"📖 {rules_channel}", 
                        f"🎭 {roles_channel}",
                        f"💬 {general_channel}"
                    ]
                    
                    for instruction in instructions:
                        embed.description += f"{instruction}\n"
                    
                    # Устанавливаем изображение если есть
                    if hasattr(self, "welcome_image_url") and self.welcome_image_url:
                        embed.set_image(url=self.welcome_image_url)
                    
                    # Добавляем информацию о сервере
                    embed.add_field(
                        name="👥 Участников", 
                        value=str(member.guild.member_count), 
                        inline=True
                    )
                    
                    embed.timestamp = discord.utils.utcnow()
                    embed.set_footer(text="Добро пожаловать на сервер!")
                    
                    await channel.send(embed=embed)
                except Exception:
                    log.exception("Failed to send welcome embed")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        log.info("Member left: %s (%s)", member, member.id)
        await self._send_log(
            embed=discord.Embed(title="👋 Покинул", description=f"{member.mention}", color=discord.Color.red())
        )

    @commands.hybrid_command(name="logs-setup", description="Указать канал для логов")
    @commands.has_guild_permissions(manage_guild=True)
    async def logs_setup(self, ctx: commands.Context, channel: discord.TextChannel):
        self.log_channel_id = channel.id
        await ctx.reply("✅ Канал логов сохранён на время работы бота")

    @commands.hybrid_command(name="welcome-setup", description="Указать канал для приветствий и (опц.) картинку")
    @commands.has_guild_permissions(manage_guild=True)
    async def welcome_setup(self, ctx: commands.Context, channel: discord.TextChannel, image_url: str | None = None):
        self.welcome_channel_id = channel.id
        if image_url:
            self.welcome_image_url = image_url
        # persist в БД
        try:
            db = self.bot.db  # type: ignore[attr-defined]
            await db.exec("INSERT OR REPLACE INTO settings(key, value) VALUES('welcome_channel_id', ?)", str(channel.id))
            if image_url:
                await db.exec("INSERT OR REPLACE INTO settings(key, value) VALUES('welcome_image_url', ?)", image_url)
        except Exception:
            log.exception("Failed to persist welcome settings")
        await ctx.reply(f"✅ Приветствия: {channel.mention}{' (картинка сохранена)' if image_url else ''}")

    @commands.hybrid_command(name="welcome-channels", description="Настроить ссылки на каналы в приветственном сообщении")
    @commands.has_guild_permissions(manage_guild=True)
    async def welcome_channels(self, ctx: commands.Context, 
                             rules: discord.TextChannel | None = None,
                             roles: discord.TextChannel | None = None,
                             general: discord.TextChannel | None = None,
                             rules_desc: str | None = None,
                             roles_desc: str | None = None,
                             general_desc: str | None = None):
        """Настроить ссылки на каналы в приветственном сообщении
        
        Параметры:
        - rules: канал с правилами
        - roles: канал с ролями  
        - general: общий канал
        - rules_desc: описание для ссылки на правила (например: "read our rules")
        - roles_desc: описание для ссылки на роли (например: "get your roles")
        - general_desc: описание для общего канала (например: "Talk with others")
        """
        try:
            db = self.bot.db
            channels_set = []
            
            if rules:
                await db.exec(
                    "INSERT OR REPLACE INTO welcome_channels (channel_type, channel_id, channel_name, description) VALUES (?, ?, ?, ?)",
                    "rules", rules.id, rules.name, rules_desc or ""
                )
                desc_text = f" ({rules_desc})" if rules_desc else ""
                channels_set.append(f"📖 Rules: {rules.mention}{desc_text}")
                
            if roles:
                await db.exec(
                    "INSERT OR REPLACE INTO welcome_channels (channel_type, channel_id, channel_name, description) VALUES (?, ?, ?, ?)",
                    "roles", roles.id, roles.name, roles_desc or ""
                )
                desc_text = f" ({roles_desc})" if roles_desc else ""
                channels_set.append(f"🎭 Roles: {roles.mention}{desc_text}")
                
            if general:
                await db.exec(
                    "INSERT OR REPLACE INTO welcome_channels (channel_type, channel_id, channel_name, description) VALUES (?, ?, ?, ?)",
                    "general", general.id, general.name, general_desc or ""
                )
                desc_text = f" ({general_desc})" if general_desc else ""
                channels_set.append(f"💬 General: {general.mention}{desc_text}")
            
            if channels_set:
                await ctx.reply(f"✅ Настроены каналы для приветствия:\n" + "\n".join(channels_set))
            else:
                await ctx.reply("❌ Укажите хотя бы один канал для настройки.")
                
        except Exception as e:
            log.exception("Error setting welcome channels: %s", e)
            await ctx.reply("❌ Произошла ошибка при настройке каналов.")

    @commands.hybrid_command(name="welcome-preview", description="Предварительный просмотр приветственного сообщения")
    @commands.has_guild_permissions(manage_guild=True)
    async def welcome_preview(self, ctx: commands.Context):
        """Предварительный просмотр приветственного сообщения"""
        try:
            # Создаем тестовое приветственное сообщение
            embed = discord.Embed(
                color=0x00BFFF,  # Голубой цвет как на картинке
            )
            
            # Основной текст с пингом пользователя
            embed.description = f"**{ctx.author.mention}** Welcome new member~!!\n\n"
            
            # Получаем ссылки на каналы
            rules_channel = await self._get_channel_link("rules", ctx.guild.id)
            roles_channel = await self._get_channel_link("roles", ctx.guild.id)
            general_channel = await self._get_channel_link("general", ctx.guild.id)
            
            # Добавляем инструкции с эмодзи и ссылками
            instructions = [
                f"📖 {rules_channel}", 
                f"🎭 {roles_channel}",
                f"💬 {general_channel}"
            ]
            
            for instruction in instructions:
                embed.description += f"{instruction}\n"
            
            # Устанавливаем изображение если есть
            if hasattr(self, "welcome_image_url") and self.welcome_image_url:
                embed.set_image(url=self.welcome_image_url)
            
            # Добавляем информацию о сервере
            embed.add_field(
                name="👥 Участников", 
                value=str(ctx.guild.member_count), 
                inline=True
            )
            
            embed.timestamp = discord.utils.utcnow()
            embed.set_footer(text="Добро пожаловать на сервер!")
            
            await ctx.reply("📋 Предварительный просмотр приветственного сообщения:", embed=embed)
            
        except Exception as e:
            log.exception("Error in welcome preview: %s", e)
            await ctx.reply("❌ Произошла ошибка при создании предварительного просмотра.")

    @commands.hybrid_command(name="welcome-list", description="Показать текущие настройки каналов приветствия")
    @commands.has_guild_permissions(manage_guild=True)
    async def welcome_list(self, ctx: commands.Context):
        """Показать текущие настройки каналов приветствия"""
        try:
            db = self.bot.db
            channels = await db.fetchall(
                "SELECT channel_type, channel_id, channel_name, description FROM welcome_channels ORDER BY channel_type"
            )
            
            if not channels:
                await ctx.reply("📋 Каналы для приветствия не настроены.")
                return
                
            embed = discord.Embed(
                title="📋 Настройки каналов приветствия",
                color=discord.Color.blurple()
            )
            
            for channel_type, channel_id, channel_name, description in channels:
                channel = ctx.guild.get_channel(channel_id)
                if channel:
                    desc_text = f" ({description})" if description else ""
                    embed.add_field(
                        name=f"{'📖' if channel_type == 'rules' else '🎭' if channel_type == 'roles' else '💬'} {channel_type.title()}",
                        value=f"{channel.mention}{desc_text}",
                        inline=False
                    )
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            log.exception("Error listing welcome channels: %s", e)
            await ctx.reply("❌ Произошла ошибка при получении списка каналов.")

    async def _load_welcome_settings(self):
        """Загружает настройки приветствия из БД"""
        try:
            db = self.bot.db
            # Загружаем ID канала приветствий
            result = await db.fetchone("SELECT value FROM settings WHERE key='welcome_channel_id'")
            if result and result[0].isdigit():
                self.welcome_channel_id = int(result[0])
            
            # Загружаем URL изображения
            result = await db.fetchone("SELECT value FROM settings WHERE key='welcome_image_url'")
            if result:
                self.welcome_image_url = result[0]
        except Exception as e:
            log.exception("Failed to load welcome settings: %s", e)

    async def _get_channel_link(self, channel_type: str, guild_id: int) -> str:
        """Получает ссылку на канал по типу"""
        try:
            db = self.bot.db
            result = await db.fetchone(
                "SELECT channel_id, channel_name, description FROM welcome_channels WHERE channel_type = ?", 
                channel_type
            )
            if result:
                channel_id, channel_name, description = result
                # Используем описание если есть, иначе название канала
                link_text = description if description else channel_name
                # Создаем короткую ссылку в формате [текст](ссылка)
                return f"[{link_text}](https://discord.com/channels/{guild_id}/{channel_id})"
            return channel_type.replace('_', ' ').title()
        except Exception:
            return channel_type.replace('_', ' ').title()

    async def _send_log(self, *, embed: discord.Embed):
        if not self.log_channel_id:
            return
        channel = self.bot.get_channel(self.log_channel_id)
        if isinstance(channel, discord.TextChannel):
            try:
                await channel.send(embed=embed)
            except Exception:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Logs(bot))


