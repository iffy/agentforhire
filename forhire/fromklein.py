from twisted.internet import reactor, defer
from twisted.web.client import Agent


class MostlyRealAgent(object):
    
    
    def __init__(self, resource, addr=None):
        self.agent = Agent(reactor)


    def request(self, method, uri, headers=None, bodyProducer=None):
        return defer.succeed({})



#------------------------------------------------------------------------------
# test
#------------------------------------------------------------------------------
from twisted.trial.unittest import TestCase
from forhire.mixin import ResourceAgentTestMixin

class MostlyRealAgentTest(TestCase, ResourceAgentTestMixin):

    
    def getAgent(self, resource, address=None):
        return MostlyRealAgent(resource, address)