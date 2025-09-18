## Amadeus Discord Bot

Функциональный Discord-бот на Python: модерация, тикеты с кнопками, embeds, роли (реакции/автороль), приватные войс-каналы, логи, статистика и безопасность.

### Быстрый старт
1) Создайте и заполните `.env` (см. ниже)
2) Установите зависимости в venv
```powershell
  python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
3) Запустите бота
```powershell
python -m src.bot
```

### Переменные окружения (.env)
```
DISCORD_TOKEN=your_token_here
GUILD_ID=123456789012345678
OWNER_IDS=123456789012345678,234567890123456789
LOG_LEVEL=INFO
DB_PATH=./src/data/amadeus.db
PREFIX=!
```

### Права и приглашение
- В SCOPES выберите: `bot`, `applications.commands`
- В PERMISSIONS: рекомендуется `Administrator` или минимум: View Channels, Send Messages, Manage Messages, Embed Links, Read Message History, Add Reactions, Use Slash Commands, Manage Roles, Manage Channels, Kick, Ban, Moderate, Connect, Move Members

### Команды и функции
- **Модерация**: `/kick`, `/ban`, `/mute`, `/warn`, `/warns` (только админы)
- **Тикеты**:
  - `/ticket setup` — указать категорию и роль поддержки (сохраняется в БД)
  - `/ticket panel` — создать панель с кнопкой "Создать тикет"
  - `/ticket set-closed-channel` — канал, куда улетают логи закрытых тикетов
  - Кнопки: "Создать тикет" создаёт приват-канал в заданной категории; "Закрыть тикет" удаляет канал и отправляет embed-лог
- **Уровни** (доступны всем):
  - `/lvl [пользователь]` — показать уровень и опыт пользователя
  - `/leaderboard [лимит]` — топ пользователей по уровню (1-25)
  - `/rewards-list` — показать список наград за уровни
  - **Админские команды:**
    - `/level-reset @пользователь` — сбросить уровень
    - `/reward-add <уровень> @роль` — добавить награду-роль за уровень
    - `/reward-remove <уровень>` — удалить награду за уровень
  - Автоматическое начисление опыта за сообщения (15-25 XP, кулдаун 60 сек)
  - Автоматическая выдача ролей при достижении уровней
  - Уведомления о повышении уровня с прогресс-баром
- **Embeds**: `/embed-modal`, `/edit-embed`, `/edit-embed-reply` (только админы)
- **Роли**: `/role-add`, `/role-remove`, `/autorole-set`, `/reaction-bind` (только админы)
- **Приватные войс-каналы**: `voice-setup`, `voice transfer` (только админы)
- **Логи**: `logs-setup`, `welcome-setup`, `welcome-channels`, `welcome-preview`, `welcome-list` (только админы)
- **Статистика**: сбор ведётся в фоне (команда скрыта по запросу)
- **Безопасность**: анти-спам/инвайты (только админы)

### Настройка тикетов (пример)
1) `/ticket setup #tickets @Support` — сохранит категорию и роль поддержки
2) `/ticket set-closed-channel #closed-tickets` — куда присылать логи закрытия
3) `/ticket panel "Report issues" "Опишите проблему, прикрепите доказательства" #support-panel`
4) Пользователь нажимает кнопку → создаётся приватный канал в выбранной категории; при закрытии канал удаляется, лог уходит в `#closed-tickets`

### Реакционные роли к существующему сообщению
1) Скопируйте ID сообщения (режим разработчика)
2) `/reaction-bind <message_id> 😀 @Role`
3) Реакция на это сообщение выдаёт/снимает роль. Привязки переживают перезапуск (хранятся в БД).

### Настройка приветственных сообщений
1) `/welcome-setup #welcome https://ссылка-на-картинку.jpg` — канал и картинка
2) `/welcome-channels rules:#rules roles:#roles general:#general rules_desc:"read our rules" roles_desc:"get your roles" general_desc:"Talk with others"` — ссылки на каналы с описаниями
3) `/welcome-preview` — предварительный просмотр
4) `/welcome-list` — показать текущие настройки
5) При входе нового участника отправится красивое сообщение с кликабельными ссылками

### Редактирование Embed сообщений
1) **По ID сообщения**: `/edit-embed <message_id>` — редактировать embed по ID
2) **Ответом на сообщение**: Ответьте на сообщение бота командой `/edit-embed-reply`
3) **Модальное окно**: Откроется форма с текущими значениями для редактирования
4) **Скрытое редактирование**: Все ответы ephemeral (видно только вам)

### Структура проекта
```
src/
  bot.py            # запуск, регистрация persistent views
  config.py         # .env настройки
  utils/
    db.py           # aiosqlite + schema (warns, tickets, settings, reaction_roles)
    logging_setup.py
  cogs/
    moderation.py   # kick/ban/mute/warn + логи
    tickets.py      # панели, кнопки, создание/закрытие приватных тикетов
    levels.py       # система уровней, опыт, топ пользователей
    embeds.py       # embed + modal
    roles.py        # manual roles + autorole + reaction roles/bind
    voice.py        # приватные войс-каналы
    logs.py         # лог-канал join/leave
    stats.py        # счётчики сообщений и топ
    security.py     # анти-спам/инвайты + verify
```

### Частые проблемы
- Нет ссылки приглашения? Убедитесь, что выбраны SCOPES: `bot`, `applications.commands`.
- Ошибка `audioop`: установите `discord.py[voice]` (уже в requirements).
- Кнопки не работают после перезапуска: бот добавляет persistent views при старте, убедитесь, что выполнен `/ticket setup`.

