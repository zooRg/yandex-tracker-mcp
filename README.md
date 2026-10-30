# Yandex Tracker MCP — форк qtim

Форк [aikts/yandex-tracker-mcp](https://github.com/aikts/yandex-tracker-mcp) (база — апстрим 0.10.0) с загрузкой локальных файлов в задачи и комментарии, скачиванием вложений и просмотром картинок прямо в ответе модели. Ставится как плагин Claude Code из этого репозитория.

Полная документация по инструментам, переменным окружения, Docker и HTTP-транспорту — в апстриме: [README](https://github.com/aikts/yandex-tracker-mcp#readme) / [README_ru](https://github.com/aikts/yandex-tracker-mcp/blob/main/README_ru.md).

## Установка в Claude Code

Нужны Claude Code и [uv](https://docs.astral.sh/uv/) в `PATH`.

```bash
claude plugin marketplace add https://github.com/zooRg/yandex-tracker-mcp.git
claude plugin install yandex-tracker-mcp@qtim-yandex-tracker
```

Затем в сессии Claude Code:

```
/plugin configure yandex-tracker-mcp@qtim-yandex-tracker
/reload-plugins
```

`configure` спрашивает три поля:

| Поле | Что вводить |
|---|---|
| Yandex Tracker OAuth Token | OAuth-токен Трекера. Хранится в системном Keychain, в `settings.json` не попадает |
| Tracker Cloud Org Id | ID организации Yandex Cloud (`X-Cloud-Org-ID`) |
| Tracker Org Id | ID организации Яндекс 360 (`X-Org-ID`) |

Заполняется ровно один из двух org id, второй остаётся пустым.

Первый запуск сервера делает `uv sync` в каталоге плагина — 10–20 секунд.

Обновление после новых коммитов в этом репозитории: `/plugin` → Update (или `claude plugin update yandex-tracker-mcp@qtim-yandex-tracker`).

## Что добавлено

`issue_get_attachment_content(issue_id, attachment_id)` — id вложения берётся из `issue_get_attachments`.

- png / jpeg / gif / webp до 5 МБ возвращаются изображением (`ImageContent`): модель видит картинку в ответе инструмента;
- остальные файлы и картинки крупнее сохраняются в `<tmp>/yandex-tracker-mcp/<KEY>-<id>-<name>`, возвращается путь.

В апстриме есть только метаданные вложений (`issue_get_attachments`).

| Инструмент | Назначение | Основные аргументы |
|---|---|---|
| `issue_get_attachment_content` | Скачать вложение или показать изображение | `issue_id`, `attachment_id` |
| `issue_add_attachment` | Загрузить локальный файл, получить ID и метаданные | `issue_id`, `file_path`, `temporary` |
| `issue_add_comment` | Создать комментарий с вложениями | `issue_id`, `text`, `attachment_ids` |
| `issue_update_comment` | Добавить вложения в существующий комментарий | `issue_id`, `comment_id`, `text`, `attachment_ids` |

Загрузка локальных файлов доступна только при `TRANSPORT=stdio`: `file_path` — абсолютный путь к обычному файлу на машине MCP-сервера. HTTP/SSE-вызовы отклоняются до чтения файла. Действуют `TRACKER_READ_ONLY`, `TRACKER_READ_ONLY_QUEUES` и `TRACKER_LIMIT_QUEUES`. Файлы передаются потоково; ошибки доступа, ограничения размера и таймаут API возвращаются вызывающему клиенту (`TRACKER_API_TIMEOUT`, по умолчанию 10 секунд).

Чтобы прикрепить файл к задаче, вызовите `issue_add_attachment(issue_id="TEST-1", file_path="/absolute/report.pdf")`.

Чтобы прикрепить файлы к комментарию:

1. Для каждого файла вызовите `issue_add_attachment(issue_id="TEST-1", file_path="/absolute/report.pdf", temporary=true)`.
2. Передайте полученные `id` в `attachment_ids` инструмента `issue_add_comment` или `issue_update_comment` той же задачи. Для редактирования сначала прочитайте текущий текст через `issue_get_comments` и передайте его без изменений, если нужно только добавить файлы.
3. Проверьте результат через `issue_get_attachments`: файлы комментария также видны во вложениях задачи, а их `commentId` совпадает с `longId` комментария из `issue_get_comments` (в селекторе `fields` используйте `comment_id`).

Временный файл ещё не прикреплён к задаче; его ID можно использовать только один раз. `attachment_ids` добавляет файлы, а пропуск параметра сохраняет существующие вложения. Загрузка и публикация комментария — отдельные операции: при ошибке публикации проверьте состояние перед повтором, чтобы избежать дубликатов. Если включён Redis-кэш, повторные чтения могут отставать на его TTL.

Контракт API: [загрузка в задачу](https://yandex.ru/support/tracker/en/api/issues/post-attachment), [временные файлы](https://yandex.ru/support/tracker/ru/api/issues/temp-attachment), [редактирование комментария](https://yandex.ru/support/tracker/en/api/issues/edit-comment).

Инструменты вложений находятся в `mcp_tracker/mcp/tools/issue_read.py` и `issue_write.py`; HTTP-методы, протокол и обёртка кэша — в `mcp_tracker/tracker/`.

## Устройство плагина

- `.claude-plugin/marketplace.json` — репозиторий сам является marketplace `qtim-yandex-tracker`;
- `.claude-plugin/plugin.json` — манифест плагина, версия и `userConfig` (токен помечен `sensitive`);
- `.mcp.json` — запуск сервера: `uv run --directory ${CLAUDE_PLUGIN_ROOT} yandex-tracker-mcp`, значения `userConfig` уходят в `TRACKER_*` env.

## Синхронизация с апстримом

```bash
git remote add upstream https://github.com/aikts/yandex-tracker-mcp.git
git fetch upstream
git merge upstream/main
```

При синхронизации проверьте инструменты вложений, комментариев и их протокольные методы. После мержа — поднять `version` в `.claude-plugin/plugin.json` и записать изменения в `CHANGELOG.md`.

## Запуск без плагина

Тот же сервер через uvx, в любом MCP-клиенте:

```bash
uvx --from git+https://github.com/zooRg/yandex-tracker-mcp yandex-tracker-mcp
```

Переменные окружения: `TRACKER_TOKEN` и один из `TRACKER_CLOUD_ORG_ID` / `TRACKER_ORG_ID`. Остальные (лимиты очередей, read-only, кэш, транспорт) описаны в апстриме.
