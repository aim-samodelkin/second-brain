# Деплой Second Brain на Timeweb Cloud

Пошаговая инструкция по развертыванию проекта на Timeweb Cloud с использованием [TWC CLI](https://github.com/timeweb-cloud/twc).

## Содержание

1. [Установка TWC CLI](#1-установка-twc-cli)
2. [Получение API токена](#2-получение-api-токена)
3. [Настройка CLI](#3-настройка-cli)
4. [Управление сервером](#4-управление-сервером)
5. [Деплой проекта](#5-деплой-проекта)
6. [Проверка работы](#6-проверка-работы)
7. [Полезные команды](#7-полезные-команды)

---

## 1. Установка TWC CLI

### Через pip (рекомендуется)

```bash
pip install twc-cli
```

### Через pipx (изолированно)

```bash
pipx install twc-cli
```

### Проверка установки

```bash
twc --version
```

### Автодополнение (опционально)

```bash
twc --install-completion
```

---

## 2. Получение API токена

1. Зайдите в [Timeweb Cloud Console](https://timeweb.cloud/my/api-keys)
2. Нажмите **"Создать токен"**
3. Введите название (например, "second-brain-deploy")
4. Скопируйте токен (показывается только один раз!)

---

## 3. Настройка CLI

```bash
twc config
```

Введите токен и нажмите Enter. Конфигурация сохранится в `~/.twc`.

### Проверка подключения

```bash
twc account info
```

---

## 4. Управление сервером

### 4.1 Просмотр доступных серверов

```bash
twc server list
```

### 4.2 Создание нового сервера

```bash
# Посмотреть доступные конфигурации
twc server preset list

# Посмотреть доступные ОС
twc server os list

# Создать сервер
twc server create \
  --name second-brain \
  --preset-id <PRESET_ID> \
  --os-id 61 \
  --ssh-key-id <SSH_KEY_ID>
```

> **Рекомендуемый preset:** 2 vCPU, 4 GB RAM, 40 GB NVMe (~700 руб/мес)
> **OS ID 61** = Ubuntu 22.04 LTS

### 4.3 Управление SSH-ключами

```bash
# Список ключей
twc ssh-key list

# Добавить ключ
twc ssh-key create --name macbook --public-key "$(cat ~/.ssh/id_rsa.pub)"
```

### 4.4 Получение IP сервера

```bash
twc server list --output json | jq '.[].networks[0].ips[0].ip'
```

Или через веб-консоль Timeweb Cloud.

---

## 5. Деплой проекта

### 5.1 Настройка DNS

В панели управления вашего домена добавьте A-записи:

```
notes.yourdomain.com  →  IP_СЕРВЕРА
api.yourdomain.com    →  IP_СЕРВЕРА
```

Дождитесь обновления DNS (обычно 5-30 минут).

### 5.2 Подключение к серверу

```bash
ssh root@IP_СЕРВЕРА
```

### 5.3 Установка Docker на сервере

```bash
# Обновление системы
apt update && apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com | bash

# Установка Docker Compose plugin
apt install docker-compose-plugin -y

# Проверка
docker --version
docker compose version
```

### 5.4 Настройка файрвола

```bash
ufw allow 22,80,443/tcp
ufw --force enable
```

### 5.5 Копирование проекта на сервер

На вашем компьютере:

```bash
# Архивирование (исключая данные и секреты)
cd ~/Projects
tar --exclude='couchdb/data' \
    --exclude='caddy/data' \
    --exclude='caddy/config' \
    --exclude='.env' \
    --exclude='__pycache__' \
    -czvf second-brain.tar.gz second-brain/

# Копирование на сервер
scp second-brain.tar.gz root@IP_СЕРВЕРА:~/
```

На сервере:

```bash
cd ~
tar -xzvf second-brain.tar.gz
cd second-brain
```

### 5.6 Создание .env файла

```bash
cp .env.example .env
nano .env
```

Заполните все переменные:

```bash
# Домены (замените на свои!)
DOMAIN=notes.yourdomain.com
API_DOMAIN=api.yourdomain.com

# CouchDB
COUCHDB_USER=obsidian_admin
COUCHDB_PASSWORD=$(openssl rand -base64 32)
COUCHDB_DATABASE=obsidian_notes

# API
API_SECRET_KEY=$(openssl rand -hex 32)
NOTES_API_TOKEN=$(openssl rand -hex 24)

# Telegram
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHI...  # от @BotFather
TELEGRAM_ADMIN_ID=123456789                 # от @userinfobot
```

### 5.7 Настройка Caddyfile

```bash
nano Caddyfile
```

Замените `your-email@example.com` на ваш email для Let's Encrypt.

### 5.8 Запуск сервисов

```bash
# Запуск
docker compose up -d

# Проверка статуса
docker compose ps

# Просмотр логов
docker compose logs -f
```

### 5.9 Инициализация CouchDB

```bash
cd scripts
bash init-couchdb.sh
```

---

## 6. Проверка работы

### 6.1 Проверка endpoints

```bash
# CouchDB
curl https://notes.yourdomain.com

# API Health
curl https://api.yourdomain.com/health

# API (с токеном)
curl https://api.yourdomain.com/api/notes/recent \
  -H "X-API-Token: YOUR_NOTES_API_TOKEN"
```

### 6.2 Проверка Telegram бота

Отправьте `/start` вашему боту в Telegram.

### 6.3 Настройка Obsidian

1. Установите плагин **Self-hosted LiveSync**
2. Настройте подключение:
   - URI: `https://notes.yourdomain.com`
   - Username: значение `COUCHDB_USER`
   - Password: значение `COUCHDB_PASSWORD`
   - Database: `obsidian_notes`
3. Включите E2E шифрование (опционально)
4. Нажмите **Test Connection** → OK
5. Нажмите **Rebuild everything**

---

## 7. Полезные команды

### TWC CLI

```bash
# Информация об аккаунте
twc account info

# Список серверов
twc server list

# Перезагрузка сервера
twc server reboot <SERVER_ID>

# Логи действий
twc server action list <SERVER_ID>

# SSH подключение (если настроено)
twc server ssh <SERVER_ID>
```

### На сервере

```bash
# Просмотр логов
docker compose logs -f

# Перезапуск сервиса
docker compose restart notes-api

# Обновление (после изменений)
docker compose pull
docker compose up -d --build

# Бэкап
./scripts/backup.sh
```

### Мониторинг

```bash
# Использование ресурсов
docker stats

# Место на диске
df -h

# Логи системы
journalctl -f
```

---

## Troubleshooting

### SSL сертификат не выдаётся

```bash
# Проверьте DNS
nslookup notes.yourdomain.com

# Проверьте логи Caddy
docker compose logs caddy
```

### CouchDB не отвечает

```bash
docker compose logs couchdb
docker compose restart couchdb
```

### Telegram бот не работает

```bash
# Проверьте логи
docker compose logs notes-api | grep -i telegram

# Проверьте токен
echo $TELEGRAM_BOT_TOKEN

# Перезапустите
docker compose restart notes-api
```

### Obsidian не синхронизируется

1. Проверьте **Test Connection** в настройках плагина
2. Убедитесь, что passphrase совпадает на всех устройствах
3. Попробуйте **Rebuild everything**

---

## Автоматизация деплоя

Добавьте в `~/.bashrc` или `~/.zshrc`:

```bash
# Second Brain deployment
export SB_SERVER_IP="YOUR_SERVER_IP"
alias sb-ssh="ssh root@\$SB_SERVER_IP"
alias sb-logs="sb-ssh 'cd ~/second-brain && docker compose logs -f'"
alias sb-restart="sb-ssh 'cd ~/second-brain && docker compose restart'"
```

---

## Ссылки

- [TWC CLI GitHub](https://github.com/timeweb-cloud/twc)
- [TWC CLI Документация](https://timeweb.cloud/docs/twc-cli)
- [Timeweb Cloud Console](https://timeweb.cloud/my)
- [Obsidian LiveSync](https://github.com/vrtmrz/obsidian-livesync)
