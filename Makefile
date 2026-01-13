.PHONY: help dev stop logs test test-cov test-watch lint format clean backup \
	claude-ask claude-review claude-tests claude-debug claude-refactor claude-docs claude-architecture claude-feature claude-usage \
	install-dev setup \
	twc-install twc-config twc-info twc-servers twc-server-info twc-ssh-keys twc-presets twc-os \
	deploy-pack deploy-upload deploy-ssh deploy-logs deploy-restart deploy-status

help: ## Показать эту справку
	@echo "Second Brain - доступные команды:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🤖 Claude AI команды работают через Anthropic API (без ограничений сессий)"

# Docker команды
dev: ## Запустить все сервисы в dev режиме
	docker compose up --build

stop: ## Остановить все сервисы
	docker compose down

logs: ## Показать логи всех сервисов
	docker compose logs -f

logs-api: ## Показать логи API
	docker compose logs -f notes-api

logs-db: ## Показать логи CouchDB
	docker compose logs -f couchdb

# Тестирование и качество кода
test: ## Запустить тесты
	cd api && python -m pytest tests/ -v

test-cov: ## Запустить тесты с покрытием
	cd api && python -m pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html

test-watch: ## Запустить тесты в watch режиме
	cd api && python -m pytest tests/ -v --tb=short -x

lint: ## Проверить код линтером
	cd api && pylint *.py

format: ## Форматировать код
	cd api && black *.py && isort *.py

clean: ## Очистить временные файлы
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete

backup: ## Создать backup
	./scripts/backup.sh

# Claude AI команды (через Anthropic API, без ограничений сессий!)
claude-ask: ## Задать вопрос Claude (make claude-ask Q="вопрос" FILES="file1.py file2.py")
	@if [ -z "$(Q)" ]; then \
		echo "❌ Ошибка: укажите вопрос"; \
		echo "Использование: make claude-ask Q=\"ваш вопрос\" FILES=\"file.py\""; \
		exit 1; \
	fi
	@./tools/claude.py "$(Q)" $(if $(FILES),-f $(FILES),)

claude-review: ## Code review файла (make claude-review FILE=api/main.py)
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Ошибка: укажите файл"; \
		echo "Использование: make claude-review FILE=api/main.py"; \
		exit 1; \
	fi
	@./tools/review.sh $(FILE)

claude-tests: ## Генерация тестов (make claude-tests FILE=api/main.py)
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Ошибка: укажите файл"; \
		echo "Использование: make claude-tests FILE=api/main.py"; \
		exit 1; \
	fi
	@./tools/generate-tests.sh $(FILE)

claude-debug: ## Отладка сервиса (make claude-debug SERVICE=notes-api DESC="описание")
	@./tools/debug.sh $(SERVICE) "$(DESC)"

claude-refactor: ## Рефакторинг кода (make claude-refactor FILE=api/main.py)
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Ошибка: укажите файл"; \
		echo "Использование: make claude-refactor FILE=api/main.py"; \
		exit 1; \
	fi
	@echo "🔄 Рефакторинг: $(FILE)"
	@./tools/claude.py "Рефактори этот код:\n\
	\n\
	1. Улучши читаемость и структуру\n\
	2. Следуй SOLID принципам\n\
	3. Убери дублирование (DRY)\n\
	4. Добавь/улучши type hints\n\
	5. Улучши обработку ошибок\n\
	6. Оптимизируй производительность\n\
	7. Добавь docstrings где нужно\n\
	\n\
	Верни полный рефакторенный код, готовый к использованию." \
		-f $(FILE) --max-tokens 8192

claude-docs: ## Генерация документации (make claude-docs)
	@echo "📚 Генерация документации API..."
	@mkdir -p docs
	@./tools/claude.py "Создай подробную документацию API в формате Markdown.\n\
	\n\
	Включи:\n\
	1. OpenAPI/Swagger спецификацию\n\
	2. Описание всех endpoints\n\
	3. Примеры запросов и ответов\n\
	4. Коды ошибок\n\
	5. Authentication\n\
	6. Rate limits\n\
	\n\
	Верни готовую документацию в Markdown." \
		-f api/main.py -f api/bot.py --max-tokens 8192 > docs/API.md
	@echo "✅ Документация сохранена: docs/API.md"

claude-architecture: ## Анализ архитектуры проекта
	@echo "🏗️ Анализ архитектуры Second Brain..."
	@./tools/claude.py "Проанализируй архитектуру проекта Second Brain.\n\
	\n\
	Оцени:\n\
	1. Структуру и организацию кода\n\
	2. Архитектурные паттерны\n\
	3. Масштабируемость\n\
	4. Безопасность\n\
	5. Производительность\n\
	6. DevOps практики\n\
	\n\
	Предложи конкретные улучшения с приоритетами." \
		-f api/main.py \
		-f api/bot.py \
		-f docker-compose.yml \
		-f Caddyfile \
		-f README.md \
		--max-tokens 8192

