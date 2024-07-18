from django.contrib import admin
from django.urls import path
from .views import QueryView, DataTableView, custom_page_not_found
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
	# path('admin/', admin.site.urls),
	# path('api-token-auth/', obtain_auth_token, name='api_token_auth'),
    path('query/', QueryView.as_view(), name='query'),
	path('data_table/', DataTableView.as_view(), name='data_table'),
	path('query/<str:db_name>/', QueryView.as_view(), name='query'),
	path('data_table/<str:db_name>/', DataTableView.as_view(), name='data_table'),
]
# Настройка обработчика ошибки 404
handler404 = custom_page_not_found