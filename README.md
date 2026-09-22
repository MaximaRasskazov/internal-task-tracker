# Internal Task Tracker

Корпоративный таск-трекер по заданию 2: проекты, Kanban-доски, задачи, совместная работа и аналитика.
Текущий этап — серверная часть. Бэкенд работает с настоящим PostgreSQL; Vue-интерфейс будет отдельным этапом.

## Что реализовано

- Регистрация, вход и выход; JWT в HttpOnly cookie, серверные сессии, CSRF и ограничение неудачных входов.
- Глобальные роли admin / pm / developer, членство в проекте и передача владения.
- Проекты, участники, доски, колонки и теги с проверкой прав на сервере.
- Все поля задачи, назначение исполнителя, мягкое удаление, комментарии и неизменяемая история.
- Атомарный порядок карточек и защита от потери параллельных изменений через `expected_version`.
- Совместные фильтры по исполнителю, тегам, сроку, приоритету, колонкам и тексту.
- WebSocket-уведомления после сохранения, heartbeat, отзыв доступа и восстановление по снимку доски.
- Аналитика текущих колонок и первых завершений задач с учетом часового пояса проекта.
- Миграции, демоданные, OpenAPI, автоматические тесты PostgreSQL, конфигурация Docker Compose и CI.

Состояние проверок и ограничения фиксируются в [отчете о проверке](docs/reports/verification.md).
Наличие конфигурации CI само по себе не означает, что workflow уже выполнен на GitHub.

## Документы команды

| Документ | Для чего нужен |
|---|---|
| [product_spec.md](product_spec.md) | Единый контракт продукта, API, прав и приемки |
| [TEAM_ROADMAP.md](TEAM_ROADMAP.md) | Задачи, зависимости и критерии готовности команды |
| [Текущее состояние](docs/team-progress.md) | Что проверено на серверном этапе и что делать дальше |
| [CLAUDE.md](CLAUDE.md) | Общие правила работы в репозитории |
| [Архитектура](docs/architecture.md) | Слои приложения, схема БД и причины решений |
| [Отчет по бэкенду](docs/reports/backend.md) | Подробное объяснение серверной логики и ее проверки |
| [Отчет по БД](docs/reports/database.md) | Миграции, связи, ограничения, роли подключения |
| [Эксплуатация](docs/operations.md) | Запуск, конфигурация, диагностика и сохранность данных |
| [Передача фронтенду](docs/frontend-handoff.md) | Практический порядок подключения Vue к API |
| [План сдачи](course_delivery_plan.md) | Пять мини-отчетов и защита |

## Стек

Python 3.13, FastAPI, Pydantic 2, SQLAlchemy 2 async, asyncpg, Alembic, PostgreSQL 18,
PyJWT, pwdlib/Argon2id. Проверки: pytest, HTTPX, Ruff и mypy.
Точные версии Python и всех библиотек закреплены в `backend/.python-version` и `backend/uv.lock`.

## Быстрый запуск через Docker

Нужны Git, uv и запущенный Docker Desktop с Linux-контейнерами. Команды подходят для PowerShell и терминала macOS.

```sh
cd backend
uv sync --frozen
uv run python -m app.cli.init_env
cd ..
docker compose config --quiet
docker compose up --build --wait backend
docker compose run --rm seed
```

`init_env` создает локальные случайные секреты и сохраняет существующий `.env` без изменений.
Compose ожидает готовность PostgreSQL, запускает миграции отдельным процессом и затем поднимает API.

