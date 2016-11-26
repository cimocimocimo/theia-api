from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.conf import settings
from hashlib import sha256
import json, hmac

from .tasks import handle_webhook

class DropboxInterface:
    def __init__(self):
        pass

    @classmethod
    def verify_webhook(cls, request):
        challenge = request.GET.get('challenge')
        if challenge is not None:
            return HttpResponse(challenge)
        else:
            return HttpResponseBadRequest('Missing "challenge" parameter.')

    @classmethod
    def process_notification(cls, request):
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

        raw_body = request.body.decode('utf-8')
        try:
            data = json.loads(raw_body)
            # Process request in worker task
            for account in data['list_folder']['accounts']:
                handle_webhook.delay(account)

            return HttpResponse('OK')
        except ValueError:
            return HttpResponseBadRequest()
