HTTP API
========

Health
------

``GET /health``
   healthcheck

Auth
----

``POST /auth/login``
   Принимает ``login`` и ``password``, создаёт серверную сессию, ставит cookie и
   возвращает пользователя с ``csrf_token``.

``POST /auth/logout``
   Отзывает текущую сессию. Требует ``X-CSRF-Token``.

``GET /auth/me``
   Возвращает текущего пользователя и CSRF-токен.

Devices
-------

``GET /devices``
   Список приборов и краткое описание переменных.

``GET /devices/{device_id}``
   Детальная карточка прибора.

``GET /devices/{device_id}/values``
   Снимок всех читаемых переменных. Переменные mode ``W`` не возвращаются.

``GET /devices/{device_id}/values/{name}``
   Значение одной переменной. Для write-only переменной вернётся ``403``.

``PUT /devices/{device_id}/values/{name}``
   Запись значения. Read-only переменная вернёт ``403``; неверный тип - ``422``.

``GET /devices/{device_id}/stream``
   SSE-поток снимков значений. Используется фронтендом для мониторинга.

Configs
-------

``GET /configs``
   Список доступных пользователю конфигов с вычисленным доступом.

``POST /configs``
   Создание конфига. Публиковать ``PUBLIC`` могут только ``DEV`` и ``ADMIN``.

``GET /configs/{config_id}``
   Детальный конфиг.

``PUT /configs/{config_id}``
   Обновление. ``OWNER`` управляет метаданными и видимостью, ``WRITE`` может
   менять payload.

``DELETE /configs/{config_id}``
   Удаление, только владелец или admin через effective owner-доступ.

``POST /configs/{config_id}/shares``
   Выдать или обновить доступ другому пользователю.

``DELETE /configs/{config_id}/shares/{login}``
   Отозвать share.

Ошибки доступа
--------------

Сервисные исключения мапятся в HTTP-коды:

* ``404`` - прибор, переменная, конфиг или пользователь-грант не найдены.
* ``403`` - нет прав, нельзя читать/write-only или писать/read-only.
* ``422`` - некорректное значение или попытка поделиться с владельцем.