- Swagger: [http://localhost:8000/docs](http://localhost:8000/docs).
- Готовность БД и миграций: [http://localhost:8000/api/v1/health/ready](http://localhost:8000/api/v1/health/ready).
- Остановка с сохранением БД: `docker compose down`.

Том `postgres_data` хранит данные между перезапусками. Команда `down --volumes` удаляет том;
она применяется только к одноразовому окружению CI, а не к рабочей БД команды.

Если uv на компьютере еще нет, файл окружения можно создать контейнером:

```sh
docker build --target init-env -t itt-init-env ./backend
docker run --rm --mount "type=bind,source=${PWD},target=/workspace" itt-init-env
docker compose up --build --wait backend
```

## Локальный запуск без Docker

Нужны PostgreSQL 18, Python 3.13 и uv. В PostgreSQL заранее создаются база `tracker`,
ее владелец `tracker_owner` и ограниченный пользователь `tracker`; порядок описан в
[эксплуатации](docs/operations.md). Локальное окружение использует `127.0.0.1:5433`.

```sh
cd backend
uv sync --frozen
uv run python -m app.cli.init_env
uv run alembic upgrade head
uv run python -m app.cli.seed
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

Для точного воспроизведения учебных сроков seed принимает `--reference-date 2026-09-11`.
Повторный запуск не дублирует данные и не сбрасывает существующие пароли.

## Первый вход и проверка через Swagger

1. Открыть `/docs`, выполнить `POST /api/v1/auth/login` с `pm@example.test`
   и значением `DEMO_PASSWORD` из локального `.env`.
2. Браузер сохранит HttpOnly cookie. Из JSON-ответа скопировать `csrf_token`.
3. Для операций изменения вставлять этот токен в поле `X-CSRF-Token` в Swagger.
4. Получить проекты, открыть доску, создать или изменить задачу.
5. Выполнить `/auth/logout` с CSRF-токеном. Повторное использование этой сессии вернет 401.

Swagger в браузере сам отправляет Origin. В Postman и других HTTP-клиентах для write-запросов
нужно явно установить `Origin: http://localhost:8000`, для JSON-тела — `Content-Type: application/json`.
Отсутствие Origin намеренно отклоняется. Вход возвращает CSRF-токен, но не JWT.

Учебные пользователи: `admin@example.test`, `pm@example.test`, `dev-a@example.test`,
`dev-b@example.test`, `outsider@example.test`, `pm-private@example.test`.
У последних двух нет доступа к проекту TEAM. Пароль хранится только в `.env`.

Для первого администратора без демоданных используются переменные
`BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_NAME`, `BOOTSTRAP_ADMIN_PASSWORD` и команда:

```sh
uv run python -m app.cli.bootstrap_admin
```

## Проверки перед коммитом

Из `backend`:

```sh
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest -m "not integration"
uv run python -m app.cli.export_openapi --check
```

Для интеграции заранее нужна отдельная БД `tracker_test` с теми же владельцем и runtime-ролью.
Из корня:

```sh
python scripts/test-backend.py --integration
```

Скрипт читает локальное окружение, подставляет отдельную БД с суффиксом `_test` и не выводит
секреты. Можно явно задать `TEST_DATABASE_URL` и `TEST_MIGRATION_DATABASE_URL`.
Тесты очищают только проверенную тестовую БД. Не запускать параллельные независимые наборы
против одной тестовой БД; фикстуры дополнительно сериализуют очистку advisory lock.

После изменения публичных DTO нужно выполнить `uv run python -m app.cli.export_openapi`
и включить обновленный `docs/api/openapi.json` в тот же коммит.

## Структура

```text
backend/
  app/
    api/           HTTP-маршруты, сессия запроса, WebSocket
    cli/           init_env, bootstrap_admin, seed, export_openapi
    core/          настройки, ошибки, логирование, криптография
    db/            модели, подключения, согласованное чтение
    schemas/       входные и выходные DTO
    services/      права, транзакции, представления, события, аналитика
    main.py        сборка приложения и жизненный цикл
  migrations/      версия схемы, ограничения, права runtime-роли
  tests/           unit и интеграционные сценарии PostgreSQL
infra/postgres/    первоначальное создание runtime-роли в контейнере
scripts/           запуск проверок без вывода секретов
docs/              контракт, архитектура, инструкции и отчеты
.github/workflows/ автоматические проверки и контейнерный smoke test
compose.yaml       PostgreSQL → миграции → FastAPI
compose.dev.yaml   необязательный доступ к Docker-БД с хоста
```

## Совместная работа

Функции разрабатываются в отдельных ветках; коммит описывает поведение и причину изменения.
Изменения API включают DTO, тесты и OpenAPI. Миграции, lockfile и общие маршруты имеют
одного текущего владельца изменения. Перед слиянием другой участник проверяет код и
сценарий на своей машине. Подробные роли и карточки находятся в `TEAM_ROADMAP.md`.
