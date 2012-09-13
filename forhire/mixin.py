from twisted.web.resource import Resource
from twisted.internet import protocol, defer


class JustTheBodyProtocol(protocol.Protocol):
    """
    I collect the body of a web response and callback my C{finished} Deferred
    with the entire body as a string when the response is done.
    """


    def __init__(self):
        self.finished = defer.Deferred()
        self._data = ''


    def dataReceived(self, data):
        self._data += data


    def connectionLost(self, reason):
        self.finished.callback(self._data)



def getBody(response):
    """
    Get the entire body of the response as a string
    
    @rtype: C{Deferred}
    """
    proto = JustTheBodyProtocol()
    response.deliverBody(proto)
    return proto.finished




class ResourceAgentTestMixin(object):

    timeout = 1


    def getAgent(self, resource, client_address=None):
        """
        Get an instance of the Agentish to be tested.
        
        @param resource: The resource to simulate requesting.
        @param client_address: The L{IAddress} from which the request will
            appear to come.
        
        @return: Something that implements the L{twisted.web.client.Agent} api
            (i.e. has a C{request} method that returns something like what the
            agent returns.)
        """
        raise NotImplementedError("You must implement C{getAgent} in your"
                                  " TestCase in order to use the "
                                  "ResourceAgentTestMixin")


    def test_get(self):
        """
        A simple GET should work.
        """
        class R(Resource):
            def render_GET(self, request):
                return 'GET response'
        
        agent = self.getAgent(R())
        r = agent.request('GET', 'http://example.com')
        r.addCallback(getBody)
        
        def check(body):
            self.assertEqual(body, 'GET response')
        return r.addCallback(check)

