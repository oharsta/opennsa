"""
A nice handy HTTP client.

Author: Henrik Thostrup Jensen <htj@nordu.net>
Copyright: NORDUnet (2011-2012)
"""

from twisted.python import log
from twisted.internet import reactor, defer
from twisted.web import client as twclient, http as twhttp
from twisted.web.error import Error as WebError
from twisted.internet.error import ConnectionClosed, ConnectionRefusedError


LOG_SYSTEM = 'HTTPClient'

DEFAULT_TIMEOUT = 30 # seconds



class HTTPRequestError(Exception):
    """
    Raised when a request could not be made or failed in an unexpected way.
    """


def soapRequest(url, soap_action, soap_envelope, timeout=DEFAULT_TIMEOUT, ctx_factory=None, headers=None):

    if not headers:
        headers = {}

    headers['Content-Type'] = 'text/xml; charset=utf-8' # CXF will complain if this is not set
    headers['soapaction'] = soap_action

    return httpRequest(url, soap_envelope, headers, ctx_factory=ctx_factory)



def httpRequest(url, payload, headers, method='POST', timeout=DEFAULT_TIMEOUT, ctx_factory=None):
    # copied from twisted.web.client in order to get access to the
    # factory (which contains response codes, headers, etc)

    if type(url) is not str:
        e = HTTPRequestError('URL must be string, not %s' % type(url))
        return defer.fail(e)

    if not url.startswith('http'):
        e = HTTPRequestError('URL does not start with http (URL %s)' % (url))
        return defer.fail(e)

    log.msg(" -- Sending Payload to %s --\n%s\n -- END. Sending Payload --" % (url, payload), system=LOG_SYSTEM, payload=True)

    scheme, netloc, _ , _, _, _ = twhttp.urlparse(url)
    if not ':' in netloc:
        host = netloc
        port = 80 if scheme == 'http' else 443
    else:
        host, s_port = netloc.split(':',1)
        port = int(s_port)

    factory = twclient.HTTPClientFactory(url, method, postdata=payload, timeout=timeout)
    factory.noisy = False # stop spewing about factory start/stop
    factory.protocol.handleStatus_204 = lambda _ : None # 204 is an ok reply, needed by NCS VPN backend

    # fix missing port in header (bug in twisted.web.client)
    factory.headers['host'] = host + ':' + str(port)
    factory.headers['User-Agent'] = 'OpenNSA/Twisted'

    for header, value in list(headers.items()):
        factory.headers[header] = value

    if scheme == 'https':
        if ctx_factory is None:
            return defer.fail(HTTPRequestError('Cannot perform https request without context factory'))
        reactor.connectSSL(host, port, factory, ctx_factory)
    else:
        reactor.connectTCP(host, port, factory)

    def invocationError(err):
        if isinstance(err.value, ConnectionClosed): # note: this also includes ConnectionDone and ConnectionLost
            pass # these are pretty common when the remote shuts down
        elif isinstance(err.value, WebError):
            data = err.value.response
            log.msg(' -- Received Reply (fault) --\n%s\n -- END. Received Reply (fault) --' % data, system=LOG_SYSTEM, payload=True)
            return err
        elif isinstance(err.value, ConnectionRefusedError):
            log.msg('Connection refused for %s:%i. Request URL: %s' % (host, port, url), system=LOG_SYSTEM)
            return err
        else:
            return err

    def logReply(data):
        log.msg(" -- Received Reply --\n%s\n -- END. Received Reply --" % data, system=LOG_SYSTEM, payload=True)
        return data

    factory.deferred.addCallbacks(logReply, invocationError)

    return factory.deferred

