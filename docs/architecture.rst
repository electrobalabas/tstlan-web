Архитектура
===========

Слои
----

:mod:`tstlan.app` собирает приложение: настройки, SQLAlchemy engine/sessionmaker,
middleware, роутеры и runtime приборов. Это единственная точка композиции.

:mod:`tstlan.auth` отвечает за пользователей, сессии и CSRF. Сессия хранится в БД,
в браузере лежит только ``HttpOnly`` cookie. CSRF проверяется middleware на
изменяющих запросах.

:mod:`tstlan.configs` хранит пользовательские конфиги приборов. Сервисный слой
считает эффективный доступ через :func:`tstlan.configs.service.effective_access`.
``PUBLIC`` - управляемое состояние, ``PRIVATE``/``SHARED`` нормализуются по
наличию грантов.

:mod:`tstlan.devices` описывает приборы и переменные, строит layout переменных в
буфере, читает и пишет значения через :class:`tstlan.devices.unidriver.io.UnidriverIO`.
API не знает, где физически живёт прибор.

:mod:`devsim` - отдельный TCP-процесс прибора для локальной отладки. Он
использует тот же in-memory буфер и тот же runtime обновления значений, поэтому
dev-сценарий близок к будущей сетевой интеграции.

``web/tstlan-web`` держит клиентский контракт: TypeScript-типы зеркалят Pydantic
схемы, а Next.js проксирует ``/api/*`` на FastAPI. Браузер остаётся на одном
origin, поэтому cookie-сессии и CSRF не требуют CORS.

Контракт ввода-вывода приборов
------------------------------

Ключевое архитектурное решение - протокол
:class:`tstlan.devices.unidriver.io.UnidriverIO`. Он задаёт минимальные операции:
читать/писать байты, читать/писать бит, проверить подключение и сделать ``tick``.

Реализации:

* :class:`tstlan.devices.unidriver.io.InMemoryUnidriverIO` - байтовые буферы в
  памяти для локального режима и тестов.
* :class:`tstlan.devices.net.client.LazySocketUnidriverIO` - клиент к
  :mod:`devsim`. Соединяется при первом обращении, поэтому процесс-прибор можно
  запустить позже сервера. При обрыве сбрасывает соединение и повторяет
  операцию один раз на новом соединении.
* транспорты реальных приборов - MxNet, Modbus, USB HID, нативно или поверх
  ``libunidriver.so`` - должны реализовать тот же контракт, не меняя
  :class:`tstlan.devices.service.DeviceService` и роуты.

Размещение переменных
---------------------

:func:`tstlan.devices.unidriver.netvar.build_scheme` превращает список
:class:`tstlan.models.NetVar` в набор
:class:`tstlan.devices.unidriver.netvar.NetVarAccessor`. Адреса выводятся из
порядка переменных и C-типа. Числа кодируются little-endian, ``BIT`` занимает
отдельный бит внутри байта.

Это решение делает YAML-профиль прибора источником layout: если меняется порядок
или типы переменных, меняются адреса в буфере. Поэтому профили нужно версионировать
и не править порядок переменных без миграции связанных конфигов.

Потоки данных
-------------

Чтение значений: ``GET /devices/{id}/values`` ->
:class:`tstlan.devices.service.DeviceService` ->
:meth:`tstlan.devices.unidriver.netvar.NetVarAccessor.get` ->
:class:`tstlan.devices.unidriver.io.UnidriverIO`.

Запись значения: ``PUT /devices/{id}/values/{name}`` -> проверка mode ->
приведение типа -> :meth:`tstlan.devices.unidriver.netvar.NetVarAccessor.set`.

Streaming: ``GET /devices/{id}/stream`` отдаёт Server-Sent Events раз в секунду.
Заголовки ``Cache-Control: no-cache, no-transform`` и ``X-Accel-Buffering: no``
нужны, чтобы dev-proxy или nginx не сжимали и не буферизовали поток - иначе
``EventSource`` в браузере не получает события.

Локальный runtime приборов
--------------------------

:class:`tstlan.devices.simulation.engine.SimulationEngine` нужен для локального
запуска без реального оборудования. На каждом тике он сначала считывает из буфера
все переменные, которые не являются read-only: так команды и настройки, записанные
бэкендом, попадают в состояние прибора. Затем engine сэмплирует сигналы сенсоров
и публикует новые значения обратно в буфер.

Сигналы строятся как маленький Composite: ``sine``, ``square``, ``ramp``,
``noise`` и другие источники можно складывать через ``plus``.
:class:`tstlan.devices.simulation.signals.Follow` повторяет текущее значение
другой переменной, поэтому RW-переменная может управлять сгенерированным
сенсором.

:mod:`devsim` оборачивает тот же буфер в TCP-сервер. Вокруг обработки запроса и
тика runtime стоит lock: клиент не видит частично обновлённое состояние.

База данных
-----------

Alembic - источник истины для схемы. Приложение не создаёт таблицы на старте.
SQLite используется по умолчанию, PostgreSQL включается через ``database_url``.
Для SQLite явно включены foreign keys.

Конвертация старых конфигов
---------------------------

:mod:`tstlan.tools.ini2yaml` читает legacy ``.ini`` в ``cp1251`` и собирает YAML,
совместимый с :class:`tstlan.configs.schemas.ConfigCreate`. Транспорт определяется
по строке ``device.type``. Переменные берутся из секции ``vars`` в порядке
``name_N``; номер ``N`` нужен только для сортировки, адрес всё равно выводится
через :func:`tstlan.configs.schemas.variable_offsets`.
