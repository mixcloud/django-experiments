from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

admin.autodiscover()

urlpatterns = [
    path('experiments/', include('experiments.urls')),
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name="test_page.html"), name="test_page"),
    path('goal/', TemplateView.as_view(template_name="goal.html"), name="goal"),
]

