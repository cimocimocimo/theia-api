from django.conf.urls import url

from .views import WebhookView

urlpatterns = [
    url(r'^(?P<handle>[a-z0-9-]+)/$', WebhookView.as_view(), name='webhook'),
]
