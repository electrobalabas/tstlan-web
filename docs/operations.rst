Эксплуатация и разработка
=========================

Эта страница описывает путь от свежего клона репозитория до запущенного
локального проекта. Для первого запуска не нужны PostgreSQL, Docker и реальные
приборы: backend использует SQLite и встроенную симуляцию.

Требования
----------

Нужны четыре инструмента:

* Python >= 3.14.
* ``uv`` для установки Python-зависимостей и запуска backend.
* Node.js >= 20.
* ``pnpm`` для frontend.

Если Python 3.14 ещё не установлен, его можно поставить через ``uv``:

.. code-block:: shell

   uv python install 3.14

``pnpm`` удобнее включить через Corepack:

.. code-block:: shell

   corepack enable
   corepack prepare pnpm@latest --activate

Проверка окружения:

.. code-block:: shell

   uv --version
   python --version
   node --version
   pnpm --version

Быстрый старт
-------------

Все команды, кроме frontend-команд, выполняются из корня репозитория.

1. Создать локальную БД и администратора:

   .. code-block:: shell

      uv run python -m tstlan.tools.create_admin --login admin --password secret

   Команда сама применяет миграции Alembic и создаёт ``tstlan.db``.
   Отдельный ``make migrate`` перед ней не нужен.

2. Запустить backend в первом терминале:

   .. code-block:: shell

      uv run tstlan

   Backend слушает ``http://127.0.0.1:8000``.

   Проверка:

   .. code-block:: shell

      curl http://127.0.0.1:8000/health

   Ожидаемый ответ: ``{"status":"ok"}``.

3. Запустить frontend во втором терминале:

   .. code-block:: shell

      cd web/tstlan-web
      pnpm install
      pnpm dev

   Frontend слушает ``http://localhost:3000``.

4. Открыть ``http://localhost:3000`` и войти:

   * login: ``admin``
   * password: ``secret``

Как frontend находит backend
----------------------------

Браузер ходит на origin frontend. Next.js проксирует ``/api/*`` в backend,
поэтому cookie-сессии и CSRF работают без CORS.

По умолчанию frontend проксирует API на ``http://127.0.0.1:8000``. Если backend
запущен на другом порту:

.. code-block:: shell

   cd web/tstlan-web
   BACKEND_ORIGIN=http://127.0.0.1:9000 pnpm dev

PowerShell:

.. code-block:: powershell

   cd web/tstlan-web
   $env:BACKEND_ORIGIN = "http://127.0.0.1:9000"
   pnpm dev

Dev-приборы
-----------

Без ``config.dev.toml`` backend поднимает приборы in-process и запускает
``SimulationEngine``. Этого достаточно для первого запуска.

Чтобы проверить режим с отдельными TCP-процессами приборов, используйте
dev-эмуляторы:

.. code-block:: shell

   make device-multimeter
   make device-thermostat
   make dev-server

Что делают команды:

* ``make device-multimeter`` - запускает ``devsim`` с ``dev/multimeter.yaml`` на
  ``127.0.0.1:9001``.
* ``make device-thermostat`` - запускает ``devsim`` с ``dev/thermostat.yaml`` на
  ``127.0.0.1:9002``.
* ``make dev-server`` - запускает backend с ``config.dev.toml``. Этот конфиг
  подключает backend к двум TCP-эмуляторам.

Соединение с прибором ленивое: backend может стартовать до devsim, но чтение и
запись значений заработают только после запуска соответствующего процесса.

Тестовые данные
---------------

Для демо-данных поднимите backend и выполните:

.. code-block:: shell

   make seed

``make seed``:

* применяет миграции;
* создаёт пользователей напрямую в БД;
* создаёт конфиги через HTTP API уже запущенного backend.

Backend должен работать до запуска ``make seed``.

Тестовые пользователи:

* ``admin`` / ``admin123``
* ``engineer`` / ``engineer123``
* ``operator`` / ``operator123``
* ``viewer`` / ``viewer123``

Конфигурация
------------

Приоритет настроек:

``Settings`` defaults < ``config.toml`` < CLI-аргументы.

Основные поля:

* ``database_url`` - SQLite или PostgreSQL URL.
* ``allowed_origins`` - origins frontend для CSRF-проверок.
* ``cookie_secure`` - ``true`` для HTTPS-окружений.
* ``session_ttl_hours`` и ``session_refresh_hours`` - параметры скользящей
  сессии.
* ``devices`` - список TCP-приборов с ``id``, ``host``, ``port`` и ``profile``.

Минимальный ``config.toml``:

.. code-block:: toml

   bind_host = "127.0.0.1"
   bind_port = 8000
   database_url = "sqlite+aiosqlite:///./tstlan.db"
   allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

База данных и миграции
----------------------

По умолчанию используется SQLite-файл ``tstlan.db`` в корне репозитория.

Создать или обновить только схему, без пользователя:

.. code-block:: shell

   make migrate

Создать администратора и схему одной командой:

.. code-block:: shell

   uv run python -m tstlan.tools.create_admin --login admin --password secret

PostgreSQL подключается через ``--database-url`` или ``config.toml``:

.. code-block:: shell

   uv run tstlan --database-url postgresql+psycopg://user:password@host:5432/db

Тесты и проверки
----------------

Основной набор:

.. code-block:: shell

   make test
   make can-i-push

``make test`` запускает unit-тесты. По умолчанию pytest исключает маркеры
``integration`` и ``postgres``.

Локальные интеграционные тесты с TCP-эмулятором:

.. code-block:: shell

   make test-integration

PostgreSQL-тесты через Docker Compose:

.. code-block:: shell

   make test-postgres
   make postgres-down

Сборка документации:

.. code-block:: shell

   make docs-build
   make docs-open

Частые проблемы
---------------

``pnpm`` не найден
~~~~~~~~~~~~~~~~~~

.. code-block:: shell

   corepack enable
   corepack prepare pnpm@latest --activate

Порт backend занят
~~~~~~~~~~~~~~~~~~

Запустите backend на другом порту и укажите frontend новый ``BACKEND_ORIGIN``:

.. code-block:: shell

   uv run tstlan --port 9000

.. code-block:: shell

   cd web/tstlan-web
   BACKEND_ORIGIN=http://127.0.0.1:9000 pnpm dev

Нужно начать с чистой SQLite-базы
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Остановите backend, удалите ``tstlan.db`` и снова создайте администратора:

.. code-block:: shell

   uv run python -m tstlan.tools.create_admin --login admin --password secret

CSRF или login не работает через frontend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Проверьте, что:

* backend запущен;
* frontend проксирует API на правильный ``BACKEND_ORIGIN``;
* origin frontend есть в ``allowed_origins``;
* запросы идут через ``http://localhost:3000`` или
  ``http://127.0.0.1:3000``, а не через случайный hostname.
