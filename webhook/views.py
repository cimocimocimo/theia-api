from django.http import HttpResponse, Http404, HttpResponseBadRequest, HttpResponseForbidden
from django.conf import settings
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from hashlib import sha256
import json, hmac
import logging

from data_import.tasks import handle_webhook

log = logging.getLogger('django')

from pprint import pprint

# TODO: refactor this view to allow other apps to register their own webhooks.
# I think I can use signals for this.
class WebhookView(View):
    handle = 'inventory-updated'

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(WebhookView, self).dispatch(request, *args, **kwargs)

    def get(self, request, handle):
        # TODO: refactor this code into the data_import app. It is specific to
        # dropbox webhooks only.
        challenge = request.GET.get('challenge')
        # TODO: the handle checking code should be in this webhook app. the
        # challenge specific stuff should be moved to the dropbox specific
        # stuff.
        if handle == self.handle and challenge is not None:
            log.info('challenge: {}'.format(challenge))
            return HttpResponse(challenge)

        raise Http404('Webhook not found')

    # TODO: could the get and post handlers be combined into a single method?
    # If so then the handle checking code could live in one place and then use
    # an if/else for the get/post specific code.
    def post(self, request, handle):
        # HMAC verification
        # Make sure this is a valid request from Dropbox
        signature = request.META['HTTP_X_DROPBOX_SIGNATURE']
        app_secret = settings.DROPBOX_APP_SECRET
        if not settings.DEBUG and not hmac.compare_digest(
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
                for account in data['list_folder']['accounts']:
                    handle_webhook.delay(account)

                return HttpResponse('OK')
            except ValueError:
                return HttpResponseBadRequest()

        raise Http404('Webhook not found')
