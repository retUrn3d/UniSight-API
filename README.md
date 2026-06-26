# unisight
Клиент для API UniSight.

Токен выпускается в [личном кабинете UniSight](https://app.unisight.ru/profile).

## Установка

[![PyPI](https://img.shields.io/pypi/v/unisight)](https://pypi.org/project/unisight/)

```bash
pip install unisight
```

Пакет на PyPI: [https://pypi.org/project/unisight/](https://pypi.org/project/unisight/). Python 3.9 и выше.

## Быстрый старт

```bash
pip install unisight
```

Синхронный клиент:

```python
from unisight import UniSightClient

with UniSightClient("us_xxxxxxxxxxxxxxxxxxxxxxxx") as api:
    me = api.me()
    orgs = api.orgs()
    org_id = orgs[0].id

    for v in api.vehicles(org_id):
        print(v.imei, v.display_name)
```

Асинхронный:

```python
import asyncio
from unisight import AsyncUniSightClient

async def main():
    async with AsyncUniSightClient("us_xxxxxxxxxxxxxxxxxxxxxxxx") as api:
        orgs = await api.orgs()
        track = await api.track(
            org_id=orgs[0].id,
            imei="123456789012345",
            dt_from="2026-06-01T00:00:00",
            dt_to="2026-06-02T00:00:00",
        )
        print(len(track), "точек")

asyncio.run(main())
```

## Авторизация

```python
api = UniSightClient("us_new_token", base_url="https://api.unisight.ru")
```

## Организации

`orgs()` возвращает список организаций в области токена. У токена организации это одна запись, у токена интегратора - весь портфель. `id` организации нужен как `org_id` в остальных вызовах.

Интегратор может создавать организации:

```python
org = api.create_org(
    name="ООО ТрансЛогистик",
    admin_login="translog_admin",
    admin_password="strong-password",
    timezone="Europe/Moscow",
)
```

## Пользователи

Для этих методов нужен scope `users`. Он выдаётся отдельно от `vehicles`, `reports` и `diagnostics`.

```python
users = api.users(org_id)
for u in users:
    print(u.user_id, u.username, u.role_template)

user = api.create_user(
    org_id=org_id,
    username="dispatcher_1",
    password="strong-password",
    display_name="Диспетчер",
    role_template="dispatcher",
)

api.block_user(org_id=org_id, user_id=user.user_id)
api.set_user_group(org_id=org_id, user_id=user.user_id, role_template="dispatcher")
```

`users` возвращает пользователей организации и их `user_id`. Этот идентификатор нужен для блокировки и смены группы.

`create_user` создаёт пользователя внутри организации и тоже возвращает `user_id`. Токен организации работает только со своей организацией. Токен интегратора может работать с организациями из своего портфеля.

`block_user` ставит `active=False`. Если нужно вернуть доступ, используйте `set_user_active(..., active=True)`.

`set_user_group` меняет группу пользователя: `admin`, `integrator`, `dispatcher` или `viewer`. Через публичный API нельзя выдать права `api.*`, включая право на выпуск API-токенов. Если выбрать группу, которая в кабинете обычно имеет такие права, сервер снимет их при применении группы через API.

## Техника

```python
api.create_vehicle(org_id=org_id, imei="123456789012345", label="А123АА77", display_name="Камаз 5490")
api.update_vehicle_name(org_id=org_id, imei="123456789012345", display_name="Камаз 5490Neo")
api.delete_vehicle(org_id=org_id, imei="123456789012345")
```

`update_vehicle_name` меняет отображаемое имя и госномер. IMEI и телеметрию он не трогает.

## Отчёты

Список показателей и шаблонов:

```python
catalog = api.report_tiles()
for t in catalog.tiles:
    print(t.key, t.label)
```

Генерация. Период передаётся как `datetime` или строка ISO 8601.

```python
report = api.create_report(
    org_id=org_id,
    imeis=["123456789012345"],
    tiles=["distance_km", "fuel_l"],
    dt_from="2026-06-01T00:00:00",
    dt_to="2026-06-02T00:00:00",
    format="json",
)
print(report.count, "строк")
for row in report.rows:
    print(row)
```

Для `format="xlsx"` возвращается `download_url`. Файл можно забрать сразу:

```python
job = api.create_report(..., format="xlsx")
downloaded = api.download_report(job.job_id)
open(downloaded.filename, "wb").write(downloaded.content)
```

Статус задачи отдельно:

```python
status = api.report_job(job.job_id)
print(status.status, status.finished_at)
```

## Диагностика и телеметрия

```python
for d in api.diagnostics(org_id):
    print(d.imei, d.health_score, "crit:", d.crit_count)

dash = api.dispatch(org_id)
print(dash["vehicle_count"], "ТС, активных:", dash["active_count"])

track = api.track(org_id=org_id, imei="123456789012345",
                  dt_from="2026-06-01T00:00:00", dt_to="2026-06-02T00:00:00")

raw = api.raw_telemetry(org_id=org_id, imei="123456789012345",
                        dt_from="2026-06-01T00:00:00", dt_to="2026-06-02T00:00:00",
                        limit=5000)
```

`track` отдаёт точки с координатами и подходит для карты. `raw_telemetry` отдаёт пакеты как есть: `adc`, `iobits`, `params`, включая точки без координат.

## Лимиты

| Запросы | Лимит |
|---------|-------|
| Все с одного IP | 2 в секунду, 100 в минуту |
| Генерация отчёта | 1 за 10 секунд |
| Диагностика и телеметрия | 10 в минуту |
| Неудачная авторизация | 1 за 3 секунды |

При превышении клиент бросает `RateLimitError`. В нём есть `retry_after` в секундах, если сервер прислал `Retry-After`.

## Ошибки

Все ошибки наследуются от `UniSightError`. Ответы API с кодом 4xx/5xx оборачиваются в подклассы:

| Класс | Когда |
|-------|-------|
| `UnauthorizedError` | 401, нет токена или токен отозван |
| `ForbiddenError` | 403, нет нужного scope |
| `NotFoundError` | 404, объекта нет или он вне области токена |
| `ConflictError` | 409, операция невозможна в текущем состоянии |
| `ValidationError` | 422, тело не прошло валидацию |
| `RateLimitError` | 429, превышен лимит |
| `UniSightAPIError` | прочие ответы API |

```python
from unisight import UniSightClient, NotFoundError, RateLimitError

try:
    api.vehicles(org_id=999)
except NotFoundError:
    print("организации нет или она недоступна")
except RateLimitError as e:
    print("подождите", e.retry_after, "секунд")
```

У любой `UniSightAPIError` есть `status_code`, `code`, `request_id` и `body`. `request_id` удобно прикладывать к обращению в поддержку.

## Лицензия

MIT
