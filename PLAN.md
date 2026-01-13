# Second Brain - План проекта

## 🎯 Цель проекта

Self-hosted система управления заметками на базе Obsidian с:
- Синхронизацией между устройствами через CouchDB
- Telegram ботом для быстрых заметок
- REST API для интеграций
- Web-просмотрщиком

---

## 📊 Статус разработки

| Phase | Описание | Статус |
|-------|----------|--------|
| 1 | Инфраструктура (Docker, CouchDB, Caddy) | ✅ Готово |
| 2 | Backend API (FastAPI) | ✅ Готово |
| 3 | Telegram Bot | ✅ Готово |
| 4 | Web Viewer | ✅ Готово |
| 5 | Claude API интеграция | ✅ Готово |
| 6 | Тестирование | ✅ Готово |
| 7 | **Деплой на Timeweb** | ✅ Готово |
| 8 | Дополнительные фичи | ⏳ Планируется |

---

## 🌐 Production Environment

### Сервер

| Параметр | Значение |
|----------|----------|
| **Хостинг** | Timeweb Cloud |
| **Server ID** | 6383807 |
| **IP** | 82.147.71.198 |
| **ОС** | Ubuntu 22.04 LTS |
| **Статус** | ✅ Online |

### URLs

| Сервис | URL | Описание |
|--------|-----|----------|
| **CouchDB** | https://notes.yakushev.me | База данных для Obsidian LiveSync |
| **REST API** | https://api.yakushev.me | API + Telegram бот |
| **Web Viewer** | https://api.yakushev.me/view | Просмотр заметок в браузере |

### Учётные данные

