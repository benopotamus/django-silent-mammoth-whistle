Django Silent Mammoth Whistle
#############################

A super-simple user analytics tool that tracks user behaviour based on web requests to your Django app.

It's intended for use with libraries such as `htmx <https://htmx.org>`_, which generally make a web request for each user interaction. It also includes a JavaScript function for tracking purely client-side actions (e.g. things you might use `Alpine.js <https://alpinejs.dev/>`_ for). The UI is designed for small projects where understanding individual user behaviour is useful.

Features
========

* (optional) Automatic tracking of all web requests - no additional code needed in your project
* JavaScript function for tracking client-side actions
* Separate reporting of authenticated and anonymous sessions
* Shows top platforms, top user-agents (using `user-agents <https://pypi.org/project/user-agents/>`_), top viewport sizes, and new users, for each month
* Tracking cookies can be disabled - you just won't see viewport size data

Requirements
============

Django 4.2+ and Python 3.8+

Installation
============

1. ``pip install django-silent-mammoth-whistle``

2. Add silent mammoth whistle to ``INSTALLED_APPS`` setting::

	  INSTALLED_APPS = [
        ...,
        "silent_mammoth_whistle",
		    ...,
    ]

	Ideally just above the main app. This is because silent mammoth whistle will intercept async JavaScript requests (if you use them) to log client side events (e.g. opening a dialog box). When it does this, it prevents the request from making it to ``views.py`` of the main app and being accidently interpreted by a view.

3. Add silent mammoth whistle middleware. At the end is fine::
	
    MIDDLEWARE = [
		    ...,
		    'silent_mammoth_whistle.middleware.SilentMammothWhistleMiddleware',
    ]
	
4. Include the silent mammoth whistle URLconf in your project urls.py. The URL (e.g. ``/mammoth``) can be anything you like::
	
    'path('/mammoth', include('silent_mammoth_whistle.urls')),'
	
5. Add ``<script src="{% static 'silent_mammoth_whistle/js/whistle.js' %}"></script>`` to your templates

6. Run ``migrations ./manage.py migrate silent_mammoth_whistle``

Configuration
=============

All configuration is optional

settings.py
-----------

``WHISTLE_USER_ID_FIELD``

	Defaults to ``'id'``

	The name (as a string) of a ``User`` model attribute that is used as the user identified. It appears in the UI and it used for determining which web requests belong to which users. It should be a unique value.


``WHISTLE_AUTO_LOG_REQUESTS``

	Defaults to ``True``

	When True, all web requests are tracked. Disable this feature if you want to record only specific requests.


``WHISTLE_CLIENT_EVENT_PATH``

	Defaults to ``'/whistle'``

	The url used by ``whistle.js`` to make web requests using JavaScript.


``WHISTLE_COOKIES``

	Defaults to ``True``

	When True, a cookie is added to clients and is used with some JavaScript to record viewport dimensions. I don't think this constitutes a "tracking cookie", but if you think it does, and you don't want that, just set this to ``False``


Usage
=====

By default, silent mammoth whistle will record all web requests (with a HTTP method and the URL for each request).

You can also record additional data for a request. 

    .. code-block:: Python

    request.whistle.request('put a string here')

Silent mammoth whistle is super-simple and the data for requests needs to be in a string format. You can record as much data as you like, and you can make as many of these ``request.whistle.request()`` calls as you like. Silent mammoth whistle will merge the strings from all the calls into a single string, separated by a tab.

Practical example! This line will record the fields present in a POST request. This could be useful if your form has many optional fields and you want to know which ones were included.

    .. code-block:: Python

    request.whistle.request('fields=' + ", ".join(request.POST.dict().keys()))

The session details in silent mammoth whistle has 3 columns: time, request, and response. Request is the obvious column to use, but you might like to separate tracking of what the user requested from how the server responded. E.g.

    .. code-block:: Python

    request.whistle.response('fields in error=' + ", ".join(form.errors.dict().keys()))

These calls all start with ``request.`` because silent mammoth whistle adds a ``whistle`` object to the standard Django ``request`` object.

The JavaScript API is similar

    .. code-block:: JavaScript

    whistle('Edit dialog box open')
