from suds.transport.https import HttpAuthenticated, HttpTransport

"""
Boilerplate code provided by CDMO web services for accessing the API with username/password
instead of relying on the IP whitelist.
"""


class CustomTransport(HttpAuthenticated):
    def __init__(self, username, password):
        self.username = username
        self.password = password
        HttpAuthenticated.__init__(self, username=username, password=password)

    def open(self, request):
        request.headers["authorization"] = f"Basic {self._basic_auth()}"
        return HttpTransport.open(self, request)

    def _basic_auth(self):
        import base64

        credentials = f"{self.username}:{self.password}"
        return base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
