#!/usr/bin/env python3
"""
Claude CLI обертка для работы через API без ограничений сессий
Использование: ./tools/claude.py "ваш вопрос" -f file1.py -f file2.py
"""
import os
import sys
import anthropic
from pathlib import Path

def get_api_key():
    """Получает API ключ из переменных окружения"""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ Ошибка: ANTHROPIC_API_KEY не найден")
        print("\n📝 Решение:")
        print("1. Создайте .env файл с ключом:")
        print("   ANTHROPIC_API_KEY=sk-ant-api03-...")
        print("\n2. Загрузите переменные:")
        print("   source .env")
        print("\n3. Или установите напрямую:")
        print("   export ANTHROPIC_API_KEY=sk-ant-api03-...")
        print("\n🔑 Получить ключ: https://console.anthropic.com/settings/keys")
        sys.exit(1)
    return api_key

def read_files(file_paths):
    """Читает файлы и возвращает их содержимое с форматированием"""
    if not file_paths:
        return ""
    
    contents = []
    for path in file_paths:
        try:
            file_path = Path(path)
            if not file_path.exists():
                contents.append(f"\n### ❌ Файл не найден: {path}\n")
                continue
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Определяем язык по расширению
                ext = file_path.suffix.lstrip('.')
                lang_map = {
                    'py': 'python',
                    'js': 'javascript',
                    'ts': 'typescript',
                    'yml': 'yaml',
                    'yaml': 'yaml',
                    'json': 'json',
                    'sh': 'bash',
                    'md': 'markdown',
                }
                lang = lang_map.get(ext, ext or 'text')
                
                contents.append(f"\n### 📄 Файл: {path}\n```{lang}\n{content}\n```\n")
        except Exception as e:
            contents.append(f"\n### ❌ Ошибка чтения {path}: {e}\n")
    
    return "\n".join(contents)

def ask_claude(prompt, files=None, model="claude-3-5-sonnet-20241022", max_tokens=4096, system=None):
    """
    Отправляет запрос к Claude через API
    
    Args:
        prompt: Текст запроса
        files: Список путей к файлам для контекста
        model: Модель Claude
        max_tokens: Максимум токенов в ответе
        system: Системный промпт (опционально)
    """
    client = anthropic.Anthropic(api_key=get_api_key())
    
    # Собираем полный промпт с файлами
    full_prompt = prompt
    if files:
        files_content = read_files(files)
        if files_content:
            full_prompt = f"{prompt}\n\n---\n\n**Контекст из файлов:**{files_content}"
    
    # Системный промпт по умолчанию для разработки
    if system is None:
        system = """Ты опытный Python разработчик и архитектор.
Помогаешь с проектом Second Brain - системой управления заметками.

При ответах:
- Давай конкретные, действенные советы
- Предлагай code examples когда уместно
- Следуй best practices для Python, FastAPI, Docker
- Проверяй безопасность и производительность
- Будь кратким но информативным"""
    
    # Отправляем запрос
    try:
        print("🤖 Отправляю запрос к Claude API...")
        print(f"📊 Модель: {model}")
        if files:
            print(f"📁 Файлов в контексте: {len(files)}")
        print()
        
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[
                {"role": "user", "content": full_prompt}
            ]
        )
        
        # Выводим ответ
        response_text = message.content[0].text
        print(response_text)
        print()
        
        # Показываем статистику
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens
        
        # Расчет стоимости
        costs = {
            "claude-3-5-sonnet-20241022": (3, 15),
            "claude-3-sonnet-20240229": (3, 15),
            "claude-3-opus-20240229": (15, 75),
            "claude-3-haiku-20240307": (0.25, 1.25),
        }
        
        input_cost_per_mtok, output_cost_per_mtok = costs.get(model, (3, 15))
        cost_input = (input_tokens / 1_000_000) * input_cost_per_mtok
        cost_output = (output_tokens / 1_000_000) * output_cost_per_mtok
        total_cost = cost_input + cost_output
        
        print("=" * 70)
        print(f"📊 Статистика запроса:")
        print(f"   ⬆️  Входящие токены:  {input_tokens:>6,} (~${cost_input:.4f})")
        print(f"   ⬇️  Исходящие токены: {output_tokens:>6,} (~${cost_output:.4f})")
        print(f"   💰 Общая стоимость:   ${total_cost:.4f}")
        print("=" * 70)
        print(f"📈 Мониторинг: https://console.anthropic.com/settings/usage")
        
        return response_text
        
    except anthropic.APIError as e:
        print(f"❌ API Ошибка: {e}")
        print("\n💡 Возможные причины:")
        print("   - Неверный API ключ")
        print("   - Недостаточно credits на балансе")
        print("   - Rate limit превышен")
        print("   - Проблемы с сетью")
        print("\n🔧 Проверьте: https://console.anthropic.com/")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='🤖 Claude CLI через Anthropic API (без ограничений сессий)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

  # Простой вопрос
  %(prog)s "объясни структуру проекта"
  
  # С контекстом файлов
  %(prog)s "как улучшить этот код?" -f api/main.py
  
  # Несколько файлов
  %(prog)s "проанализируй архитектуру" -f api/main.py -f docker-compose.yml
  
  # Быстрая модель для простых вопросов
  %(prog)s "быстрый вопрос" -m claude-3-haiku-20240307
  
  # Больше токенов для длинных ответов
  %(prog)s "напиши подробную документацию" -f api/main.py -t 8192

Модели и стоимость:
  haiku   ($0.25/$1.25 за 1M)  - быстро и дешево, для простых задач
  sonnet  ($3/$15 за 1M)       - баланс качества и цены (по умолчанию)
  opus    ($15/$75 за 1M)      - максимальное качество, для сложных задач
        """
    )
    
    parser.add_argument('prompt', help='Ваш вопрос или задача для Claude')
    parser.add_argument('-f', '--files', nargs='+', 
                       help='Файлы для контекста (можно указать несколько)')
    parser.add_argument('-m', '--model', 
                       default='claude-3-5-sonnet-20241022',
                       choices=[
                           'claude-3-5-sonnet-20241022',
                           'claude-3-sonnet-20240229',
                           'claude-3-opus-20240229',
                           'claude-3-haiku-20240307',
                       ],
                       help='Модель Claude (по умолчанию: sonnet 3.5)')
    parser.add_argument('-t', '--max-tokens', type=int, default=4096,
                       help='Максимум токенов в ответе (по умолчанию: 4096)')
    parser.add_argument('-s', '--system', 
                       help='Системный промпт (опционально)')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    
    args = parser.parse_args()
    
    # Короткие алиасы для моделей
    model_aliases = {
        'sonnet': 'claude-3-5-sonnet-20241022',
        'opus': 'claude-3-opus-20240229',
        'haiku': 'claude-3-haiku-20240307',
    }
    model = model_aliases.get(args.model, args.model)
    
    ask_claude(args.prompt, args.files, model, args.max_tokens, args.system)

if __name__ == '__main__':
    main()
