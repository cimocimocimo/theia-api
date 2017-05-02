from django.test import SimpleTestCase
from . import register_webhook
from .views import WebhookView
from django.http import HttpResponse, HttpResponseServerError, HttpRequest

test_webhook = ('test-webhook', {
    'GET': lambda x: HttpResponse('OK'),
    'POST': lambda x: HttpResponse('OK'),
})

invalid_webhook = ('invalid-webhook', {
    'GET': lambda x: False,
    'POST': lambda x: False,
})

class RegisterWebhookTest(SimpleTestCase):
    def test_register_webhook(self):
        register_webhook(test_webhook[0], test_webhook[1])
        self.assertTrue('test-webhook' in WebhookView.webhooks)

class ModelTest(SimpleTestCase):
    def test_webhook_response(self):
        register_webhook(test_webhook[0], test_webhook[1])
        r = self.client.get('/webhook/test-webhook/')
        self.assertEqual(r.status_code, 200)
        r = self.client.post('/webhook/test-webhook/', {'testvar': 'testvalue'})
        self.assertEqual(r.status_code, 200)

    def test_404(self):
        register_webhook(test_webhook[0], test_webhook[1])
        r = self.client.get('/webhook/not-registered/')
        self.assertEqual(r.status_code, 404)

