# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Что это за репозиторий

Учебный Django-проект: **сервис управления рассылками, администрирования и получения
статистики**. `origin` — https://github.com/Jd4rc/project_4.git, ветка `main`.

## Рабочие файлы

- `SPEC.md` — текст ТЗ и разбор на требования `R1…R19`. Источник истины: спорный вопрос
  решается по нему, а не по памяти. В конце файла перечислено, **чего в ТЗ нет**
  (ролей, планировщика, блога, кэша, требований к БД) — этого не делаем.
- `TODO.md` — только оставшееся: блоки 0б, 1 и 7, у каждой задачи проверка и имя коммита. Пометки: ⛔ блокирует · ⚠️ потом дорого · ❓ вопрос куратору.
- `MADE.md` — журнал сделанного, новые записи сверху, в конце каждой блок **Знать:**.

Закончил кусок — перенеси его из `TODO.md` в `MADE.md` в том же заходе.

## Состояние

**Все 19 требований ТЗ закрыты**, 32 теста зелёные. Работают: CRUD получателей, сообщений
и рассылок, статусы с фоновым закрытием, отправка кнопкой и командой, попытки в две ступени,
статистика и главная. Не сделано (не по ТЗ): перевод на PostgreSQL (блок 0б), вход и
регистрация (блок 1, отложено владельцем — `owner` у моделей есть, но пустой) и сдача.

## Команды

Окружение poetry не активировано в оболочке — всё через `poetry run`:

```bash
poetry run python manage.py check                   # быстрая проверка без БД
poetry run python manage.py makemigrations
poetry run python manage.py migrate
poetry run python manage.py createsuperuser
poetry run python manage.py runserver
poetry run python manage.py test                    # все тесты
poetry run python manage.py test mailings           # тесты приложения
poetry run python manage.py test mailings.tests.SendMailingTests.test_failure_does_not_stop_the_rest   # один тест
poetry run python manage.py send_mailing 3          # отправить рассылку №3 (без номера — все, кому пора)
poetry run python manage.py update_mailing_statuses # закрыть просроченные (вешается на планировщик ОС)
```

⚠️ **Установка пакетов из сессии не работает.** `poetry add ...` падает с «All attempts to
connect to pypi.org failed», хотя настоящая причина — `Permission denied` на кэш poetry
в `AppData` (песочница не пускает за пределы проекта). Ставить нужно в обычном окне
PowerShell: `cd C:\Users\dosed\PycharmProjects\project_4; poetry add <пакет>`.

## Архитектура

- `config/` — проект в корне репозитория: `settings.py`, `urls.py`, wsgi/asgi.
  Маршруты приложений подключаются через `include` с `namespace`.
- `mailings/` — предметная область целиком: модели `Client`, `Message`, `Mailing`,
  `MailingAttempt`; CBV во `views.py`, формы в `forms.py` (общий `StyleFormMixin`).
  Логика вне вьюх: `services.py` — `send_mailing()`, единственный вход отправки для кнопки
  и команды; `statistics.py` — агрегаты для главной и отчёта. Команды — в `management/commands/`.
- `users/` — `User(AbstractUser)`, пока без единого своего поля.
- `templates/` — общий `base.html` (Bootstrap 5 с CDN) и `includes/nav.html`;
  шаблоны приложений лежат у себя: `mailings/templates/mailings/…`.
- Настройки читаются из `.env` (`load_dotenv` в `settings.py`), шаблон — `.env.example`.
  Секретов в коде нет и быть не должно.

Вьюхи — **class-based**. У `ListView(model=X)` и `DetailView` имена шаблонов выводятся
автоматически (`x_list.html`, `x_detail.html`); переименовал шаблон — проверь связку.

## Грабли, которые уже стоили времени

