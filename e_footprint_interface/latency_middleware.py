import time


class NetworkLatencyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        time.sleep(0)

        response = self.get_response(request)
        return response
