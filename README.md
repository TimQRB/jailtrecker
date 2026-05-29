# jailtracker

Система электронного надзора за поднадзорными лицами (электронные браслеты, геозоны, инциденты). Веб-панель для администрации ИУ + бэкенд с поддержкой реальных трекеров HC02 через TCP-gateway.

Архитектурно — наследник учебного проекта SafeMektep, но переработанный под пенитенциарную специфику и с закрытыми известными уязвимостями SafeMektep (см. раздел «Что улучшено»).

> Статус: **этап 1** — реализованы бэкенд (REST + gateway-скелет) и веб админ-панель с ролью **администратора ИУ**. Роли надзирателя/инспектора УИИ и мобильное приложение — задел на будущее (заложены в модель данных, но UI/доступ пока не активированы).

## Быстрый старт

```bash
cp .env.example .env   # и поменяйте секреты
docker compose up --build
```

| Сервис | Порт | Назначение |
|---|---|---|
| Frontend (React/Vite + nginx) | `5173` | http://localhost:5173 |
| Backend (FastAPI) | `8080` → 8000 | http://localhost:8080/docs |
| TCP Gateway (HC02) | `13000`, `13001` | приём трекеров |
| PostgreSQL + PostGIS | внутренний | БД (наружу не проброшена) |
| Redis | внутренний | Pub/Sub + durable-очередь команд |

При старте backend накатывает миграции Alembic и сидирует демо-админа.

## Демо-доступ

| Роль | Email | Пароль |
|---|---|---|
| Администрация ИУ | `admin@jailtracker.kz` | `admin123` |

> Сменить через `ADMIN_EMAIL` / `ADMIN_PASSWORD` в `.env` перед любым реальным запуском.

## Стек

| Слой | Технология |
|---|---|
| Backend | Python 3.12 + FastAPI + asyncio TCP Gateway |
| БД | PostgreSQL 16 + PostGIS 3.4 (миграции Alembic) |
| Pub/Sub | Redis 7 (AOF включён) |
| Frontend | React 18 + TypeScript + Vite + Leaflet (подложка MapTiler vector через maplibre-gl, фолбэк OSM) |
| Устройства | HC02 (TCP, бинарный протокол) + HTTP-ingest для симулятора |

## Сценарии надзора

Модель данных универсальна и держит три сценария одновременно; конкретика задаётся типом дела (`case.supervision_type`) и типами геозон:

- **Домашний арест** — зоны `home`/`work`, комендантский час через `schedules` (`must_be_inside`), алерт при выходе/нарушении графика.
- **Внутри ИУ** — зоны `perimeter` (алерт при выходе) и `forbidden` (алерт при входе).
- **Конвоирование** — маршрутный коридор `route_corridor` (алерт при отклонении).

## Структура

```
jailtrecker/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── alembic/                 # миграции (0001_initial — вся схема + PostGIS)
│   ├── app/
│   │   ├── main.py              # FastAPI: lifespan, CORS (белый список), роутеры
│   │   ├── config.py            # настройки из env
│   │   ├── database.py          # engine + сессии
│   │   ├── models.py            # ORM: users, inmates, cases, devices, geofences,
│   │   │                        #      schedules, location_points, device_zone_states,
│   │   │                        #      incidents, audit_logs
│   │   ├── schemas.py           # Pydantic
│   │   ├── security.py          # JWT + bcrypt + require_roles
│   │   ├── audit.py             # запись аудит-лога
│   │   ├── bus.py               # Redis Pub/Sub (jailtracker:events)
│   │   ├── device_commands.py   # команды + durable-очередь для offline
│   │   ├── geofence_service.py  # PostGIS ST_Covers + enter/exit + инциденты
│   │   ├── schedule_service.py  # комендантский час
│   │   ├── init_db.py           # сид админа (схему накатывает Alembic)
│   │   └── routers/             # auth, users, inmates, cases, devices, geofences,
│   │                            # schedules, locations, incidents, audit, health, ws
│   └── gateway/                 # asyncio TCP listeners + протокол HC02 (скелет)
├── frontend/
│   └── src/
│       ├── api.ts               # типы DTO + fetch-обёртки
│       ├── auth.tsx             # JWT-контекст
│       ├── useLiveBus.ts        # WebSocket (токен НЕ в URL)
│       ├── components/MapView.tsx
│       └── pages/
│           ├── Login.tsx
│           ├── Dashboard.tsx    # карта + поднадзорные + инциденты (live)
│           └── admin/           # Admin.tsx + 8 вкладок (декомпозировано)
└── simulator/simulate.py        # HTTP-симулятор браслета (локации, tamper, батарея)
```

