.. :changelog:

Changelog
#########

2.5 (07 May 2025)
=================

Improvements
------------

* Replaced the monthly new users table with a monthly "Logged in users" table. This new table lists the users who made an authenticated whistle during the month. New users are marked with a "new" tag.
* Clicking a row in the main page Sessions table now navigates to the details page for that session
* Toned down the styling for the userid hyperlinks (which navigate to the all sessions page for that user)
* CSS tweaks for smaller screen sizes


2.4 (30 Mar 2025)
=================

Improvements
------------

* Added a new page - user-sessions - which lists all sessions in the database for the selected user. User selection is done by clicking the user id on the home page.
* Updated CSS to *better* support smaller screen sizes

Bug fixes
---------

* When passing multiple arguments to the client side whistle function, they will now be correctly separated by tabs when rendered.
* Client side whistles with no form data will no longer be logged - but they'll still return a 204 so the client doesn't process it as an error.

2.3 (18 Mar 2025)
=================

Improvements
------------

* Added ``referer`` url for the first request in a session

Bug fixes
---------

Thank you **jbaack** for finding these.

* Fixed incorrect path slashes when including ``chart.js`` in the ``index.html`` template
* Fixed bug where the ``index`` view had an error if ``django-invitations`` was not installed
* Active invitations (on index page) now only lists *unaccepted* invitations

2.2 (23 December 2024)
======================

Improvements
------------

* viewport dimensions cookie now uses ``SameSite: Strict``

2.1 (22 December 2024)
======================

Improvements
------------

* Added counts of 4xx and 5xx responses to the session summary on the main page.
* Added color to 4xx and 5xx responses on the whistle details page.
* Added 3 new settings: ``WHISTLE_AUTOLOG_REQUEST_METHOD``, ``WHISTLE_AUTOLOG_REQUEST_PATH``, and ``WHISTLE_AUTOLOG_RESPONSE_CODE``. These replace the ``WHISTLE_AUTO_LOG`` setting. See README.rst for details.


2.0 (10 October 2024)
=====================

Improvements
------------

* Added basic bot filtering. The chart and whistles should be almost all non-bot requests now.
* Added a minimum for the y-axis on the chart so you can really appreciate when a project takes off.

Breaking change
---------------

* The bot filtering relies on clients executing some JavaScript (sends a 'PING' request) which is then used to filter out sessions that don't have it. It seems bots don't generally execute the JavaScript. As a result, old sessions (those created before this update) will be hidden.

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
