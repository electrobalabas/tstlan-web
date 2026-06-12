Эксплуатация и разработка
=========================

Требования
----------

* Python >= 3.14.
* ``uv`` для Python-команд.
* Node.js >= 20 и ``pnpm`` для фронтенда.

Быстрый старт
-------------

Создать БД и администратора:

.. code-block:: shell

   uv run python -m tstlan.tools.create_admin --login admin --password secret

Команда сама применяет миграции, отдельный ``make migrate`` перед ней не нужен.

Запустить бэкенд:

.. code-block:: shell

   uv run tstlan

Запустить фронтенд:

.. code-block:: shell

   cd web/tstlan-web
   pnpm install
   pnpm dev

Фронтенд доступен на ``http://localhost:3000``. Next.js проксирует ``/api/*`` на
``BACKEND_ORIGIN``; по умолчанию это ``http://127.0.0.1:8000``.

Dev-приборы
-----------

В отдельных терминалах:

.. code-block:: shell

   make device-multimeter   # devsim с dev/multimeter.yaml на порту 9001
   make device-thermostat   # devsim с dev/thermostat.yaml на порту 9002
   make dev-server          # бэкенд с config.dev.toml
   make seed                # тестовые пользователи и конфиги

``config.dev.toml`` подключает бэкенд к TCP-эмуляторам. Если ``devices`` пустой,
бэкенд поднимает приборы in-process и запускает
:class:`tstlan.devices.simulation.engine.SimulationEngine`.

``make seed`` создаёт пользователей ``admin``/``admin123`` с ролью ``admin`` и
``engineer``/``engineer123`` с ролью ``dev``, а затем наполняет конфиги через
HTTP API - тем же путём, которым ходит браузер, так что сид заодно проверяет
аутентификацию и CSRF.

Профиль прибора - YAML с именем, типом, переменными и опциональными сигналами.
Если у переменной есть ``signal`` и не указан ``mode``, она считается read-only.
Без ``signal`` и без ``mode`` переменная считается ``rw``.

Конфигурация
------------

Приоритет настроек: дефолты < ``config.toml`` < аргументы CLI.

Важные поля:

* ``database_url`` - SQLite или PostgreSQL URL.
* ``allowed_origins`` - origin фронтенда для CSRF.
* ``cookie_secure`` - должен быть ``true`` за HTTPS.
* ``session_ttl_hours`` и ``session_refresh_hours`` - скользящая сессия.
* ``devices`` - список TCP-приборов с ``id``, ``host``, ``port`` и ``profile``.

Миграции и тесты
----------------

.. code-block:: shell

   make migrate
   make test
   make test-integration
   make can-i-push

``make test`` гоняет только юнит-тесты: дефолтные опции pytest исключают маркер
``integration``. Так же работает CI.

``make test-integration`` запускает интеграционные тесты: каждый тест поднимает
:mod:`devsim` отдельным процессом и проверяет обмен через настоящий TCP-сокет на
loopback. Им не нужно ни оборудование, ни Docker - они работают на любой машине
разработчика, но исключены из CI, потому что зависят от реальных сокетов и
таймингов.

Конвертер legacy INI:

.. code-block:: shell

   uv run python -m tstlan.tools.ini2yaml old.ini -o config.yaml

Документация
------------

Исходники лежат в ``docs/``. HTML-артефакт собирается в ``build/docs``:

.. code-block:: shell

   make docs-build
   make docs-open

``docs-open`` сначала пересобирает документацию, затем открывает
``build/docs/index.html`` через стандартный модуль ``webbrowser``.
