.. :changelog:

Changelog
#########

1.2.0 (3 August 2024)
====================

I added a changelog! :-D

Breaking change
---------------

* WHISTLE_AUTO_LOG_REQUESTS setting renamed to WHISTLE_AUTO_LOG

Improvements
------------

* WHISTLE_AUTO_LOG now also logs the HTTP response code and reason
* ``whistle.request()`` and ``whistle.response()`` now accept values other than strings. They'll be cast to strings using ``str()`` before saving. 
