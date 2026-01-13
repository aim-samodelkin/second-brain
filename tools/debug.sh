#!/bin/bash
# Отладка через Claude API
# Использование: ./tools/debug.sh notes-api "бот не отвечает"

set -e

SERVICE=${1:-"notes-api"}
DESCRIPTION=${2:-"Сервис работает некорректно"}

echo "🐛 Отладка сервиса: $SERVICE"
echo "📝 Проблема: $DESCRIPTION"
echo ""

# Проверяем что сервис существует
if ! docker compose ps "$SERVICE" &>/dev/null; then
    echo "❌ Сервис '$SERVICE' не найден"
    echo ""
    echo "Доступные сервисы:"
    docker compose ps --services
    exit 1
fi

# Собираем логи
echo "📋 Собираю логи (последние 100 строк)..."
LOGS_FILE="/tmp/debug-${SERVICE}-$(date +%s).txt"
docker compose logs "$SERVICE" --tail 100 > "$LOGS_FILE"

# Проверяем статус контейнера
echo "🔍 Проверяю статус контейнера..."
STATUS_FILE="/tmp/status-${SERVICE}-$(date +%s).txt"
{
    echo "=== Docker Compose Status ==="
    docker compose ps "$SERVICE"
    echo ""
    echo "=== Container Inspect ==="
    docker compose ps -q "$SERVICE" | xargs docker inspect --format='{{.State.Status}}: {{.State.Health.Status}} - {{range .State.Health.Log}}{{.Output}}{{end}}'
} > "$STATUS_FILE" 2>&1

echo ""
echo "🤖 Отправляю данные Claude для анализа..."
echo ""

./tools/claude.py "Помоги отладить проблему в сервисе $SERVICE.

**Описание проблемы:**
$DESCRIPTION

**Контекст проекта:**
- Проект: Second Brain (система управления заметками)
- Стек: Python FastAPI + CouchDB + Telegram Bot + Docker
- Сервисы: couchdb, notes-api (FastAPI + Bot), caddy

**Твоя задача:**
1. Проанализируй логи и найди причину проблемы
2. Объясни что произошло простыми словами
3. Дай пошаговое решение
4. Предложи как предотвратить в будущем

Будь конкретным и практичным!" \
    -f "$LOGS_FILE" \
    -f "$STATUS_FILE" \
    -f "api/main.py" \
    -f "api/bot.py" \
    -f "docker-compose.yml" \
    --max-tokens 8192

# Очищаем временные файлы
rm "$LOGS_FILE" "$STATUS_FILE"

echo ""
echo "💡 Полезные команды для дальнейшей отладки:"
echo "   docker compose logs $SERVICE -f      # Следить за логами"
echo "   docker compose restart $SERVICE      # Перезапустить"
echo "   docker compose exec $SERVICE bash    # Войти в контейнер"
echo "   docker compose up $SERVICE --build   # Пересобрать и запустить"
