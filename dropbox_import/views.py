import hmac, json, logging
from hashlib import sha256

from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.conf import settings

from core.controllers import Controller
from interfaces import DropboxInterface
from .tasks import process_inventory_file


log = logging.getLogger('development')
controller = Controller()


"""Dropbox webhook handling functions

https://www.dropbox.com/developers/reference/webhooks
"""


# Dropbox webhook verification
def verify_webhook(request):
    challenge = request.GET.get('challenge')
    if challenge is not None:
        return HttpResponse(challenge)
    else:
        return HttpResponseBadRequest('Missing "challenge" parameter.')


# responds to the dropbox webhook request
def process_webhook_notification(request):
    log.debug('process_webhook_notification view')

    # Make sure this is a valid request from Dropbox
    if not settings.DEBUG and not is_request_valid(request):
        return HttpResponseForbidden()

    # Ensure the body is valid utf-8 text
    try:
        raw_body = request.body.decode('utf-8')
    except UnicodeError:
        return HttpResponseBadRequest()

    # Decode json body data
    try:
        data = json.loads(raw_body)
    except ValueError:
        return HttpResponseBadRequest()

    # 'data' just holds the accounts and users that have changed files on
    # dropbox. We only have one account and one user to we just ignore the data
    # and simply list files on using our preconfigured dropbox api token.
    # If we need to expand this app to multiple accounts and users we'd need
    # this data.

    try:
        controller.handle_dropbox_file_change_notification()
    except Exception as e:
        log.exception(e)

    return HttpResponse('OK')


# verifies the request came from our dropbox app
def is_request_valid(request):
    generated_digest = hmac.new(
        settings.DROPBOX_APP_SECRET.encode('utf-8'),
        request.body,
        sha256
    ).hexdigest()

    # HMAC verification
    return hmac.compare_digest(
        request.META['HTTP_X_DROPBOX_SIGNATURE'],
        generated_digest
    )
