from django.http import HttpResponse, Http404, HttpResponseBadRequest, HttpResponseForbidden
from django.conf import settings
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from hashlib import sha256
import json, hmac
from data_import.tasks import handle_webhook
import logging

log = logging.getLogger('django')

from pprint import pprint

# Create your views here.
class WebhookView(View):
    handle = 'inventory-updated'

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(WebhookView, self).dispatch(request, *args, **kwargs)

    def get(self, request, handle):
        challenge = request.GET.get('challenge')
        if handle == self.handle and challenge is not None:
            log.info('challenge: {}'.format(challenge))
            return HttpResponse(challenge)

        raise Http404('Webhook not found')

    def post(self, request, handle):
        # HMAC verification
        # Make sure this is a valid request from Dropbox
        signature = request.META['HTTP_X_DROPBOX_SIGNATURE']
        app_secret = settings.DROPBOX_APP_SECRET
        if not hmac.compare_digest(
                signature,
                hmac.new(
                    app_secret.encode('utf-8'),
                    request.body,
                    sha256).hexdigest()):
            return HttpResponseForbidden()

        if handle == self.handle:
            raw_body = request.body.decode('utf-8')
            try:
                data = json.loads(raw_body)
                log.info('webhook data: {}'.format(data))

                # Process request in worker task
                handle_webhook(data)

                return HttpResponse('OK')
            except ValueError:
                return HttpResponseBadRequest()

        raise Http404('Webhook not found')
