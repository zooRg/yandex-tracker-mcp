# Yandex Tracker MCP — форк qtim

Форк [aikts/yandex-tracker-mcp](https://github.com/aikts/yandex-tracker-mcp) (база — апстрим 0.10.0) с одним отличием: инструмент `issue_get_attachment_content`, который скачивает вложения задачи и отдаёт картинки прямо в ответ модели. Ставится как плагин Claude Code из этого репозитория.

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

Правки относительно апстрима: `mcp_tracker/mcp/tools/issue_read.py` (инструмент), `mcp_tracker/tracker/proto/issues.py`, `mcp_tracker/tracker/custom/client.py`, `mcp_tracker/tracker/caching/client.py` (метод `issue_download_attachment`).

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

Конфликты возможны только в четырёх файлах из раздела «Что добавлено». После мержа — поднять `version` в `.claude-plugin/plugin.json` и записать изменения в `CHANGELOG.md`.

## Запуск без плагина

Тот же сервер через uvx, в любом MCP-клиенте:

```bash
uvx --from git+https://github.com/zooRg/yandex-tracker-mcp yandex-tracker-mcp
```

Переменные окружения: `TRACKER_TOKEN` и один из `TRACKER_CLOUD_ORG_ID` / `TRACKER_ORG_ID`. Остальные (лимиты очередей, read-only, кэш, транспорт) описаны в апстриме.
