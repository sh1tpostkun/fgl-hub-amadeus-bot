from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands

from .config import load_settings
from discord import app_commands
from .utils.logging_setup import setup_logging
from .utils.db import Database


class RestrictedCommandTree(app_commands.CommandTree):
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        client = interaction.client  # Bot instance
        user = interaction.user
        
        # Команды уровней доступны всем
        if interaction.command and interaction.command.name in ['lvl', 'leaderboard', 'rewards-list']:
            return True
            
        try:
            owner_ids = set(getattr(client, "settings").owner_ids)
        except Exception:
            owner_ids = set()
        if user and user.id in owner_ids:
            return True
        if isinstance(user, discord.Member) and user.guild_permissions.administrator:
            return True
        raise app_commands.CheckFailure("Команда доступна только владельцу или администраторам")


class AmadeusBot(commands.Bot):
    def __init__(self, *, intents: discord.Intents, db: Database, prefix: str, settings):
        super().__init__(command_prefix=commands.when_mentioned_or(prefix), intents=intents, tree_cls=RestrictedCommandTree)
        self.db = db
        self.settings = settings

    async def setup_hook(self) -> None:
        await self.db.connect()
        await self.db.init_schema()
        
        # Добавляем персистентные view для кнопок с учётом сохранённых настроек
        from src.cogs.tickets import TicketButton, CloseTicketView
        category_id_val = None
        support_role_id_val = None
        try:
            row = await self.db.fetchone("SELECT value FROM settings WHERE key='tickets_category_id'")
            if row and str(row[0]).isdigit():
                category_id_val = int(row[0])
        except Exception:
            pass
        try:
            row = await self.db.fetchone("SELECT value FROM settings WHERE key='tickets_support_role_id'")
            if row and str(row[0]).isdigit():
                support_role_id_val = int(row[0])
        except Exception:
            pass
        self.add_view(TicketButton(self, category_id_val, support_role_id_val))
        self.add_view(CloseTicketView())

        # Подтягиваем welcome настройки
        try:
            row = await self.db.fetchone("SELECT value FROM settings WHERE key='welcome_channel_id'")
            self.welcome_channel_id = int(row[0]) if row and str(row[0]).isdigit() else None  # type: ignore[attr-defined]
            row2 = await self.db.fetchone("SELECT value FROM settings WHERE key='welcome_image_url'")
            self.welcome_image_url = row2[0] if row2 else None  # type: ignore[attr-defined]
        except Exception:
            pass

        # Ограничение для prefix/hybrid-команд
        async def predicate(ctx: commands.Context) -> bool:
            # Команды уровней доступны всем
            if ctx.command and ctx.command.name in ['lvl', 'leaderboard', 'rewards-list']:
                return True
                
            if ctx.author.id in set(self.settings.owner_ids):
                return True
            if isinstance(ctx.author, discord.Member) and ctx.author.guild_permissions.administrator:
                return True
            raise commands.CheckFailure("Команда доступна только владельцу или администраторам")

        self.check(predicate)
        
        for ext in (
            "src.cogs.moderation",
            "src.cogs.tickets",
            "src.cogs.embeds",
            "src.cogs.roles",
            "src.cogs.voice",
            "src.cogs.logs",
            "src.cogs.stats",
            "src.cogs.security",
            "src.cogs.levels",
        ):
            try:
                await self.load_extension(ext)
            except Exception:
                logging.exception("Failed to load extension %s", ext)
        # Sync application commands for all guilds during startup
        try:
            await self.tree.sync()
            logging.getLogger(__name__).info("Slash commands synced")
        except Exception:
            logging.exception("Failed to sync application commands")

    async def close(self) -> None:
        await super().close()
        await self.db.close()


async def main() -> None:
    # Keep-alive для Replit
    try:
        from keep_alive import keep_alive
        keep_alive()
    except ImportError:
        pass  # Не Replit окружение
    
    settings = load_settings()
    setup_logging(settings.log_level)

    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.guilds = True
    intents.emojis = True
    intents.voice_states = True
    intents.presences = False

    db = Database(settings.db_path)
    bot = AmadeusBot(intents=intents, db=db, prefix=settings.prefix, settings=settings)

    async with bot:
        await bot.start(settings.token)


if __name__ == "__main__":
    asyncio.run(main())


