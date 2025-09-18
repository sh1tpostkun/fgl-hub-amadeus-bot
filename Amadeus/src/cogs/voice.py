from __future__ import annotations

from typing import Optional

import discord
from discord.ext import commands


class VoiceControlModal(discord.ui.Modal, title="Управление голосовым каналом"):
    def __init__(self, voice_channel: discord.VoiceChannel, action: str, **kwargs):
        super().__init__(**kwargs)
        self.voice_channel = voice_channel
        self.action = action
        
        if action == "rename":
            self.name_input = discord.ui.TextInput(
                label="Новое название канала",
                placeholder=f"Текущее: {voice_channel.name}",
                default=voice_channel.name.replace("🔒 ", ""),
                max_length=100,
                required=True
            )
            self.add_item(self.name_input)
        elif action == "limit":
            self.limit_input = discord.ui.TextInput(
                label="Лимит пользователей (0 = без лимита)",
                placeholder="0",
                default=str(voice_channel.user_limit) if voice_channel.user_limit else "0",
                max_length=2,
                required=True
            )
            self.add_item(self.limit_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if self.action == "rename":
                new_name = f"🔒 {self.name_input.value}"
                await self.voice_channel.edit(name=new_name)
                
                # Сохраняем настройку пользователя
                cog = interaction.client.get_cog("PrivateVoice")
                if cog and hasattr(cog, 'save_user_voice_settings'):
                    await cog.save_user_voice_settings(
                        interaction.user.id, 
                        self.name_input.value, 
                        self.voice_channel.user_limit or 0,
                        False  # is_locked
                    )
                
                await interaction.response.send_message(f"✅ Канал переименован в: {new_name}", ephemeral=True)
                
            elif self.action == "limit":
                try:
                    limit = int(self.limit_input.value)
                    if limit < 0:
                        limit = 0
                    await self.voice_channel.edit(user_limit=limit)
                    
                    # Сохраняем настройку пользователя
                    cog = interaction.client.get_cog("PrivateVoice")
                    if cog and hasattr(cog, 'save_user_voice_settings'):
                        channel_name = self.voice_channel.name.replace("🔒 ", "")
                        await cog.save_user_voice_settings(
                            interaction.user.id, 
                            channel_name, 
                            limit,
                            False  # is_locked
                        )
                    
                    limit_text = "без лимита" if limit == 0 else str(limit)
                    await interaction.response.send_message(f"✅ Лимит пользователей установлен: {limit_text}", ephemeral=True)
                except ValueError:
                    await interaction.response.send_message("❌ Введите корректное число", ephemeral=True)
                    return
                    
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {str(e)}", ephemeral=True)


class VoiceControlView(discord.ui.View):
    def __init__(self, voice_channel: discord.VoiceChannel, owner_id: int):
        super().__init__(timeout=None)
        self.voice_channel = voice_channel
        self.owner_id = owner_id

    @discord.ui.button(label="Переименовать", style=discord.ButtonStyle.primary, emoji="✏️", custom_id="voice_rename")
    async def rename_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ Только владелец канала может управлять им", ephemeral=True)
            return
        await interaction.response.send_modal(VoiceControlModal(self.voice_channel, "rename"))

    @discord.ui.button(label="Лимит пользователей", style=discord.ButtonStyle.secondary, emoji="👥", custom_id="voice_limit")
    async def limit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ Только владелец канала может управлять им", ephemeral=True)
            return
        await interaction.response.send_modal(VoiceControlModal(self.voice_channel, "limit"))

    @discord.ui.button(label="Заблокировать канал", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="voice_lock")
    async def lock_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ Только владелец канала может управлять им", ephemeral=True)
            return
        
        # Блокируем канал для всех кроме владельца
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(connect=False),
            interaction.user: discord.PermissionOverwrite(connect=True)
        }
        await self.voice_channel.edit(overwrites=overwrites)
        
        # Сохраняем настройку блокировки
        cog = interaction.client.get_cog("PrivateVoice")
        if cog and hasattr(cog, 'save_user_voice_settings'):
            channel_name = self.voice_channel.name.replace("🔒 ", "")
            await cog.save_user_voice_settings(
                interaction.user.id, 
                channel_name, 
                self.voice_channel.user_limit or 0,
                True  # is_locked
            )
        
        await interaction.response.send_message("🔒 Канал заблокирован", ephemeral=True)

    @discord.ui.button(label="Разблокировать канал", style=discord.ButtonStyle.success, emoji="🔓", custom_id="voice_unlock")
    async def unlock_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ Только владелец канала может управлять им", ephemeral=True)
            return
        
        # Разблокируем канал для всех
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(connect=True)
        }
        await self.voice_channel.edit(overwrites=overwrites)
        
        # Сохраняем настройку разблокировки
        cog = interaction.client.get_cog("PrivateVoice")
        if cog and hasattr(cog, 'save_user_voice_settings'):
            channel_name = self.voice_channel.name.replace("🔒 ", "")
            await cog.save_user_voice_settings(
                interaction.user.id, 
                channel_name, 
                self.voice_channel.user_limit or 0,
                False  # is_locked
            )
        
        await interaction.response.send_message("🔓 Канал разблокирован", ephemeral=True)

    @discord.ui.button(label="Передать владение", style=discord.ButtonStyle.primary, emoji="👑", custom_id="voice_transfer")
    async def transfer_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ Только владелец канала может управлять им", ephemeral=True)
            return
        
        # Создаем модальное окно для выбора нового владельца
        modal = TransferModal(self.voice_channel)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Удалить канал", style=discord.ButtonStyle.danger, emoji="🗑️", custom_id="voice_delete")
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ Только владелец канала может управлять им", ephemeral=True)
            return
        try:
            # Немедленно подтверждаем взаимодействие (эпемерально), чтобы не истекало
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)

            # Получаем ког для удаления связанного текстового канала
            cog = interaction.client.get_cog("PrivateVoice")
            if cog and hasattr(cog, 'text_channels'):
                # Удаляем из словаря связанных каналов
                if self.voice_channel.id in cog.text_channels:
                    text_channel_id = cog.text_channels.pop(self.voice_channel.id)
                    try:
                        text_channel = interaction.guild.get_channel(text_channel_id)
                        if text_channel:
                            await text_channel.delete(reason="Voice channel deleted by owner")
                    except Exception:
                        pass

            # Удаляем голосовой канал
            try:
                await self.voice_channel.delete(reason=f"Deleted by {interaction.user}")
            except Exception:
                pass

            # Сообщаем результат followup-ответом
            await interaction.followup.send("🗑️ Канал удален", ephemeral=True)
        except Exception as e:
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(f"❌ Ошибка при удалении: {e}", ephemeral=True)
                else:
                    await interaction.response.send_message(f"❌ Ошибка при удалении: {e}", ephemeral=True)
            except Exception:
                pass


