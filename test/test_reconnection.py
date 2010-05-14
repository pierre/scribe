#!/usr/bin/env python

#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import time
import unittest

# FacebookService imports, to access Scribe counters
from fb303 import *

# Thrift imports
from thrift import protocol, transport
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol

# Scribe imports
from scribe import scribe

# Test the reconnection feature for the Network Store
#
# To run the test:
#   1/ Start the primary Scribe server:
#       src > ./scribed ../test/scribe.conf.reconnection.test
#   2/ Start the secondary Scribe server:
#       src > ./scribed ../test/scribe.conf.test
#   3/ Run the tests:
#       test > python test_reconnection.py
#       .
#       ----------------------------------------------------------------------
#       Ran 1 test in 6.008s
#
#       OK
#
# The primary Scribe server (sender) should show in the logs:
#
# [Fri May 14 15:39:19 2010] "[TestReconnection] Changing state from <SENDING_BUFFER> to <STREAMING>"
# [Fri May 14 15:39:21 2010] "Successfully sent <3> messages to remote scribe server <localhost:1463> (<3> since last reconnection)"
# [Fri May 14 15:39:23 2010] "Successfully sent <3> messages to remote scribe server <localhost:1463> (<6> since last reconnection)"
# [Fri May 14 15:39:23 2010] "Sent <6> messages since last reconnect to  <localhost:1463>, threshold is <5>, re-opening the connection"
# [Fri May 14 15:39:23 2010] "Opened connection to remote scribe server <localhost:1463>"
# [Fri May 14 15:39:25 2010] "Successfully sent <1> messages to remote scribe server <localhost:1463> (<1> since last reconnection)"
class TestReconnection(unittest.TestCase):

    def setUp(self):
        self.sender_host = '127.0.0.1'
        self.sender_port = 1455
        self.fb303_client, self.scribe_client, self.transport = self.setupClients(self.sender_host, self.sender_port)
        self.transport.open()

    def tearDown(self):
        self.transport.close()

    def setupClients(self, sender_host, sender_port):
        socket = TSocket.TSocket(host=sender_host, port=sender_port)
        transport = TTransport.TFramedTransport(socket)
        protocol = TBinaryProtocol.TBinaryProtocol(trans=transport, strictRead=False, strictWrite=False)

        fb303_client = FacebookService.Client(protocol, protocol)
        scribe_client = scribe.Client(iprot=protocol, oprot=protocol)

        return fb303_client, scribe_client, transport

    def sendMessages(self, nb):
        msgs = []
        for i in range(nb):
            msgs.append(scribe.LogEntry("TestReconnection", "This is message " + str(i)))
        self.scribe_client.Log(messages=msgs)
        # Throttle to make sure messages go all the way through and counters are updated
        time.sleep(2)

    def totalSentMsgs(self):
        countersString = str(self.fb303_client.getCounters())
        return int(eval(countersString)['scribe_overall:sent'])

    def sentMsgsBetweenReconnect(self):
        countersString = str(self.fb303_client.getCounters())
        return int(eval(countersString)['scribe_overall:sent since last reconnect'])

    def test_reconnect(self):
        self.sendMessages(3)
        self.assertEqual(3, self.totalSentMsgs())
        self.assertEqual(3, self.sentMsgsBetweenReconnect())

        self.sendMessages(3)
        self.assertEqual(6, self.totalSentMsgs())
        # The connection is reset after the full bucket of messages has been sent, hence the 0
        self.assertEqual(0, self.sentMsgsBetweenReconnect())

        self.sendMessages(1)
        self.assertEqual(7, self.totalSentMsgs())
        self.assertEqual(1, self.sentMsgsBetweenReconnect())

if __name__ == '__main__':
    unittest.main()
