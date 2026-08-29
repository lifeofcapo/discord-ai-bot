
```bash
# 1. Клонировать репозиторий и перейти в папку проекта
cd discordbot

# 2. Создать и активировать виртуальное окружение
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Установить зависимости
pip install -r requirements.txt --break-system-packages

# 4. Скопировать .env.example в .env и заполнить значения (см. раздел 4)
cp .env.example .env

# 5. Поднять Postgres (pgvector) и MinIO (S3-совместимое хранилище)
docker compose up -d db minio

# 6. Создать таблицы и включить расширение pgvector (один раз)
python -m merchant_bot.db.init_db

# 7. Запустить бота
python main.py
```



```bash
docker compose up -d db minio
python main.py
```

Если хочешь, чтобы `db` и `minio` поднимались сами при старте Docker
(без ручной команды) — у них уже стоит `restart: unless-stopped` в
`docker-compose.yml`, так что достаточно один раз запустить Docker Desktop
после перезагрузки, и контейнеры вернутся сами.

---

## 2. Архитектура проекта

```
discordbot/
├── main.py                    # точка входа — запускает бота
├── docker-compose.yml         # db (Postgres+pgvector), minio (S3), bot
├── requirements.txt           # зависимости Python
├── .env                       # секреты и конфигурация (не в git!)
│
├── merchant_bot/
│   ├── bot.py                 # класс бота, регистрация cogs, sync команд
│   ├── config.py              # константы: имена каналов, роли, реакции
│   ├── permissions.py         # проверка прав администратора
│   ├── state.py                # защита от даблклика (в памяти, не в БД)
│   ├── threads_utils.py       # создание приватных Discord-тредов
│   ├── ai_client.py           # обёртка над OpenAI (chat + vision)
│   ├── system_prompt.py       # методология продаж — системный промпт AI
│   ├── knowledge_base.py      # RAG: добавление/поиск записей через embeddings
│   ├── storage.py             # загрузка скриншотов в S3/MinIO
│   │
│   ├── db/
│   │   ├── engine.py           # подключение к Postgres (SQLAlchemy async)
│   │   ├── models.py           # ORM-модели: Student, AIThread, AIMessage, KnowledgeBaseEntry, Screenshot
│   │   ├── repository.py       # CRUD-функции поверх моделей
│   │   └── init_db.py          # разовый скрипт создания таблиц/расширения
│   │
│   ├── ui/
│   │   ├── views.py            # кнопки: Launch Merchant AI, Support, Reserve, Submit Sale
│   │   └── modals.py           # формы: Reservation, Sale Submission
│   │
│   └── cogs/                   # модули команд/событий, подключаемые в bot.py
│       ├── ai_assistant.py     # основная логика диалога с Merchant AI
│       ├── knowledge_ingestion.py  # автозагрузка базы знаний из канала
│       ├── admin.py            # админ-команды (публикация кнопок, треды)
│       ├── profile.py          # /profile — карточка ученика
│       ├── misc.py             # /ping
│       └── reactions.py        # автоудаление нежелательных реакций
│
└── tests/                      # pytest-тесты
```

---

### `merchant_bot/`

| Файл | Назначение |
|---|---|
| `bot.py` | Класс `MerchantBot`. При старте загружает все cogs, регистрирует persistent views (кнопки, переживающие рестарт), синхронизирует slash-команды с сервером. |
| `config.py` | Все "магические строки" в одном месте: названия каналов, роли админов, список блокируемых реакций. |
| `permissions.py` | Декоратор `@is_authorized_admin()` — проверяет, есть ли у пользователя роль из `ADMIN_COMMAND_ROLES`. |
| `state.py` | Простая защита от даблкликов по кнопкам (in-memory, не критично при рестарте). |
| `threads_utils.py` | Создаёт приватный Discord-тред и добавляет туда автора + сотрудников с ролью из `STAFF_ROLE_NAMES`. |
| `ai_client.py` | Обёртка над OpenAI SDK: `get_ai_response()` — чат-запрос с системным промптом, `build_user_content()` — собирает текст+картинки в формат для vision. |
| `system_prompt.py` | Большой системный промпт — описывает роль Merchant AI, его методологию продаж, формат ответа (Situation/Strategy/Reply/Optional). |
| `knowledge_base.py` | RAG-логика: `add_entry()` считает embedding и сохраняет запись, `search()` находит ближайшие по смыслу записи через pgvector (`cosine_distance`), `format_for_prompt()` форматирует их для системного сообщения. |
| `storage.py` | Загружает скриншоты в S3/MinIO (`save_screenshot`), генерирует временные ссылки (`get_presigned_url`), создаёт bucket при первом запуске. |

### `merchant_bot/db/` — база данных

| Файл | Назначение |
|---|---|
| `engine.py` | Создаёт асинхронный SQLAlchemy engine по `DATABASE_URL` из `.env`. |
| `models.py` | ORM-таблицы: `Student` (ученик), `AIThread` (приватный тред: merchant_ai/support), `AIMessage` (сообщение в истории диалога), `KnowledgeBaseEntry` (запись базы знаний с embedding), `Screenshot` (метаданные загруженных скриншотов). |
| `repository.py` | Функции работы с БД: получить/создать ученика, получить активный тред, добавить сообщение в историю, сбросить историю и т.д. |
| `init_db.py` | Разовый скрипт: включает расширение `pgvector`, создаёт все таблицы из `models.py`. Запускать один раз при первой настройке БД (или после `docker volume rm`). |