class TransferModal(discord.ui.Modal, title="Передать владение каналом"):
    def __init__(self, voice_channel: discord.VoiceChannel, **kwargs):
        super().__init__(**kwargs)
        self.voice_channel = voice_channel
        
        self.user_input = discord.ui.TextInput(
            label="ID пользователя или упоминание",
            placeholder="@пользователь или 123456789",
            required=True
        )
        self.add_item(self.user_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_input = self.user_input.value.strip()
            
            # Пытаемся найти пользователя
            user = None
            
            # Если это упоминание
            if user_input.startswith('<@') and user_input.endswith('>'):
                user_id = int(user_input[2:-1])
                user = interaction.guild.get_member(user_id)
            # Если это ID
            elif user_input.isdigit():
                user_id = int(user_input)
                user = interaction.guild.get_member(user_id)
            
            if not user:
                await interaction.response.send_message("❌ Пользователь не найден", ephemeral=True)
                return
            
            # Обновляем владельца в базе данных (если есть)
            cog = interaction.client.get_cog("PrivateVoice")
            if cog and hasattr(cog, 'owner_map'):
                cog.owner_map[self.voice_channel.id] = user.id
            
            # Обновляем права доступа
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False, connect=False),
                user: discord.PermissionOverwrite(view_channel=True, connect=True, manage_channels=True),
            }
            await self.voice_channel.edit(overwrites=overwrites)
            
            await interaction.response.send_message(f"👑 Владение каналом передано {user.mention}", ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {str(e)}", ephemeral=True)


class PrivateVoice(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.template_channel_id: Optional[int] = None  # голосовой канал-шаблон
        self.owner_map: dict[int, int] = {}  # channel_id -> owner_id
        self.text_channels: dict[int, int] = {}  # voice_channel_id -> text_channel_id

    async def cog_load(self) -> None:
        """Загрузка кога: подхватываем сохранённый шаблонный канал"""
        try:
            row = await self.bot.db.fetchone("SELECT value FROM settings WHERE key='voice_template_channel_id'")
            if row and str(row[0]).isdigit():
                self.template_channel_id = int(row[0])
        except Exception as e:
            print(f"Failed to load voice template id: {e}")

    async def get_user_voice_settings(self, user_id: int) -> dict:
        """Получает настройки голосового канала пользователя"""
        try:
            result = await self.bot.db.fetchone(
                "SELECT channel_name, user_limit, is_locked FROM voice_settings WHERE user_id = ?",
                user_id
            )
            if result:
                return {
                    'channel_name': result[0] or '',
                    'user_limit': result[1] or 0,
                    'is_locked': bool(result[2])
                }
            return {'channel_name': '', 'user_limit': 0, 'is_locked': False}
        except Exception as e:
            print(f"Failed to get user voice settings: {e}")
            return {'channel_name': '', 'user_limit': 0, 'is_locked': False}

    async def save_user_voice_settings(self, user_id: int, channel_name: str = '', user_limit: int = 0, is_locked: bool = False):
        """Сохраняет настройки голосового канала пользователя"""
        try:
            await self.bot.db.exec(
                """INSERT OR REPLACE INTO voice_settings (user_id, channel_name, user_limit, is_locked) 
                   VALUES (?, ?, ?, ?)""",
                user_id, channel_name, user_limit, is_locked
            )
        except Exception as e:
            print(f"Failed to save user voice settings: {e}")

    @discord.app_commands.command(name="voice-setup", description="Указать шаблонный голосовой канал")
    @discord.app_commands.describe(template_channel="Голосовой канал-шаблон для создания приватных каналов")
    async def voice_setup(self, interaction: discord.Interaction, template_channel: discord.VoiceChannel):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ У вас нет прав для управления каналами", ephemeral=True)
            return
            
        self.template_channel_id = template_channel.id
        # Сохраняем в БД, чтобы не сбрасывалось после перезапуска бота
        try:
            await self.bot.db.exec(
                "INSERT OR REPLACE INTO settings (key, value) VALUES ('voice_template_channel_id', ?)",
                str(template_channel.id)
            )
        except Exception as e:
            print(f"Failed to persist voice template id: {e}")

        await interaction.response.send_message(f"✅ Шаблон канал установлен: {template_channel.mention}", ephemeral=True)

    @discord.app_commands.command(name="voice-status", description="Показать текущий шаблонный канал")
    async def voice_status(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ У вас нет прав для управления каналами", ephemeral=True)
            return
            
        if self.template_channel_id:
            channel = interaction.guild.get_channel(self.template_channel_id)
            if channel:
                await interaction.response.send_message(f"📢 Текущий шаблонный канал: {channel.mention}", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Шаблонный канал не найден", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Шаблонный канал не установлен", ephemeral=True)

    @discord.app_commands.command(name="voice-settings", description="Показать ваши сохраненные настройки голосового канала")
    async def voice_settings(self, interaction: discord.Interaction):
        settings = await self.get_user_voice_settings(interaction.user.id)
        
        embed = discord.Embed(
            title="🎛️ Ваши настройки голосового канала",
            color=0x5865F2
        )
        
        channel_name = settings['channel_name'] or "Не установлено"
        user_limit = settings['user_limit'] or 0
        is_locked = settings['is_locked']
        
        embed.add_field(
            name="📝 Название канала",
            value=channel_name,
            inline=True
        )
        embed.add_field(
            name="👥 Лимит пользователей",
            value="Без лимита" if user_limit == 0 else str(user_limit),
            inline=True
        )
        embed.add_field(
            name="🔒 Статус блокировки",
            value="Заблокирован" if is_locked else "Разблокирован",
            inline=True
        )
        
        embed.set_footer(text="Эти настройки будут применены при создании нового канала")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def create_control_panel(self, voice_channel: discord.VoiceChannel, owner: discord.Member):
        """Создает панель управления для голосового канала"""
        try:
            # Создаем текстовый канал для управления
            overwrites = {
                voice_channel.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                owner: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            }
            
            text_channel = await voice_channel.guild.create_text_channel(
                name=f"control-{voice_channel.name.lower().replace('🔒 ', '').replace(' ', '-')}",
                category=voice_channel.category,
                overwrites=overwrites,
                reason="Voice control panel"
            )
            
            # Сохраняем связь
            self.text_channels[voice_channel.id] = text_channel.id
            
            # Создаем embed с панелью управления
            embed = discord.Embed(
                title="🎛️ Панель управления голосовым каналом",
                description=f"**Канал:** {voice_channel.mention}\n**Владелец:** {owner.mention}",
                color=0x5865F2
            )
            embed.add_field(
                name="Доступные действия:",
                value="• ✏️ Переименовать канал\n• 👥 Установить лимит пользователей\n• 🔒 Заблокировать канал\n• 🔓 Разблокировать канал\n• 👑 Передать владение\n• 🗑️ Удалить канал",
                inline=False
            )
            embed.set_footer(text="Только владелец канала может использовать эти кнопки")
            
            # Отправляем панель управления
            view = VoiceControlView(voice_channel, owner.id)
            await text_channel.send(embed=embed, view=view)
            
        except Exception as e:
            print(f"Failed to create control panel: {e}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # Создание приватного канала при входе в шаблон
        if self.template_channel_id and after.channel and after.channel.id == self.template_channel_id:
            try:
                guild = member.guild
                
                # Получаем сохраненные настройки пользователя
                settings = await self.get_user_voice_settings(member.id)
                channel_name = settings['channel_name'] or member.display_name
                user_limit = settings['user_limit'] or 0
                is_locked = settings['is_locked']
                
                # Настраиваем права доступа
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False, connect=not is_locked),
                    member: discord.PermissionOverwrite(view_channel=True, connect=True, manage_channels=True),
                }
                
                # Создаем канал с сохраненными настройками
                new_channel = await guild.create_voice_channel(
                    name=f"🔒 {channel_name}",
                    category=after.channel.category,
                    overwrites=overwrites,
                    user_limit=user_limit if user_limit > 0 else None,
                    reason="Create private voice",
                )
                self.owner_map[new_channel.id] = member.id
                
                # Создаем панель управления
                await self.create_control_panel(new_channel, member)
                
                try:
                    await member.move_to(new_channel)
                except Exception as e:
                    print(f"Failed to move user to new channel: {e}")
            except Exception as e:
                print(f"Failed to create private voice channel: {e}")

        # Удаление пустых приватных каналов и их панелей управления
        if before.channel and before.channel.id in self.owner_map:
            if len(before.channel.members) == 0:
                owner_id = self.owner_map.pop(before.channel.id)
                
                # Удаляем панель управления
                if before.channel.id in self.text_channels:
                    text_channel_id = self.text_channels.pop(before.channel.id)
                    try:
                        text_channel = before.channel.guild.get_channel(text_channel_id)
                        if text_channel:
                            await text_channel.delete(reason="Voice channel deleted")
                    except Exception as e:
                        print(f"Failed to delete text channel: {e}")
                
                try:
                    await before.channel.delete(reason=f"Private voice empty (owner {owner_id})")
                except Exception as e:
                    print(f"Failed to delete voice channel: {e}")

    @commands.hybrid_group(name="voice", with_app_command=True)
    async def voice_group(self, ctx: commands.Context):
        pass

    @voice_group.command(name="transfer")
    async def voice_transfer(self, ctx: commands.Context, new_owner: discord.Member):
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.reply("Вы должны находиться в своём приватном канале.")
        channel = ctx.author.voice.channel
        if self.owner_map.get(channel.id) != ctx.author.id:
            return await ctx.reply("Вы не владелец канала.")
        self.owner_map[channel.id] = new_owner.id
        await ctx.reply(f"Владелец канала: {new_owner.mention}")


async def setup(bot: commands.Bot):
    await bot.add_cog(PrivateVoice(bot))