claude-feature: ## Разработка новой функции (make claude-feature DESC="описание")
	@if [ -z "$(DESC)" ]; then \
		echo "❌ Ошибка: опишите функцию"; \
		echo "Использование: make claude-feature DESC=\"экспорт в PDF\""; \
		exit 1; \
	fi
	@echo "💡 Планирование функции: $(DESC)"
	@./tools/claude.py "Я хочу добавить в Second Brain: $(DESC)\n\
	\n\
	Помоги спланировать реализацию:\n\
	\n\
	1. **Архитектура решения**\n\
	   - Какие компоненты затронуты?\n\
	   - Новые endpoints/функции\n\
	   - Изменения в БД\n\
	\n\
	2. **План реализации**\n\
	   - Пошаговый план\n\
	   - Какие файлы создать/изменить\n\
	   - Зависимости\n\
	\n\
	3. **Потенциальные проблемы**\n\
	   - Что может пойти не так?\n\
	   - Как тестировать?\n\
	\n\
	4. **Примеры кода**\n\
	   - Основные функции/endpoints\n\
	\n\
	Будь конкретным и практичным!" \
		-f api/main.py \
		-f api/bot.py \
		-f docker-compose.yml \
		--max-tokens 8192

claude-usage: ## Показать статистику использования API
	@./tools/usage-stats.sh

# Установка и настройка
install-dev: ## Установить dev зависимости
	@echo "📦 Установка зависимостей для разработки..."
	pip install anthropic black isort pylint pytest pytest-asyncio
	@echo "✅ Готово!"
	@echo ""
	@echo "🔑 Не забудьте добавить ANTHROPIC_API_KEY в .env"
	@echo "   Получить ключ: https://console.anthropic.com/settings/keys"

setup: ## Первоначальная настройка проекта
	@echo "🚀 Настройка Second Brain..."
	@if [ ! -f .env ]; then \
		echo "📝 Создаю .env из примера..."; \
		cp .env.example .env; \
		echo "⚠️  Отредактируйте .env файл и добавьте:"; \
		echo "   - ANTHROPIC_API_KEY (для Claude API)"; \
		echo "   - Остальные настройки для production"; \
	fi
	@echo "📦 Проверяю Docker..."
	@docker --version || (echo "❌ Docker не установлен!" && exit 1)
	@echo "✅ Готово!"
	@echo ""
	@echo "📖 Следующие шаги:"
	@echo "   1. Отредактируйте .env файл"
	@echo "   2. Запустите: make install-dev"
	@echo "   3. Запустите: make dev"
	@echo ""
	@echo "📚 Документация по Claude API: docs/CLAUDE_API_SETUP.md"

# ============================================
# Timeweb Cloud CLI (twc) команды
# ============================================

twc-install: ## Установить Timeweb CLI
	pip install twc-cli
	@echo "✅ TWC CLI установлен!"
	@echo "Запустите: twc config"

twc-config: ## Настроить Timeweb CLI (ввести токен)
	twc config

twc-info: ## Информация об аккаунте Timeweb
	twc account info

twc-servers: ## Список серверов
	twc server list

twc-server-info: ## Подробная информация о сервере (make twc-server-info ID=123)
	@if [ -z "$(ID)" ]; then \
		echo "❌ Укажите ID сервера: make twc-server-info ID=123"; \
		twc server list; \
		exit 1; \
	fi
	twc server info $(ID)

twc-ssh-keys: ## Список SSH ключей
	twc ssh-key list

twc-presets: ## Доступные конфигурации серверов
	twc server preset list

twc-os: ## Доступные операционные системы
	twc server os list

# Деплой команды
deploy-pack: ## Упаковать проект для деплоя
	@echo "📦 Упаковка проекта..."
	tar --exclude='couchdb/data' \
		--exclude='caddy/data' \
		--exclude='caddy/config' \
		--exclude='.env' \
		--exclude='__pycache__' \
		--exclude='.git' \
		--exclude='*.tar.gz' \
		-czvf second-brain-deploy.tar.gz .
	@echo "✅ Создан: second-brain-deploy.tar.gz"

deploy-upload: ## Загрузить на сервер (make deploy-upload HOST=root@IP)
	@if [ -z "$(HOST)" ]; then \
		echo "❌ Укажите HOST: make deploy-upload HOST=root@1.2.3.4"; \
		exit 1; \
	fi
	@echo "📤 Загрузка на $(HOST)..."
	scp second-brain-deploy.tar.gz $(HOST):~/
	@echo "✅ Загружено!"
	@echo ""
	@echo "📋 Следующие шаги на сервере:"
	@echo "   ssh $(HOST)"
	@echo "   cd ~ && tar -xzvf second-brain-deploy.tar.gz -C second-brain"
	@echo "   cd second-brain && cp .env.example .env && nano .env"
	@echo "   docker compose up -d"

deploy-ssh: ## SSH на сервер (make deploy-ssh HOST=root@IP)
	@if [ -z "$(HOST)" ]; then \
		echo "❌ Укажите HOST: make deploy-ssh HOST=root@1.2.3.4"; \
		exit 1; \
	fi
	ssh $(HOST)

deploy-logs: ## Просмотр логов на сервере (make deploy-logs HOST=root@IP)
	@if [ -z "$(HOST)" ]; then \
		echo "❌ Укажите HOST: make deploy-logs HOST=root@1.2.3.4"; \
		exit 1; \
	fi
	ssh $(HOST) "cd ~/second-brain && docker compose logs -f"

deploy-restart: ## Перезапуск на сервере (make deploy-restart HOST=root@IP)
	@if [ -z "$(HOST)" ]; then \
		echo "❌ Укажите HOST: make deploy-restart HOST=root@1.2.3.4"; \
		exit 1; \
	fi
	ssh $(HOST) "cd ~/second-brain && docker compose restart"

deploy-status: ## Статус сервисов на сервере (make deploy-status HOST=root@IP)
	@if [ -z "$(HOST)" ]; then \
		echo "❌ Укажите HOST: make deploy-status HOST=root@1.2.3.4"; \
		exit 1; \
	fi
	ssh $(HOST) "cd ~/second-brain && docker compose ps"
