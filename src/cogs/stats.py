from __future__ import annotations

import collections

import discord
from discord.ext import commands


class Stats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.message_counts: dict[int, int] = collections.defaultdict(int)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild and not message.author.bot:
            self.message_counts[message.author.id] += 1
            # persist periodically
            if self.message_counts[message.author.id] % 20 == 0:
                db = self.bot.db  # type: ignore[attr-defined]
                user_id = message.author.id
                row = await db.fetchone("SELECT count FROM message_stats WHERE user_id=?", user_id)
                base = row[0] if row else 0
                await db.exec(
                    "INSERT OR REPLACE INTO message_stats(user_id, count) VALUES(?, ?)",
                    user_id,
                    base + self.message_counts[user_id],
                )

    # удалена команда /top по запросу (сбор статистики оставлен)


async def setup(bot: commands.Bot):
    await bot.add_cog(Stats(bot))