| Параметр | Значение |
|----------|----------|
| **CouchDB User** | `obsidian_admin` |
| **CouchDB Password** | `oLqAXQNR7shrTj8T/g5zsgWlYKS/uHeA8RXUD3UtnX0=` |
| **Database** | `obsidian_notes` |
| **API Token** | `e5200c625d5b1649aa17a6303d84d9bf75123b3a4d78b1db` |
| **Telegram Bot** | `@second_brain_yakushev_bot` (ID: 8186895415) |
| **Telegram Admin** | 1525875 |

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                     INTERNET                                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│  CADDY (Reverse Proxy + Auto SSL via Let's Encrypt)         │
│  ├── notes.yakushev.me → CouchDB:5984                       │
│  └── api.yakushev.me   → FastAPI:8000                       │
└─────────────────────────┬───────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌───────────────┐  ┌─────────────┐  ┌──────────────┐
│   CouchDB     │  │  FastAPI    │  │  Telegram    │
│   (Database)  │◄─┤  (REST API) │──┤  Bot         │
│   :5984       │  │  :8000      │  │  (polling)   │
└───────────────┘  └─────────────┘  └──────────────┘
        ▲
        │ Obsidian LiveSync
┌───────┴───────┐
│   Obsidian    │
│   (Desktop/   │
│    Mobile)    │
└───────────────┘
```

---

## 📁 Структура проекта

```
second-brain/
├── api/
│   ├── main.py              # FastAPI сервер + Web Viewer
│   ├── bot.py               # Telegram бот
│   ├── Dockerfile           # Сборка контейнера
│   ├── requirements.txt     # Python зависимости
│   ├── pytest.ini           # Конфигурация тестов
│   └── tests/               # Unit тесты
│       ├── conftest.py
│       └── test_api.py
├── couchdb/
│   ├── config/local.ini     # Конфигурация CouchDB
│   └── data/                # Данные (persistent volume)
├── caddy/
│   ├── data/                # SSL сертификаты
│   └── config/              # Конфигурация Caddy
├── scripts/
│   ├── setup-server.sh      # Настройка сервера
│   ├── init-couchdb.sh      # Инициализация БД
│   └── backup.sh            # Бэкап данных
├── tools/
│   ├── claude.py            # Claude API CLI
│   ├── review.sh            # Code review
│   ├── generate-tests.sh    # Генерация тестов
│   ├── debug.sh             # Отладка
│   └── usage-stats.sh       # Статистика API
├── docs/
│   ├── CLAUDE_API_SETUP.md  # Настройка Claude API
│   └── DEPLOY.md            # Инструкция деплоя
├── docker-compose.yml       # Оркестрация контейнеров
├── Caddyfile                # Конфигурация reverse proxy
├── Makefile                 # Команды разработки
├── .env.example             # Шаблон переменных окружения
├── .gitignore
├── README.md                # Основная документация
├── PLAN.md                  # План и roadmap
├── PROJECT_STATUS.md        # Полная информация о проекте
└── STATUS_RULES.md          # Правила обновления статуса
```

---

## ✅ Завершённый деплой (Phase 7)

### Чеклист деплоя

- [x] Установить Timeweb CLI (`pip install twc-cli`)
- [x] Авторизоваться (`twc config`)
- [x] Проверить сервер (ID: 6383807)
- [x] Настроить DNS (notes.yakushev.me, api.yakushev.me → 82.147.71.198)
- [x] Добавить SSH ключ на сервер
- [x] Установить Docker на сервер
- [x] Настроить файрвол (порты 22, 80, 443)
- [x] Скопировать проект на сервер
- [x] Создать `.env` с реальными данными
- [x] Исправить конфликт зависимостей (httpx 0.27.0)
- [x] Исправить health-check CouchDB (авторизация)
- [x] Запустить `docker compose up -d`
- [x] Инициализировать CouchDB (создать базу obsidian_notes)
- [x] Проверить работу всех сервисов
- [ ] Настроить Obsidian LiveSync на устройствах

---

## 🔮 Phase 8: Планируемые фичи

### Высокий приоритет
- [ ] **AI-обработка заметок** - автоматические теги, саммари
- [ ] **Напоминания** - уведомления в Telegram о задачах
- [ ] **Голосовые заметки** - транскрибация через Whisper

### Средний приоритет
- [ ] **Экспорт в PDF** - форматированный экспорт заметок
- [ ] **Полнотекстовый поиск** - улучшенный поиск через Elasticsearch
- [ ] **Граф связей** - визуализация связей между заметками

### Низкий приоритет
- [ ] **Веб-редактор** - редактирование заметок в браузере
- [ ] **Шаринг** - публичные ссылки на заметки
- [ ] **Мобильное приложение** - нативное приложение

---

## 📝 Журнал изменений

### 2026-01-12 — Исправление совместимости с Obsidian LiveSync
- ✅ Исправлена конфигурация CORS в CouchDB (`origins = *`)
- ✅ Добавлены CORS заголовки в Caddyfile (Access-Control-Allow-Origin: *)
- ✅ Добавлена обработка OPTIONS preflight запросов в Caddy
- ✅ Добавлена нормализация HTTP статус-кодов (201 → 200) для совместимости с LiveSync
- ✅ Конфигурация загружена на production сервер
- ✅ Контейнеры couchdb и caddy перезапущены
- 🐛 Исправлена ошибка "CORS settings on the remote database"
- 🐛 Исправлена ошибка "Failed to fetch by API. 201" (CouchDB возвращал 201 Created, LiveSync ожидал 200 OK)

### 2026-01-12 — Документация и деплой ✅
- ✅ Создан `PROJECT_STATUS.md` — полная информация о проекте
- ✅ Создан `STATUS_RULES.md` — правила актуализации статуса
- ✅ SSH ключ добавлен на сервер Timeweb
- ✅ Docker установлен на сервере
- ✅ Файрвол настроен (UFW)
- ✅ DNS настроен (notes.yakushev.me, api.yakushev.me)
- ✅ Проект загружен и распакован
- ✅ Исправлен конфликт httpx (0.26.0 → 0.27.0)
- ✅ Исправлен health-check CouchDB (добавлена авторизация)
- ✅ Все контейнеры запущены и healthy
- ✅ База данных obsidian_notes создана
- ✅ SSL сертификаты получены (Let's Encrypt)
- ✅ Telegram бот работает

### 2026-01-12 — Подготовка к деплою
- ✅ Создан `.env.example`
- ✅ Добавлены unit-тесты для API
- ✅ Добавлен health-check для API в docker-compose
- ✅ Создан `PLAN.md`
- ✅ Создан `docs/DEPLOY.md` с инструкцией
- ✅ Добавлена интеграция с Timeweb CLI в Makefile

### Ранее
- ✅ Базовая инфраструктура (Docker, CouchDB, Caddy)
- ✅ REST API на FastAPI
- ✅ Telegram бот
- ✅ Web Viewer
- ✅ Claude API интеграция для разработки
- ✅ Документация

---

## 🛠️ Полезные команды

### Локальная разработка
```bash
make dev              # Запуск в dev режиме
make test             # Запуск тестов
make test-cov         # Тесты с покрытием
make logs             # Просмотр логов
```

### Production (Timeweb)
```bash
# Управление сервером
make twc-servers                           # Список серверов
make deploy-status HOST=root@82.147.71.198 # Статус сервисов
make deploy-logs HOST=root@82.147.71.198   # Логи
make deploy-restart HOST=root@82.147.71.198 # Перезапуск

# SSH доступ
ssh -i ~/.ssh/id_ed25519_timeweb root@82.147.71.198
```

### Claude AI
```bash
make claude-review FILE=api/main.py
make claude-tests FILE=api/bot.py
make claude-debug SERVICE=notes-api
```

### Обслуживание
```bash
make backup           # Бэкап данных
make clean            # Очистка временных файлов
```

---

## 🔧 Настройка Obsidian LiveSync

### Параметры подключения

| Параметр | Значение |
|----------|----------|
| **URI** | `https://notes.yakushev.me` |
| **Username** | `obsidian_admin` |
| **Password** | `oLqAXQNR7shrTj8T/g5zsgWlYKS/uHeA8RXUD3UtnX0=` |
| **Database** | `obsidian_notes` |

### Инструкция
1. Установите плагин **Self-hosted LiveSync** в Obsidian
2. Введите параметры подключения
3. Нажмите **Test Connection** → OK
4. Включите E2E шифрование (рекомендуется)
5. Нажмите **Rebuild everything**

---

## 📚 Ссылки

- [Obsidian](https://obsidian.md/) - редактор заметок
- [Obsidian LiveSync](https://github.com/vrtmrz/obsidian-livesync) - плагин синхронизации
- [CouchDB](https://couchdb.apache.org/) - база данных
- [FastAPI](https://fastapi.tiangolo.com/) - веб-фреймворк
- [Timeweb Cloud](https://timeweb.cloud/) - хостинг
- [Timeweb CLI](https://github.com/timeweb-cloud/twc) - CLI для управления
