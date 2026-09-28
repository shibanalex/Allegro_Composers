# Развёртывание

Сайт — один сервис Render (бесплатный тариф), собранный из `Dockerfile` по шаблону `render.yaml`.
Данные — PostgreSQL в Neon, файлы — Yandex Object Storage.

```
GitHub (main) ──push──► Render: сборка Dockerfile ──► контейнер: start.sh
                                                        ├─ alembic upgrade head
                                                        ├─ uvicorn allegro.main:app (127.0.0.1:8000)
                                                        └─ node (Nuxt) на $PORT
```

Каждый push в `main` пересобирает и перезапускает сайт; миграции применяются при старте.

## Переменные окружения (Render → Environment)

| Переменная | Значение |
|---|---|
| `SECRET_KEY` | генерирует Render (не менять: вход у всех сбросится, сохранённые адреса почты станут нечитаемыми) |
| `DATABASE_URL` | строка подключения Neon (`postgresql://…-pooler…/neondb?sslmode=require…`) |
| `STORAGE_BACKEND` | `s3` |
| `S3_ENDPOINT_URL` | `https://storage.yandexcloud.net` |
| `S3_REGION` | `ru-central1` |
| `S3_BUCKET` | имя бакета |
| `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | статический ключ сервисного аккаунта (роль `storage.editor`) |
| `MEDIA_URL_PREFIX` | `https://storage.yandexcloud.net/<бакет>` |
| `REGISTRATION_MODE` | `invite` (по приглашениям), `open` или `closed` |
| `SETUP_TOKEN` | код для `/setup` (нужен только для первого аккаунта свежей базы) |
| `NUXT_PUBLIC_SITE_URL` | свой домен, когда появится (`https://…`): канонические ссылки и переадресация |
| `NUXT_PUBLIC_YANDEX_VERIFICATION`, `NUXT_PUBLIC_GOOGLE_VERIFICATION` | коды подтверждения (если не файлом) |

Необязательные: `WRITE_REQUESTS_PER_MINUTE`, `SEARCH_REQUESTS_PER_MINUTE`, `MAX_UPLOAD_MB`,
`INVITE_TTL_DAYS`, `RESET_LINK_TTL_HOURS`, `EMAIL_ENCRYPTION_KEY`.

## Бакет Yandex Object Storage

- Доступ на чтение объектов — публичный; к списку объектов — ограниченный.
- CORS: `GET`, `HEAD`, заголовки `*`, источник — адрес сайта (или `*`).
- Биллинг: перейти на платную версию до конца пробного периода; бюджет с уведомлением.

## Приглашения и доступ

- Приглашения создаются на странице **Управление** (`/admin`), ссылка показывается один раз.
- Забытый пароль: там же «Сброс пароля» — одноразовая ссылка на 48 часов.
- Скрыть участника со всем опубликованным — «Скрыть» (ничего не удаляется).

## Свой домен

1. Купить домен (Reg.ru, RU-CENTER, Timeweb, Beget — российская карта).
2. Render → Settings → Custom Domains → добавить; вписать показанные записи DNS у регистратора.
3. `NUXT_PUBLIC_SITE_URL=https://домен` — старый адрес `…onrender.com` будет переадресовывать.
4. Заново подтвердить сайт в Яндекс.Вебмастере и Google Search Console, добавить `/sitemap.xml`.
5. Сузить CORS бакета до домена. Хороший момент перенести сервис в регион Frankfurt (docs/SCALING.md).

## Если что-то пошло не так

- **Deploy failed** — Render → Logs: последние строки. Частое: не задана переменная
  (приложение само назовёт какую), неверная строка базы.
- **Сайт открывается минуту** — он спал; см. «будильник» в SCALING.md.
- **Откат** — Render → Deploys → предыдущая успешная сборка → Rollback (база при этом не
  откатывается: миграции пишутся так, чтобы старый код их переживал, либо откат — через новую миграцию).
