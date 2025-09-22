from __future__ import annotations

import aiosqlite


class Database:
    def __init__(self, path: str) -> None:
        self._path = path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        if self._conn is None:
            self._conn = await aiosqlite.connect(self._path)
            await self._conn.execute("PRAGMA foreign_keys = ON;")
            await self._conn.commit()

    async def init_schema(self) -> None:
        await self.exec(
            """
            CREATE TABLE IF NOT EXISTS warns (
                user_id INTEGER PRIMARY KEY,
                count INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS moderation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                target_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS tickets (
                channel_id INTEGER PRIMARY KEY,
                owner_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS message_stats (
                user_id INTEGER PRIMARY KEY,
                count INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reaction_roles (
                message_id INTEGER NOT NULL,
                emoji TEXT NOT NULL,
                role_id INTEGER NOT NULL,
                PRIMARY KEY (message_id, emoji)
            );

            CREATE TABLE IF NOT EXISTS user_levels (
                user_id INTEGER PRIMARY KEY,
                xp INTEGER NOT NULL DEFAULT 0,
                level INTEGER NOT NULL DEFAULT 0,
                last_message_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS level_rewards (
                level INTEGER PRIMARY KEY,
                role_id INTEGER NOT NULL,
                role_name TEXT NOT NULL
            );

                    CREATE TABLE IF NOT EXISTS welcome_channels (
                        channel_type TEXT PRIMARY KEY,
                        channel_id INTEGER NOT NULL,
                        channel_name TEXT NOT NULL,
                        description TEXT NOT NULL DEFAULT ''
                    );

                    CREATE TABLE IF NOT EXISTS voice_settings (
                        user_id INTEGER PRIMARY KEY,
                        channel_name TEXT NOT NULL DEFAULT '',
                        user_limit INTEGER NOT NULL DEFAULT 0,
                        is_locked BOOLEAN NOT NULL DEFAULT FALSE
                    );
            """
        )
        
        # Проверяем и добавляем колонку description если её нет
        await self._migrate_welcome_channels()

    async def _migrate_welcome_channels(self) -> None:
        """Миграция: добавляем колонку description если её нет"""
        try:
            # Проверяем структуру таблицы
            result = await self.fetchall("PRAGMA table_info(welcome_channels)")
            columns = [row[1] for row in result]  # row[1] это имя колонки
            
            # Если колонки description нет, добавляем её
            if 'description' not in columns:
                await self.exec("ALTER TABLE welcome_channels ADD COLUMN description TEXT DEFAULT ''")
        except Exception:
            # Игнорируем ошибки миграции
            pass

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @property
    def connection(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not connected")
        return self._conn

    async def exec(self, query: str, *params) -> None:
        await self.connection.executescript(query) if not params else await self.connection.execute(query, params)
        await self.connection.commit()

    async def fetchone(self, query: str, *params):
        async with self.connection.execute(query, params) as cursor:
            return await cursor.fetchone()

    async def fetchall(self, query: str, *params):
        async with self.connection.execute(query, params) as cursor:
            return await cursor.fetchall()