## Сущности БД

```
users(id, email, password_hash, full_name, role, is_active)
inmates(id, full_name, inmate_number UNIQUE, date_of_birth, supervisor_id → users)
cases(id, inmate_id → inmates, case_number UNIQUE, article, supervision_type, status, start/end_date)
devices(id, identifier, imei UNIQUE, inmate_id, api_key, last_seen_at, last_battery, tamper_state)
geofences(id, name, zone_type, polygon GEOMETRY(POLYGON,4326), inmate_id NULL, case_id NULL)
schedules(id, inmate_id, geofence_id, rule, day_of_week, start_time, end_time)
location_points(id, device_id, lat, lon, accuracy, speed, battery, source, recorded_at)
device_zone_states(id, device_id, geofence_id, is_inside, updated_at)
incidents(id, inmate_id, device_id, incident_type, severity, geofence_id, message, lat, lon, acknowledged)
audit_logs(id, user_id, user_email, action, entity_type, entity_id, detail, ip, user_agent, created_at)
```

Миграции — **Alembic** (`alembic upgrade head`), без `create_all`.

## REST API

Swagger: http://localhost:8080/docs

- `/api/auth/*` — login, `/me`
- `/api/users` — CRUD пользователей (admin)
- `/api/inmates` — CRUD поднадзорных
- `/api/cases` — CRUD дел
- `/api/devices` — CRUD браслетов, `/assign/{inmate_id}`, `/locate-now`
- `/api/geofences` — CRUD геозон (POLYGON)
- `/api/schedules` — CRUD расписаний/комендантского часа
- `/api/ingest/location` — POST с `X-API-Key` (симулятор/источник), rate-limited
- `/api/inmates/{id}/track`, `/last-location` — треки
- `/api/incidents` — лента + `/ack`
- `/api/audit` — просмотр аудит-лога (admin)
- `/api/health` — health-check
- `/ws` — WebSocket real-time (аутентификация первым сообщением, не в query)

## Логика инцидентов

На каждой точке (`/api/ingest/location` и далее gateway) пересчитывается:
- **геозоны** — `ST_Covers`, переходы enter/exit фиксируются в `device_zone_states`; выход из `home`/`perimeter`/`route_corridor` и вход в `forbidden` → критический инцидент;
- **комендантский час** — если действует правило `must_be_inside`, а точка вне зоны → `curfew_violation`;
- **tamper** — `strap_cut`/`opened` от устройства → критический инцидент;
- **низкий заряд** — ≤15% → предупреждение.

Все инциденты публикуются в Redis `jailtracker:events` и долетают до веб-панели по WebSocket.

## Что улучшено относительно SafeMektep

| Известная проблема SafeMektep | Решение в jailtracker |
|---|---|
| #4 нет миграций | Alembic, схема в `0001_initial`, `create_all` убран |
| #7 CORS `*` | Белый список origin'ов из `CORS_ORIGINS` |
| #5 JWT в query при WS | Токен передаётся первым WS-сообщением `{type:auth}` |
| #6 нет rate-limit на ingest | Redis sliding-counter на `X-API-Key` |
| #2 потеря offline-команд | Durable-очередь `dev_cmd_queue:<IMEI>` + Redis AOF |
| #9 нет аудита доступа | Таблица `audit_logs` + запись на всех мутациях и логине |
| БД проброшена наружу | Порт Postgres наружу не публикуется |

## Запуск без Docker (dev)

Backend:
```bash
cd backend
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://jailtracker:jailtracker@localhost:5432/jailtracker
export REDIS_URL=redis://localhost:6379/0
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Frontend:
```bash
cd frontend
npm install
npm run dev   # http://localhost:5173, проксирует /api и /ws на :8080
```

Симулятор (API-key возьмите из вкладки «Браслеты» после создания устройства):
```bash
cd simulator
pip install -r requirements.txt
python simulate.py --api-key <API_KEY> --imei 860000000000001
```

## Дорожная карта

- [ ] Роли надзирателя и инспектора УИИ (RBAC уже заложен в `require_roles`)
- [x] Интерактивный редактор геозон на карте (leaflet-geoman: рисование/правка/удаление)
- [ ] Перетаскиваемые маркеры для ручной корректировки GPS-позиции
- [ ] Полный разбор бинарного протокола HC02 в gateway (сейчас — скелет кадра)
- [ ] Детектор `device_offline` по `last_seen_at` (фоновая задача)
- [ ] Интеграция с УИС, экспорт отчётов
```
