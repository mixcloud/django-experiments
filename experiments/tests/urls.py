from experiments.urls import urlpatterns
from django.urls import path
from django.contrib import admin


urlpatterns += [
    path('admin/', admin.site.urls),
]
