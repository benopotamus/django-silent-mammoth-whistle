from django.urls import path
from .views import *

app_name = 'silent_mammoth_whistle'

urlpatterns = [
	path('<str:user_id>/<str:requested_date>', session, name='session'),
	path('<str:requested_date>', index, name='index_by_date'),
	path('', index, name='index'),
]