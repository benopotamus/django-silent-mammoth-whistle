.. :changelog:

Changelog
#########

2.0.0 (10 October 2024)
=======================

Improvements
------------

* Added basic bot filtering. The chart and whistles should be almost all non-bot requests now.
* Added a minimum for the y-axis on the chart so you can really appreciate when a project takes off.

Breaking change
---------------

The bot filtering relies on clients executing some JavaScript (sends a 'PING' request) which is then used to filter out sessions that don't have it. It seems bots don't generally execute the JavaScript. As a result, old sessions (those created before this update) will be hidden.

1.2.4 and 1.2.5 (18 September 2024)
===================================

Updating packaging method. No functional change to app.

1.2.3 (14 August 2024)
======================

Silent mammoth whistle already ignores whistles from is_staff users. It now also removes the anonymous session whistles for users who eventually authenticate as an is_staff user.

1.2.2 (14 August 2024)
======================

Added missing dependency ``user-agents`` to ``setup.cfg``

1.2.1 (3 August 2024)
=====================

Minor doco update. No functional changes.

1.2.0 (3 August 2024)
=====================

I added a changelog! :-D

Breaking change
---------------

* WHISTLE_AUTO_LOG_REQUESTS setting renamed to WHISTLE_AUTO_LOG

Improvements
------------

* WHISTLE_AUTO_LOG now also logs the HTTP response code and reason
* ``whistle.request()`` and ``whistle.response()`` now accept values other than strings. They'll be cast to strings using ``str()`` before saving. 
