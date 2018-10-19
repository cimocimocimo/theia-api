# TODO: Look into using Django Signals for decoupled communication between apps
# and these webhooks.

# register webhook in other app by calling this function in your AppConfig.ready() method
# callback should be a dict with http methods as the keys and the callbacks for the values
def register_webhook(handle, callback):
    from webhook.views import WebhookView
    WebhookView.register(handle, callback)
