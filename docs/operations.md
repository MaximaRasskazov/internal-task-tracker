# Запуск и эксплуатация

## Два способа разработки

Для команды базовый способ — Docker Compose: одинаковые версии PostgreSQL и Python,
миграции до запуска приложения и отдельный том данных. Нативный PostgreSQL полезен
для отладки и работы до готовности Docker/WSL. Это два разных экземпляра БД.
Данные между ними не копируются автоматически.

На текущей Windows-машине нативный PostgreSQL слушает только `127.0.0.1:5433`.
`compose.dev.yaml` по умолчанию публикует контейнерную БД на `127.0.0.1:5434`, чтобы
не занимать этот же порт. Внутри контейнеров PostgreSQL доступен как `db:5432`.

## Раздельные учетные записи БД

`tracker_owner` владеет схемой и выполняет Alembic. `tracker` выполняет HTTP-запросы
и seed, не является владельцем, суперпользователем и не может создавать таблицы.
Это ограничивает последствия ошибки в приложении: runtime не может менять миграции
и не может переписать или удалить журнал аудита.

Compose создает роли через `infra/postgres/init-app-role.sh` на пустом томе. Для нативного
сервера администратор PostgreSQL выполняет первоначальную настройку. Пароли ролей
должны совпадать с локальным `.env`; не вставлять реальные значения в SQL-файлы репозитория.
В интерактивном `psql` пароль можно задать командой `\password`, которая не записывает
его в SQL-историю в открытом виде.

```sql
CREATE ROLE tracker_owner LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE tracker LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
\password tracker_owner
\password tracker
CREATE DATABASE tracker OWNER tracker_owner;
CREATE DATABASE tracker_test OWNER tracker_owner;
```

Следующий блок применяется к **каждой** из двух баз, подключившись администратором:

```sql
ALTER SCHEMA public OWNER TO tracker_owner;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT CONNECT ON DATABASE tracker TO tracker;
GRANT CONNECT ON DATABASE tracker_test TO tracker;
GRANT USAGE ON SCHEMA public TO tracker;
ALTER DEFAULT PRIVILEGES FOR ROLE tracker_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO tracker;
ALTER DEFAULT PRIVILEGES FOR ROLE tracker_owner IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO tracker;
```

Миграция 0003 после создания таблиц сужает эти права для `audit_events` и
`alembic_version`. Рабочий `DATABASE_URL` использует tracker, а
`MIGRATION_DATABASE_URL` — tracker_owner. Запуск API с паролем владельца схемы не нужен.

## Переменные окружения

| Переменная | Назначение |
|---|---|
| APP_ENV | local, demo, test или production; определяет допустимость учебных данных |
| DATABASE_URL | Подключение runtime через postgresql+asyncpg |
| MIGRATION_DATABASE_URL | Подключение владельца для миграций; серверу в контейнере не передается |
| JWT_SECRET | Случайный секрет подписи JWT, не менее 32 символов |
| DEMO_PASSWORD | Пароль только учебных пользователей; запрещен в production |
| ALLOWED_ORIGINS | Точный список разрешенных HTTP(S) origin без путей и wildcard |
| COOKIE_SECURE | true при HTTPS; false разрешен только для loopback origins |
| SESSION_TTL_SECONDS | Срок сессии; по умолчанию 8 часов |
| API_LOCK_TIMEOUT_MS | Ограничение ожидания блокировки PostgreSQL |
| LOGIN_RATE_LIMIT_PER_MINUTE | Число неудачных входов с одного IP за минуту |
| DOCS_ENABLED | Включение /docs, /redoc и /openapi.json; для закрытой публикации задать false |
| LOG_LEVEL | Уровень структурированных логов |

`POSTGRES_PASSWORD` и `POSTGRES_OWNER_PASSWORD` используются Compose для первоначальной
настройки ролей. Изменение этих значений в `.env` не меняет автоматически пароли уже
существующих ролей PostgreSQL. При переносе окружения согласованно обновляются роли
и URL, без удаления рабочего тома.

## Повторный запуск и диагностика

```sh
docker compose ps
docker compose logs --tail=100 backend migrate
docker compose up --wait backend
```

`/health/live` подтверждает жизнь процесса. `/health/ready` дополнительно проверяет БД
и совпадение всех Alembic heads с кодом. Ответ 503 означает, что сервис пока не готов:
проверить PostgreSQL, строку подключения и выполнение миграций.

Ошибки доступа разделены: 401 — нет действующей сессии, 403 — запрещенное действие
или Origin/CSRF, 404 — ресурс отсутствует или проект недоступен. 409 при изменении задачи
требует повторного чтения; автоматический повтор неизвестно завершившегося POST небезопасен.

В логах есть request_id, маршрут, статус и длительность. Не выводятся тело запроса,
cookie, пароль, JWT и строка подключения. Uvicorn запускается с `--no-access-log`,
поскольку его стандартный лог может включать произвольную query string.

## Резервная копия

До обновления используемой БД создать копию. Пароль вводится в интерактивном запросе,
а не записывается в команду или отчет:

```sh
pg_dump -h 127.0.0.1 -p 5433 -U tracker_owner -W -F c -f tracker-backup.dump tracker
```

Файл содержит данные проекта, поэтому хранится вне Git. Восстановление проверяется
в **новой** отдельной базе, созданной администратором. Рабочая база не заменяется:

```sh
createdb -h 127.0.0.1 -p 5433 -U postgres -W -O tracker_owner tracker_restore_check
pg_restore -h 127.0.0.1 -p 5433 -U tracker_owner -W -d tracker_restore_check tracker-backup.dump
```

После восстановления сверить версию миграции, количество записей, связи и доступ runtime.
Результат фактической проверки хранится в [отчете](reports/backup-restore.md).

## Ограничения первого серверного релиза

- WebSocket и ограничитель входов хранят оперативное состояние одного процесса.
  Запускать `--workers 1`; при горизонтальном масштабировании потребуется общий канал.
- HTTP-снимки восстанавливают состояние после потери события; гарантии доставки каждого
  промежуточного уведомления ровно один раз нет. Постоянная история находится в PostgreSQL.
- Backend не обслуживает Vue-страницы. UI, визуальная адаптивность и браузерная приемка
  двух готовых интерфейсов относятся к следующему этапу.
- Windows/macOS и запуск контейнеров отмечаются проверенными только после реального прогона
  на соответствующей среде; настройки сами по себе этого не доказывают.
