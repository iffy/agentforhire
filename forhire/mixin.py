"""
I contain common tests that any resource-traversing Agent should be able to
pass.  To use them::


    from twisted.trial.unittest import TestCase
    from forhire.mixin import ResourceAgentTestMixin
    
    class MyAwesomeAgentTest(TestCase, ResourceAgentTestMixin):
    
    
        def getAgent(self, resource, address=None):
            # <-- return one of your awesome Agent's to be used on the passed
                  in resource.
            pass


"""

from urllib import urlencode

from zope.interface import implements

from twisted.web.server import Session, NOT_DONE_YET
from twisted.web.resource import Resource
from twisted.web.client import FileBodyProducer
from twisted.web.iweb import IBodyProducer
from twisted.web.static import Data
from twisted.web.http_headers import Headers
from twisted.internet import protocol, defer, address, task

from twisted.python import log

from StringIO import StringIO



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


    def assertBody(self, agent, expected, *args, **kwargs):
        r = agent.request(*args, **kwargs)
        
        def check(body):
            log.msg('assert %r == %r' % (expected, body))
            self.assertEqual(body, expected)
        r.addCallback(getBody)
        return r.addCallback(check)


    def test_get(self):
        """
        A simple GET should work.
        """
        agent = self.getAgent(Data('GET response', 'text/plain'))
        r = agent.request('GET', 'http://example.com')
        
        def gotResponse(response):
            self.assertEqual(response.code, 200)
            return getBody(response)
        r.addCallback(gotResponse)
        
        def check(body):
            self.assertEqual(body, 'GET response')
        return r.addCallback(check)


    def test_response_code(self):
        """
        The response code should be accurate
        """
        class R(Resource):
            def render_GET(self, request):
                request.setResponseCode(199)
                return ''
        
        agent = self.getAgent(R())
        r = agent.request('GET', 'http://example.com')
        
        def gotResponse(response):
            self.assertEqual(response.code, 199)
        return r.addCallback(gotResponse)


    def test_getRequestHostname(self):
        """
        The Resource should be given the correct host.
        """
        class R(Resource):
            def render_GET(self, request):
                return request.getRequestHostname()
        
        agent = self.getAgent(R())
        return self.assertBody(agent, 'example.com', 'GET', 'http://example.com')


    def test_getClientIP(self):
        """
        getClientIP should work correctly
        """
        class R(Resource):
            def render_GET(self, request):
                return str(request.getClientIP())

        agent = self.getAgent(R(), address.IPv4Address('TCP', '10.0.0.1', 293))
        return self.assertBody(agent, '10.0.0.1', 'GET', 'http://example.com')


    def test_getRequestHostname(self):
        """
        getRequestHostname should work
        """
        class R(Resource):
            def render_GET(self, request):
                return str(request.getRequestHostname())
        
        
        agent = self.getAgent(R())
        return self.assertBody(agent, 'foobar.com', 'GET', 'http://foobar.com')


    @defer.inlineCallbacks
    def test_args_GET(self):
        """
        Basic url-encoded argument use should work
        """
        class R(Resource):
            def render_GET(self, request):
                return request.args['foo'][0]
        
        agent = self.getAgent(R())
        yield self.assertBody(agent, 'hello', 'GET', 'http://fo.co/?foo=hello')
        yield self.assertBody(agent, ' ', 'GET', 'http://fo.co/?foo=+')
        yield self.assertBody(agent, ' ', 'GET', 'http://fo.co/?foo=%20')
        
        arg = u'\N{SNOWMAN}'.encode('utf-8')
        yield self.assertBody(agent, arg, 'GET',
                              'http://foo.com/?' + urlencode({'foo':arg}))


    @defer.inlineCallbacks
    def test_args_POST_x_www_form_urlencoded(self):
        """
        Arguments sent as POST data (as from a form) should work
        """
        class R(Resource):
            def render_POST(self, request):
                return request.args['foo'][0]
        
        agent = self.getAgent(R())
        yield self.assertBody(agent, 'hello', 'POST', 'http://foo.com',
                              headers=Headers({'Content-Type': ['application/x-www-form-urlencoded']}),
                              bodyProducer=FileBodyProducer(StringIO('foo=hello')))


    @defer.inlineCallbacks
    def test_args_POST_multipart_form_data(self):
        """
        Arguments sent as multipart data should work
        """
        class R(Resource):
            def render_POST(self, request):
                return request.args['foo'][0]
        
        agent = self.getAgent(R())
        
        # rather than figure out how to make these, I'm just copying what a
        # curl request did one time.  Yes, you can improve this if you'd like.
        headers = Headers({
            'Content-Type': ['multipart/form-data; boundary=----------------------------925679f220d1']
        })
        content = ('------------------------------925679f220d1\r\n'
                   'Content-Disposition: form-data; name="foo"\r\n\r\nbar\r\n'
                   '------------------------------925679f220d1--\r\n')
        yield self.assertBody(agent, 'bar', 'POST', 'http://whatever.com',
                              headers=headers,
                              bodyProducer=FileBodyProducer(StringIO(content)))


    def test_headers(self):
        """
        All headers should be passed through
        """
        class R(Resource):
            def render_GET(self, request):
                return ' '.join(request.requestHeaders.getRawHeaders('x-foo'))
        
        agent = self.getAgent(R())
        headers = Headers({
            'X-Foo': ['a', 'b'],
        })
        return self.assertBody(agent, 'a b', 'GET', 'http://something.com',
                               headers=headers)


    def test_content(self):
        """
        Content should work
        """
        class R(Resource):
            def render_GET(self, request):
                return request.content.read()
        
        agent = self.getAgent(R())
        return self.assertBody(agent, 'something', 'GET', 'http://com.com',
                bodyProducer=FileBodyProducer(StringIO('something')))


    def test_method(self):
        """
        method should be passed in
        """
        class R(Resource):
            def render_FOO(self, request):
                return request.method
        
        agent = self.getAgent(R())
        return self.assertBody(agent, 'FOO', 'FOO', 'http://something')


    @defer.inlineCallbacks
    def test_path(self):
        """
        path attribute should be correct
        """
        class R(Resource):
            def render_GET(self, request):
                return request.path
            def getChild(self, path, request):
                return self
        
        agent = self.getAgent(R())
        yield self.assertBody(agent, '/foo/bar', 'GET', 'http://aaa.com/foo/bar')
        yield self.assertBody(agent, '/', 'GET', 'http://aaa.com')
        yield self.assertBody(agent, '/', 'GET', 'http://aaa.com/')


    def test_getSession(self):
        """
        getSession should work
        """
        test = self
        class R(Resource):
            def render_GET(self, request):
                # this blowing up illustrates why testing over the wire may
                # not be the best idea.
                session = request.getSession()
                test.addCleanup(session.expire)
                test.assertTrue(isinstance(session, Session))
                return ''
        
        agent = self.getAgent(R())
        return self.assertBody(agent, '', 'GET', 'http://www.com')


    def test_delayed(self):
        """
        Delayed renders can be handled
        """
        clock = task.Clock()
        called = []
        
        class R(Resource):
            def finishHim(self, request):
                called.append('finishHim')
                request.write('end')
                request.finish()

            def render_GET(self, request):
                called.append('render')
                clock.callLater(5, self.finishHim, request)
                return NOT_DONE_YET

        resource = R()
        agent = self.getAgent(resource)
        response = agent.request('GET', 'http://www.example.com')        
        body = response.addCallback(getBody)
        
        called.append('before')
        clock.advance(5)
        called.append('after')
        
        def check(body):
            self.assertEqual(body, 'end')
            self.assertEqual(called, [
                'render',
                'before',
                'finishHim',
                'after',
            ], "Should have called things in this order")
        
        return body.addCallback(check)


    def test_redirect(self):
        """
        Requests should be redirectable
        """
        class R(Resource):
            def render_GET(self, request):
                request.redirect('/somewhere')
                return ''
        
        agent = self.getAgent(R())
        r = agent.request('GET', 'http://www.example.com')
        
        def getResponse(response):
            self.assertEqual(response.code, 302)
            self.assertEqual(response.headers.getRawHeaders('Location'),
                             ['/somewhere'])
            return getBody(response)
        r.addCallback(getResponse)
        
        def check(body):
            self.assertEqual(body, '')
        return r.addCallback(check)


    @defer.inlineCallbacks
    def test_resource_tree(self):
        """
        The agent should traverse the resource tree correctly
        """
        class R(Resource):
            def __init__(self, response):
                Resource.__init__(self)
                self._response = response
            def render_GET(self, request):
                return self._response
        
        a = Data('a', 'text/plain')
        c = Data('c', 'text/plain')
        
        a.putChild('b', Data('b', 'text/plain'))
        a.putChild('c', c)
        
        c.putChild('d', Data('d', 'text/plain'))
        
        agent = self.getAgent(a)
        
        # are these assertions correct?
        yield self.assertBody(agent, 'a', 'GET', 'http://example.com')
        yield self.assertBody(agent, 'a', 'GET', 'http://example.com/')
        yield self.assertBody(agent, 'b', 'GET', 'http://example.com/b')
        yield self.assertBody(agent, 'c', 'GET', 'http://example.com/c')
        yield self.assertBody(agent, 'd', 'GET', 'http://example.com/c/d')