### `merchant_bot/ui/` — интерфейс Discord

| Файл | Назначение |
|---|---|
| `views.py` | Кнопки: **Launch Merchant AI** (создаёт приватный тред с ботом), **Support** (тикет поддержки), **Reserve a Beat** / **Submit a Sale** (открывают формы). |
| `modals.py` | Формы Discord: заявка на резервацию бита, отчёт о продаже — обе создают приватный тред с деталями для стаффа. |

### `merchant_bot/cogs/` — модули команд и событий

| Файл | Назначение |
|---|---|
| `ai_assistant.py` | Ядро продукта. Слушает сообщения в приватных AI-тредах: сохраняет скриншоты в S3, ищет релевантные записи в базе знаний (RAG), достаёт историю диалога, вызывает OpenAI, сохраняет и отправляет ответ. Команда `/reset` — сброс памяти конкретного треда. |
| `knowledge_ingestion.py` | Слушает канал `🔧｜ai-knowledge-ingestion`. Всё, что туда кидают админы (текст/файлы/фото), автоматически парсится и попадает в базу знаний — без ручных команд. Ставит ✅/⚠️ реакцией как обратную связь. |
| `admin.py` | Команды для публикации кнопок (`/post_merchant_ai_button` и т.д.), просмотр (`/list_threads`) и удаление (`/close_thread`) приватных тредов. |
| `profile.py` | `/profile` — показывает карточку ученика: роли, статус Partner Catalog, дату вступления, статистику AI-переписки. |
| `misc.py` | `/ping` — проверка, что бот жив. |
| `reactions.py` | Автоматически убирает реакции из списка `BLOCKED_REACTIONS` (👎, 💩, 🖕). |

---

## 4. Переменные окружения (`.env`)

```dotenv
# Discord
DISCORD_BOT_TOKEN=...
DISCORD_GUILD_ID=...

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5.4-mini

# База данных (локально — localhost, в докере — db)
DATABASE_URL=postgresql://merchant:merchant@localhost:5432/merchant_standard

# S3 / MinIO (локально — localhost, в докере — minio)
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=merchant
S3_SECRET_KEY=merchant123
S3_BUCKET=merchant-screenshots
S3_REGION=auto
```

> При запуске бота **внутри Docker** (`docker compose up -d` без указания
> конкретных сервисов — поднимает всё, включая `bot`) хосты `db` и `minio`
> резолвятся docker-сетью сами. При запуске бота **локально в venv**
> нужно менять `db`/`minio` на `localhost`.

---

## 5. Частые команды

| Что нужно | Команда |
|---|---|
| Поднять БД и хранилище | `docker compose up -d db minio` |
| Поднять вообще всё (включая бота, продакшн-режим) | `docker compose up -d` |
| Посмотреть статус контейнеров | `docker compose ps` |
| Посмотреть логи бота (если в докере) | `docker compose logs -f bot` |
| Создать таблицы БД (один раз) | `python -m merchant_bot.db.init_db` |
| Зайти в psql внутри контейнера | `docker exec -it discordbot-db-1 psql -U merchant -d merchant_standard` |
| Запустить бота локально | `python main.py` |
| Прогнать тесты | `pytest` |
| Остановить всё, но сохранить данные | `docker compose down` |
| Остановить всё и **удалить данные БД** (осторожно!) | `docker compose down -v` |

---

## 6. Discord slash-команды

| Команда | Кто может | Что делает |
|---|---|---|
| `/reset` | любой ученик, внутри своего AI-треда | Сбрасывает историю диалога с Merchant AI |
| `/profile [member]` | любой | Показывает карточку профиля |
| `/ping` | любой | Проверка, что бот жив |
| `/post_merchant_ai_button` | admin | Публикует кнопку запуска AI в текущем канале |
| `/post_support_button` | admin | Публикует кнопку поддержки |
| `/post_reserve_button` | admin | Публикует кнопку резервации бита |
| `/post_submit_sale_button` | admin | Публикует кнопку отправки продажи |
| `/list_threads` | admin | Список активных приватных тредов в канале |
| `/close_thread <id>` | admin | Удаляет тред по ID |


---

## 7. Типичные проблемы

| Симптом | Причина | Решение |
|---|---|---|
| `bind: address already in use` при `docker compose up` | Порт 5432 занят системным Postgres | `sudo systemctl stop postgresql` или смени порт в compose |
| `InvalidPasswordError` | Старый docker volume с другим паролем | `docker compose down && docker volume rm <project>_pgdata` |
| `relation "students" does not exist` | Таблицы не созданы | `python -m merchant_bot.db.init_db` |
| `ArgumentError: Expected string or URL object, got None` | `.env` не загружен до импорта `engine.py` | `load_dotenv()` должен стоять раньше остальных импортов в `main.py` |
| `429 insufficient_quota` от OpenAI | Закончился баланс на API | Пополнить на platform.openai.com/settings/organization/billing |