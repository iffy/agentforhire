"""
I am an abomination of broken rules and conventions.  I am the epitome of bad
code.  I am nothing if not a hack.  I know this.  Complain not about me for I
don't claim to be good

Instead, make something better.
"""

# miserable hack


#------------------------------------------------------------------------------
# implementation
#------------------------------------------------------------------------------

from zope.interface import implements
from twisted.internet import reactor, defer, protocol, address, interfaces
from twisted.web.resource import Resource
from twisted.web.server import Site
from twisted.web import client, _newclient
from twisted.web.http_headers import Headers
from twisted.protocols import loopback



class FakeTransport(loopback._LoopbackTransport):
    """
    I subclass a private class.  Yeah.  I know.
    """

    def __init__(self, q, peer_addr=None, host_addr=None):
        loopback._LoopbackTransport.__init__(self, q)
        self._peer_addr = peer_addr or loopback._LoopbackAddress()
        self._host_addr = host_addr or loopback._LoopbackAddress()


    def pauseProducing(self):
        pass


    def resumeProducing(self):
        pass


    def getPeer(self):
        return self._peer_addr


    def getHost(self):
        return self._host_addr



def loopbackAsync(server, client, server_addr=None, client_addr=None):
    """
    I'm a copy of twisted.protocols.loopback.loopbackAsync with support for
    choosing addresses.  Am I a bad idea?  You bet, I am.
    """
    serverToClient = loopback._LoopbackQueue()
    clientToServer = loopback._LoopbackQueue()
    
    server.makeConnection(FakeTransport(serverToClient, client_addr, server_addr))
    client.makeConnection(FakeTransport(clientToServer, server_addr, client_addr))
    
    return loopback._loopbackAsyncBody(
        server, serverToClient, client, clientToServer,
        loopback.identityPumpPolicy)



class ClientProtocol(_newclient.HTTP11ClientProtocol):


    def __init__(self, request, quiescentCallback=None):
        _newclient.HTTP11ClientProtocol.__init__(self, quiescentCallback)
        self.request_object = request
        self.response = defer.Deferred()

    def connectionMade(self):
        _newclient.HTTP11ClientProtocol.connectionMade(self)
        
        r = self.request(self.request_object)
        r.addErrback(self._err)
        r.addBoth(self._allDone)

    def _allDone(self, response):
        self.response.callback(response)

    def _err(self, response):
        err = response.value.args[0][0]
        return response


class TerribleFunctionalAgent(client.Agent):
    
    def __init__(self, resource, addr=None):
        self.root = resource
        self.addr = addr or address.IPv4Address('TCP', '127.0.0.1', 12345)


    def request(self, method, uri, headers=None, bodyProducer=None):
        parsedURI = client._parse(uri)
        
        host_addr = address.IPv4Address('TCP', parsedURI.host, parsedURI.port)
        
        
        # ripped from _AgentBase._requestWithEndpoint
        if headers is None:
            headers = Headers()
        if not headers.hasHeader('host'):
            headers = headers.copy()
            headers.addRawHeader(
                'host', self._computeHostValue(parsedURI.scheme, parsedURI.host,
                                               parsedURI.port))
        request = client.Request(method, parsedURI.path, headers, bodyProducer,
                                 persistent=False)

        c = ClientProtocol(request)
        
        # ouch
        self.root.putChild('', self.root)
        
        server = Site(self.root).buildProtocol(self.addr)
        loopbackAsync(server, c, host_addr, self.addr)
        return c.response.addBoth(self._done, c)


    def _done(self, result, proto):
        return result

# end of miserable hack



#------------------------------------------------------------------------------
# test
#------------------------------------------------------------------------------
from twisted.trial.unittest import TestCase
from forhire.mixin import ResourceAgentTestMixin


class MyTest(TestCase, ResourceAgentTestMixin):


    def getAgent(self, resource, client_address=None):
        return TerribleFunctionalAgent(resource, client_address)


