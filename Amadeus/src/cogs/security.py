from __future__ import annotations

import re

import discord
from discord.ext import commands


class Security(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._url_re = re.compile(r"https?://\S+", re.IGNORECASE)
        self.max_msgs_per_10s = 8
        self.user_windows: dict[int, list[float]] = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        # Simple anti-link: delete obvious invite links
        if "discord.gg/" in message.content.lower():
            try:
                await message.delete()
            except Exception:
                pass
            return
        # Rate-limit per user (anti-spam)
        now = message.created_at.timestamp() if message.created_at else discord.utils.utcnow().timestamp()
        win = self.user_windows.setdefault(message.author.id, [])
        win.append(now)
        # keep only last 10 seconds
        self.user_windows[message.author.id] = [t for t in win if now - t <= 10]
        if len(self.user_windows[message.author.id]) > self.max_msgs_per_10s:
            try:
                await message.delete()
            except Exception:
                pass

    # удалена команда /verify по запросу (фильтры и анти-спам оставлены)


async def setup(bot: commands.Bot):
    await bot.add_cog(Security(bot))


