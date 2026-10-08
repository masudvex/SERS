from . import texts


class SiteTextMiddleware:
    """Loads all editable texts once per request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        texts.begin_request()
        try:
            return self.get_response(request)
        finally:
            texts.end_request()