- **Почта в Django 6 — это `MAILERS`**, `EMAIL_*` устарели и **не могут** объявляться рядом:
  `ImproperlyConfigured`. Поэтому хост из `.env` читается в `_email_host` (нижний регистр
  Django настройкой не считает). Есть `EMAIL_HOST` — SMTP с `timeout`, нет — письма в терминал.
  Тестовый раннер сам подменяет `MAILERS` на `locmem`: `mail.outbox` работает без `override_settings`.
- **`{% url %}` на несуществующий маршрут роняет всю страницу** (`NoReverseMatch`):
  ссылку в `nav.html` добавляй в том же изменении, что и маршрут, а не заранее.
- **Статистика считается по письмам** (`MailingAttempt.objects.letters()`), не по всем
  попыткам, и после `finish_expired()`. Второй JOIN в `mailing_report()` размножит строки.
- **Допущение по Q4:** «уникальный получатель» = клиент, состоящий хотя бы в одной рассылке;
  куратор не подтвердил. Меняется в одной строке `home_stats()`.
- **БД — PostgreSQL** (решение по Q5). ⚠️ В коде пока `sqlite3`: переключение вынесено
  отдельной задачей — блок «0б» в `TODO.md`. Параметры подключения пойдут из `.env`,
  в `settings.py` ни имени базы, ни пароля. Пользователю PostgreSQL нужно право
  `CREATEDB`, иначе `manage.py test` упадёт до первого теста.
- **`AUTH_USER_MODEL` после первой миграции не меняется.** Уже зафиксирован — не трогать.
- **FK на пользователя — только `settings.AUTH_USER_MODEL`.** Прямой импорт
  `django.contrib.auth.models.User` при своей модели пользователя — ошибка системных
  проверок. У `Client`, `Message` и `Mailing` есть `owner` (`null=True`, пока пустой):
  заполнится, когда появится вход.
- **Попытки рассылки — две ступени** (решение по Q2, `SPEC.md`): одна запись на запуск
  с пустым `client` и по записи на каждое письмо с `client` и `parent`. Считая статистику,
  фильтруй по заполненному `client`, иначе записи о запусках задвоят цифры.
- **Статус «Завершена» ставит фоновая задача** (решение по Q3): метод
  `Mailing.objects.finish_expired()` + команда `manage.py update_mailing_statuses`
  на планировщике ОС. Между её запусками хранимый статус врёт, поэтому тот же метод
  зовётся перед подсчётом статистики и перед отправкой.
- При `USE_TZ = True` сравнивай время через `django.utils.timezone.now()` —
  голый `datetime.now()` наивный, сравнение с aware-полем падает.

## Ветки

Флоу: `main` — только сдаваемые состояния, `develop` — интеграционная ветка,
`feature/<имя>` — один блок `TODO.md` = одна ветка, ответвляется от `develop`
и вливается обратно в `develop` через `--no-ff`.

| Ветка | Блок `TODO.md` |
|---|---|
| `feature/auth` | 1. Вход и регистрация (отложено) |
| `feature/clients` | 2. Получатели — R1, R2 |
| `feature/messages` | 3. Сообщения — R3, R4 |
| `feature/mailings` | 4. Рассылки — R5–R7 |
| `feature/sending` | 5. Отправка и попытки — R8–R15 |
| `feature/statistics` | 6. Статистика и главная — R16–R19 |

⚠️ База и `.env` вне git: после смены ветки прогоняй `migrate`, а новые ключи в `.env`
дописывай руками — ветка их не принесёт. Две feature-ветки одновременно легко дают
конфликт номеров миграций, поэтому по одной за раз.

## Git-гигиена

⛔ **Коммиты делает владелец.** Claude не запускает `add`, `commit`, `push` и прочие
изменяющие git-команды — он выдаёт готовые команды и сообщения коммитов текстом.
`git status`, `git diff`, `git log` — можно.

`.idea/`, `.env`, `db.sqlite3`, `__pycache__` игнорируются. Правил для `media/` и
`staticfiles/` в `.gitignore` **нет** — появится загрузка файлов или `collectstatic`,
добавь сам.
