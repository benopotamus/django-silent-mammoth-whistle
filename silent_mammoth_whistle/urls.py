from django.urls import path
from .views import *

app_name = 'silent_mammoth_whistle'

urlpatterns = [
	path('sessions/<str:user_id>/<str:requested_date>', session, name='session'),
	path('sessions/<str:user_id>', user_sessions, name='user_sessions'),
	path('<str:requested_date>', index, name='index_by_date'),
	path('', index, name='index'),
]