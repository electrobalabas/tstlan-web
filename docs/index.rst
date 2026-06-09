TSTLAN web platform
===================

TSTLAN - веб-платформа мониторинга измерительных приборов. Браузер работает с
Next.js, фронтенд проксирует ``/api/*`` в FastAPI, а бэкенд читает и пишет
переменные приборов через контракт ввода вывода ``UnidriverIO``.

.. toctree::
   :maxdepth: 2
   :caption: Содержание

   architecture
   data-model
   operations
   api
   modules
