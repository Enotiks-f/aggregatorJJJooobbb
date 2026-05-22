START_TEXT = (
    "Привет! Это Jobber — помощник по поиску вакансий для администратора канала "
    "jjjooobbb 😊\n\n"
    "Бот собирает релевантные посты из Telegram-каналов, отбирает стажировки и "
    "junior-вакансии и добавляет новые записи в Google Sheets.\n\n"
    "Уже обработанные посты не дублируются — всё хранится в локальной базе."
)

HELP_TEXT = """\
Команды Jobber:

/start — приветствие и о боте
/help — этот список команд
/jjjooobbb — запустить парсинг каналов и обновить таблицу
/chennels — список каналов для парсинга
/add_chennel — добавить один или несколько каналов
/remove_chennel — удалить один или несколько каналов"""

CHANNELS_LIST_HEADER = "📡 Каналы для парсинга:"

CHANNELS_EMPTY = (
    "Список каналов пуст.\n\n"
    "Добавьте каналы командой /add_chennel"
)

CHANNELS_ADD_USAGE = """\
Добавление каналов — /add_chennel

Укажите каналы в одном сообщении (без @):
• через пробел: workenot futru_it easycareerstart
• через запятую: workenot, futru_it
• с новой строки:
workenot
futru_it

Также можно: @channel или ссылка t.me/channel"""

CHANNELS_REMOVE_USAGE = """\
Удаление каналов — /remove_chennel

Формат такой же, как у /add_chennel:
/remove_chennel workenot futru_it
или несколько каналов с новой строки."""

PARSE_STARTED_TEXT = (
    "⏳ Начался парсинг каналов…\n"
    "Это может занять несколько минут, подождите."
)

PARSE_TABLE_TEXT = (
    "📊 Парсинг завершён.\n"
    "Началось формирование таблицы в Google Sheets…"
)

PARSE_BUSY_TEXT = "⏳ Парсинг уже выполняется. Дождитесь завершения."
