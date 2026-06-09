Модули
======

Композиция приложения
---------------------

.. autofunction:: tstlan.app.create_app

Настройки и БД
--------------

.. autoclass:: tstlan.config.DeviceEndpoint
   :members:

.. autoclass:: tstlan.config.Settings
   :members:

.. autofunction:: tstlan.config.load_settings

.. autofunction:: tstlan.db.create_engine

.. autofunction:: tstlan.db.create_sessionmaker

.. autofunction:: tstlan.db.run_migrations

Аутентификация
--------------

.. autoclass:: tstlan.auth.models.User
   :members:

.. autoclass:: tstlan.auth.models.Session
   :members:

.. autoclass:: tstlan.auth.middleware.AuthCsrfMiddleware
   :members:

.. autofunction:: tstlan.auth.service.authenticate

.. autofunction:: tstlan.auth.service.create_session

.. autofunction:: tstlan.auth.service.resolve_session

Конфиги приборов
----------------

.. autoclass:: tstlan.configs.models.DeviceConfig
   :members:

.. autoclass:: tstlan.configs.models.ConfigShare
   :members:

.. autoclass:: tstlan.configs.schemas.ConnectionSettings
   :members:

.. autoclass:: tstlan.configs.schemas.ConfigVar
   :members:

.. autoclass:: tstlan.configs.schemas.ConfigPayload
   :members:

.. autoclass:: tstlan.configs.schemas.ConfigCreate
   :members:

.. autoclass:: tstlan.configs.schemas.ConfigUpdate
   :members:

.. autofunction:: tstlan.configs.schemas.variable_offsets

.. autofunction:: tstlan.configs.service.effective_access

.. autofunction:: tstlan.configs.service.list_configs

.. autofunction:: tstlan.configs.service.create_config

.. autofunction:: tstlan.configs.service.update_config

.. autofunction:: tstlan.configs.service.share_config

Приборы
-------

.. autoclass:: tstlan.models.NetVar
   :members:

.. autoclass:: tstlan.devices.models.Device
   :members:

.. autofunction:: tstlan.devices.models.coerce_value

.. autoclass:: tstlan.devices.device_profile.DeviceProfile
   :members:

.. autofunction:: tstlan.devices.device_profile.load_profile

.. autofunction:: tstlan.devices.device_profile.device_from_profile

.. autoclass:: tstlan.devices.service.DeviceService
   :members:

.. autoclass:: tstlan.devices.runtime.DeviceRuntime
   :members:

.. autofunction:: tstlan.devices.runtime.attach_device

.. autofunction:: tstlan.devices.runtime.bind_device

.. autoclass:: tstlan.devices.unidriver.io.UnidriverIO
   :members:

.. autoclass:: tstlan.devices.unidriver.io.InMemoryUnidriverIO
   :members:

.. autoclass:: tstlan.devices.unidriver.netvar.NetVarAccessor
   :members:

.. autofunction:: tstlan.devices.unidriver.netvar.build_scheme

.. autoclass:: tstlan.devices.net.client.LazySocketUnidriverIO
   :members:

Локальный runtime приборов
--------------------------

.. autoclass:: tstlan.devices.simulation.engine.SimulationEngine
   :members:

.. autoclass:: tstlan.devices.simulation.signals.Signal
   :members:

.. autoclass:: tstlan.devices.simulation.signals.Follow
   :members:

.. autofunction:: devsim.server.serve

.. autofunction:: devsim.signals.build_signal

Инструменты
-----------

.. autofunction:: tstlan.tools.ini2yaml.convert

.. autofunction:: tstlan.tools.ini2yaml.convert_file

.. autofunction:: tstlan.tools.ini2yaml.dump_yaml
