from request.models import Request
from request import settings

class RequestMiddleware(object):
    def process_response(self, request, response):
        if request.is_ajax() and settings.REQUEST_IGNORE_AJAX:
            return response
        
        if request.META.get('REMOTE_ADDR') in settings.REQUEST_IGNORE_IP:
            return response
        
        if getattr(request, 'user', False):
            if request.user.username in settings.REQUEST_IGNORE_USERNAME:
                return response
        
        r = Request()
        r.from_http_request(request, response)
        
        return response
