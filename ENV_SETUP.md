# Настройка .env файла

## 1. Создайте .env файл
Скопируйте содержимое ниже в файл `.env` в корне проекта:

```
# Discord Bot Token - получите на https://discord.com/developers/applications
DISCORD_TOKEN=your_bot_token_here

# ID сервера (опционально) - для тестирования на конкретном сервере
GUILD_ID=123456789012345678

# ID владельцев бота (опционально) - через запятую
OWNER_IDS=123456789012345678,234567890123456789

# Уровень логирования (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Путь к базе данных SQLite
DB_PATH=./src/data/amadeus.db

# Префикс команд (для hybrid команд)
PREFIX=!
```

## 2. Как получить DISCORD_TOKEN

1. Перейдите на https://discord.com/developers/applications
2. Нажмите "New Application"
3. Введите название бота (например, "Amadeus")
4. Перейдите в раздел "Bot"
5. Нажмите "Add Bot"
6. Скопируйте токен и вставьте в `DISCORD_TOKEN=`

## 3. Как получить GUILD_ID (ID сервера)

1. В Discord включите режим разработчика: Настройки → Дополнительно → Режим разработчика
2. Правый клик на название сервера → "Копировать ID"
3. Вставьте в `GUILD_ID=`

## 4. Как получить OWNER_IDS

1. В режиме разработчика правый клик на ваш профиль → "Копировать ID"
2. Если владельцев несколько, добавьте через запятую: `123456789,987654321`

## 5. Пример заполненного .env

```
DISCORD_TOKEN=MTIzNDU2Nzg5MDEyMzQ1Njc4.GhIjKl.MnOpQrStUvWxYzAbCdEfGhIjKlMnOpQrStUvWx
GUILD_ID=987654321098765432
OWNER_IDS=123456789012345678
LOG_LEVEL=INFO
DB_PATH=./src/data/amadeus.db
PREFIX=!
```

## 6. Права бота на сервере

Добавьте бота на сервер с правами:
- ✅ Читать сообщения
- ✅ Отправлять сообщения
- ✅ Использовать слэш-команды
- ✅ Управлять ролями
- ✅ Управлять каналами
- ✅ Присоединяться к голосовым каналам
- ✅ Управлять участниками (для модерации)

## 7. Запуск

После заполнения .env файла:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m src.bot
```
