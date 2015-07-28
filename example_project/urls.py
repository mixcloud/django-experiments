from django.contrib import admin
from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView

admin.autodiscover()

urlpatterns = patterns('',
    url(r'experiments/', include('experiments.urls')),
    url(r'admin/', include(admin.site.urls)),
    url(r'^$', TemplateView.as_view(template_name="test_page.html"), name="test_page"),
    url(r'^goal/$', TemplateView.as_view(template_name="goal.html"), name="goal"),
)

