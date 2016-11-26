from django.http import Http404, HttpResponse, HttpResponseServerError
from django.conf import settings
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

class WebhookView(View):
    webhooks = dict()

    @classmethod
    def register(cls, handle, callbacks):
        cls.webhooks[handle] = callbacks

    @method_decorator(csrf_exempt)
    def dispatch(self, request, handle, *args, **kwargs):
        if not handle in self.webhooks:
            raise Http404('Webhook not found')
        response = self.webhooks[handle][request.method](request)
        if isinstance(response, HttpResponse):
            return response
        else:
            return HttpResponseServerError
