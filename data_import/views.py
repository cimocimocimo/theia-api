from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.conf import settings
from hashlib import sha256
import hmac, json, logging

log = logging.getLogger('django')

# Dropbox webhook verification
def verify_webhook(request):
    challenge = request.GET.get('challenge')
    if challenge is not None:
        return HttpResponse(challenge)
    else:
        return HttpResponseBadRequest('Missing "challenge" parameter.')

# responds to the dropbox webhook request
def process_notification(request):
    log.debug('process_notification view')

    # Make sure this is a valid request from Dropbox
    if not settings.DEBUG and not is_request_valid(request):
        return HttpResponseForbidden()

    try:
        raw_body = request.body.decode('utf-8')
    except UnicodeError:
        return HttpResponseBadRequest()

    try:
        data = json.loads(raw_body)
    except ValueError:
        return HttpResponseBadRequest()

    from .tasks import handle_notification
    handle_notification(data)

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

