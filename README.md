# Second Brain

Self-hosted система управления заметками на базе Obsidian с синхронизацией через CouchDB, REST API и Telegram-ботом.

## Возможности

- **Obsidian Livesync** - realtime синхронизация между устройствами
- **Telegram бот** - быстрые заметки и поиск
- **REST API** - программный доступ к заметкам
- **Web-просмотрщик** - доступ через браузер
- **End-to-end шифрование** - ваши данные защищены
- **Автоматический SSL** - через Let's Encrypt

## Требования

### Сервер (Timeweb Cloud или аналог)
- Ubuntu 22.04 LTS
- 2 vCPU
- 4 GB RAM
- 40 GB SSD
- ~700 руб/мес

### Домен
- Нужен свой домен с двумя поддоменами:
  - `notes.yourdomain.com` - для CouchDB
  - `api.yourdomain.com` - для API

---

## Установка

### Шаг 1: Создание сервера на Timeweb

1. Зарегистрируйтесь на [timeweb.cloud](https://timeweb.cloud)
2. Создайте облачный сервер:
   - ОС: Ubuntu 22.04
   - Конфигурация: 2 vCPU, 4 GB RAM, 40 GB NVMe
   - Создайте SSH-ключ или запомните пароль root
3. Запишите IP-адрес сервера

### Шаг 2: Настройка домена

Добавьте A-записи в DNS вашего домена:
```
notes.yourdomain.com → IP_сервера
api.yourdomain.com   → IP_сервера
```

### Шаг 3: Подключение к серверу

```bash
ssh root@IP_СЕРВЕРА
```

### Шаг 4: Настройка сервера

Скопируйте скрипт на сервер и запустите:

```bash
# Скачать и запустить скрипт настройки
curl -O https://raw.githubusercontent.com/YOUR_REPO/second-brain/main/scripts/setup-server.sh
bash setup-server.sh
```

Или вручную:

```bash
# Обновление системы
apt update && apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com | bash

# Установка Docker Compose
apt install docker-compose-plugin -y

# Настройка файрвола
ufw allow 22,80,443/tcp
ufw enable
```

### Шаг 5: Копирование проекта на сервер

На вашем компьютере:

```bash
# Архивирование проекта
cd ~/Projects
tar -czvf second-brain.tar.gz second-brain/

# Копирование на сервер
scp second-brain.tar.gz root@IP_СЕРВЕРА:~/
```

На сервере:

```bash
cd ~
tar -xzvf second-brain.tar.gz
cd second-brain
```

### Шаг 6: Настройка переменных окружения

```bash
# Копирование шаблона
cp .env.example .env

# Редактирование
nano .env
```

Заполните все поля в `.env`:

```bash
# Домены
DOMAIN=notes.yourdomain.com
API_DOMAIN=api.yourdomain.com

# CouchDB (сгенерируйте надежный пароль)
COUCHDB_USER=obsidian_admin
COUCHDB_PASSWORD=ваш_надежный_пароль_32_символа
COUCHDB_DATABASE=obsidian_notes

# API (сгенерируйте случайные строки)
API_SECRET_KEY=случайная_строка_64_символа
NOTES_API_TOKEN=токен_для_api_доступа

# Telegram (получите у @BotFather)
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHI...
TELEGRAM_ADMIN_ID=ваш_telegram_id
```

**Генерация паролей:**
```bash
# Пароль 32 символа
openssl rand -base64 32

# Ключ 64 символа
openssl rand -hex 32
```

### Шаг 7: Настройка email для SSL

Отредактируйте `Caddyfile`:

```bash
nano Caddyfile
```

Замените `your-email@example.com` на ваш email.

### Шаг 8: Запуск

```bash
# Запуск всех сервисов
docker compose up -d

# Проверка статуса
docker compose ps

# Просмотр логов
docker compose logs -f
```

### Шаг 9: Инициализация CouchDB

```bash
cd scripts
bash init-couchdb.sh
```

### Шаг 10: Проверка

```bash
# CouchDB
curl https://notes.yourdomain.com

# API
curl https://api.yourdomain.com/health
```

---

## Настройка Obsidian

### Desktop (Mac/Windows/Linux)

1. Скачайте [Obsidian](https://obsidian.md)
2. Создайте новое хранилище `SecondBrain`
3. Установите плагины:
   - Settings → Community Plugins → Browse
   - Найдите и установите: **Self-hosted LiveSync**
   - Найдите и установите: **Advanced Tables**

4. Настройте LiveSync:
   - Settings → Self-hosted LiveSync
   - URI: `https://notes.yourdomain.com`
   - Username: ваш `COUCHDB_USER`
   - Password: ваш `COUCHDB_PASSWORD`
   - Database name: `obsidian_notes`
   - End-to-end Encryption: включить
   - Passphrase: ваш `LIVESYNC_PASSPHRASE`

5. Нажмите **Test Connection** → должно показать OK
6. Нажмите **Rebuild everything**

### Mobile (iOS/Android)

1. Установите Obsidian из App Store / Google Play
2. Создайте хранилище `SecondBrain`
3. Установите плагин **Self-hosted LiveSync**
4. На Desktop: Settings → LiveSync → **Copy setup URI**
5. На Mobile: Settings → LiveSync → **Open setup URI** → вставьте URI

---

## Настройка Telegram бота

1. Откройте Telegram, найдите [@BotFather](https://t.me/BotFather)
2. Отправьте `/newbot`
3. Введите имя: `Second Brain Bot`
4. Введите username: `secondbrain_ваше_имя_bot`
5. Скопируйте токен в `.env` (`TELEGRAM_BOT_TOKEN`)

6. Получите ваш Telegram ID:
   - Найдите [@userinfobot](https://t.me/userinfobot)
   - Отправьте `/start`
   - Скопируйте ID в `.env` (`TELEGRAM_ADMIN_ID`)

7. Перезапустите сервисы:
   ```bash
   docker compose restart notes-api
   ```

8. Отправьте `/start` вашему боту

### Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Главное меню |
| `/note <текст>` | Создать заметку |
| `/recent` | Последние 10 заметок |
| `/summary` | Сводка за день |
| `/search <запрос>` | Поиск |
| Любой текст | Сохранить как заметку |

---

## API

### Аутентификация

Все запросы требуют заголовок:
```
X-API-Token: ваш_NOTES_API_TOKEN
```

### Endpoints

#### Создать заметку
```bash
curl -X POST https://api.yourdomain.com/api/notes/quick \
  -H "X-API-Token: YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "Текст заметки", "tags": ["idea"]}'
```

#### Последние заметки
```bash
curl https://api.yourdomain.com/api/notes/recent?limit=10 \
  -H "X-API-Token: YOUR_TOKEN"
```

#### Поиск
```bash
curl "https://api.yourdomain.com/api/notes/search?q=project" \
  -H "X-API-Token: YOUR_TOKEN"
```

#### Сводка за день
```bash
curl https://api.yourdomain.com/api/notes/summary \
  -H "X-API-Token: YOUR_TOKEN"
```

### Веб-просмотрщик

Откройте в браузере: `https://api.yourdomain.com/view`

---

## Обслуживание

### Обновление системы

```bash
# На сервере
apt update && apt upgrade -y
```

### Обновление контейнеров

```bash
cd ~/second-brain
docker compose pull
docker compose up -d --build
```

### Бэкап

```bash
cd ~/second-brain/scripts
bash backup.sh
```

Бэкапы сохраняются в `~/backups/`

### Просмотр логов

```bash
# Все сервисы
docker compose logs -f

# Конкретный сервис
docker compose logs -f couchdb
docker compose logs -f notes-api
docker compose logs -f caddy
```

### Перезапуск

```bash
docker compose restart
```

---

## Структура проекта

```
second-brain/
├── docker-compose.yml     # Оркестрация контейнеров
├── .env                   # Секреты (не коммитить!)
├── .env.example           # Шаблон настроек
├── Caddyfile              # Конфигурация reverse proxy
├── api/
│   ├── Dockerfile         # Сборка API
│   ├── requirements.txt   # Python зависимости
│   ├── main.py            # FastAPI сервер
│   └── bot.py             # Telegram бот
├── couchdb/
│   ├── config/
│   │   └── local.ini      # Конфигурация CouchDB
│   └── data/              # Данные (persistent)
├── caddy/
│   ├── data/              # SSL сертификаты
│   └── config/            # Конфигурация
└── scripts/
    ├── setup-server.sh    # Настройка сервера
    ├── init-couchdb.sh    # Инициализация БД
    └── backup.sh          # Бэкап данных
```

---

## Устранение проблем

### CouchDB не отвечает
```bash
docker compose logs couchdb
docker compose restart couchdb
```

### SSL сертификат не получен
```bash
# Проверьте DNS
nslookup notes.yourdomain.com

# Проверьте логи Caddy
docker compose logs caddy
```

### Telegram бот не отвечает
```bash
docker compose logs notes-api | grep -i telegram
docker compose restart notes-api
```

### Obsidian не синхронизируется
1. Проверьте Test Connection в настройках плагина
2. Убедитесь, что passphrase совпадает на всех устройствах
3. Попробуйте Rebuild everything

---

## Безопасность

- Все данные шифруются end-to-end в Obsidian
- SSL сертификаты автоматически обновляются
- API защищен токеном
- Telegram бот отвечает только владельцу (по ID)
- CouchDB требует аутентификацию

---

## Лицензия

MIT
