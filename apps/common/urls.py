from django.urls import path

from apps.common.views import ServerTimeView, health_check_celery, health_check_redis

app_name = "common"

urlpatterns = [
    path("health-check/redis/", health_check_redis, name="health-check-redis"),
    path("health-check/celery/", health_check_celery, name="health-check-celery"),
    path("server-time/", ServerTimeView.as_view(), name="server-time"),
]
