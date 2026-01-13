#!/bin/bash
# Генерация unit тестов через Claude API
# Использование: ./tools/generate-tests.sh api/main.py

set -e

if [ -z "$1" ]; then
    echo "❌ Ошибка: укажите файл для генерации тестов"
    echo "Использование: $0 <файл.py>"
    exit 1
fi

FILE="$1"

if [ ! -f "$FILE" ]; then
    echo "❌ Файл не найден: $FILE"
    exit 1
fi

# Определяем имя выходного файла
BASENAME=$(basename "$FILE" .py)
DIRNAME=$(dirname "$FILE")
OUTPUT_FILE="${DIRNAME}/tests/test_${BASENAME}.py"

# Создаем папку tests если не существует
mkdir -p "${DIRNAME}/tests"

echo "🧪 Генерация тестов для: $FILE"
echo "📝 Выходной файл: $OUTPUT_FILE"
echo ""

./tools/claude.py "Создай comprehensive набор unit тестов для этого кода.

**Требования:**

1. Используй pytest
2. Async тесты где нужно (pytest-asyncio)
3. Моки для внешних зависимостей:
   - CouchDB запросы (mock aiohttp)
   - Telegram API (mock telegram.Bot)
   - Переменные окружения
4. Покрой все функции и методы
5. Тестируй edge cases:
   - Пустые входные данные
   - Некорректные данные
   - Ошибки сети
   - Таймауты
6. Используй fixtures для setup/teardown
7. Параметризованные тесты где уместно

**Структура тестов:**
\`\`\`python
import pytest
from unittest.mock import Mock, AsyncMock, patch

# Fixtures
@pytest.fixture
def mock_couch():
    ...

# Tests
class TestClassName:
    def test_function_success(self):
        ...
    
    def test_function_error_handling(self):
        ...
    
    @pytest.mark.asyncio
    async def test_async_function(self):
        ...
    
    @pytest.mark.parametrize('input,expected', [...])
    def test_parametrized(self, input, expected):
        ...
\`\`\`

**Верни только код тестов, без дополнительных объяснений.**
Код должен быть готов к использованию." -f "$FILE" --max-tokens 8192 > "$OUTPUT_FILE"

echo ""
echo "✅ Тесты сгенерированы: $OUTPUT_FILE"
echo ""
echo "🚀 Запустить тесты:"
echo "   cd $DIRNAME && python -m pytest tests/test_${BASENAME}.py -v"
