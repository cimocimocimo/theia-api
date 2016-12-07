from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.conf import settings
from hashlib import sha256
import json, hmac

from .tasks import start_dropbox_notification_tasks

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
        # Make sure this is a valid request from Dropbox
        if not settings.DEBUG and not self.is_request_valid(request):
            return HttpResponseForbidden()

        try:
            raw_body = request.body.decode('utf-8')
        except UnicodeError:
            return HttpResponseBadRequest()

        try:
            data = json.loads(raw_body)
        except ValueError:
            return HttpResponseBadRequest()

        start_dropbox_notification_tasks(data)

        return HttpResponse('OK')


    @classmethod
    def is_request_valid(cls, request):
        # HMAC verification
        return hmac.compare_digest(
            request.META['HTTP_X_DROPBOX_SIGNATURE'],
            self.generate_signature(request)
        )

    @classmethod
    def generate_signature(cls, request):
        return hmac.new(
            settings.DROPBOX_APP_SECRET.encode('utf-8'),
            request.body,
            sha256
        ).hexdigest()
