#! /usr/bin/python

# This is the client side of a manual test for the socks/tor
# connection-handler code. To use it, first set up the server as described in
# the other file, then copy the hostname, tubid, and .onion address into this
# file:

HOSTNAME = "foolscap.lothar.com"
TUBID = "qy4aezcyd3mppt7arodl4mzaguls6m2o"
ONION = "kwmjlhmn5runa4bv.onion"
ONIONPORT = 16545
LOCALPORT = 7006

# Then run 'check-connections-client.py tcp', then with 'socks', then with
# 'tor'.

import os, sys, time
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.endpoints import HostnameEndpoint, clientFromString
from foolscap.api import Referenceable, Tub


tub = Tub()

which = sys.argv[1] if len(sys.argv) > 1 else None
if which == "tcp":
    furl = "pb://%s@tcp:%s:%d/calculator" % (TUBID, HOSTNAME, LOCALPORT)
elif which == "socks":
    # "slogin -D 8013 HOSTNAME" starts a SOCKS server on localhost 8013, for
    # which connections will emerge from the other end. Check the server logs
    # to see the peer address of each addObserver call to verify that it is
    # coming from 127.0.0.1 rather than the client host.
    from foolscap.connections import socks
    h = socks.SOCKS(HostnameEndpoint(reactor, "localhost", 8013))
    tub.removeAllConnectionHintHandlers()
    tub.addConnectionHintHandler("tcp", h)
    furl = "pb://%s@tcp:localhost:%d/calculator" % (TUBID, LOCALPORT)
elif which in ("default-socks", "socks-port", "launch-tor", "control-tor"):
    from foolscap.connections import tor
    if which == "default-socks":
        h = tor.default_socks()
    elif which == "socks-port":
        h = tor.socks_on_port(int(sys.argv[2]))
    elif which == "launch-tor":
        data_directory = None
        if len(sys.argv) > 2:
            data_directory = os.path.abspath(sys.argv[2])
        h = tor.launch_tor(reactor, data_directory)
    elif which == "control-tor":
        control_ep = clientFromString(reactor, sys.argv[2])
        h = tor.with_control_port(reactor, control_ep)
    tub.removeAllConnectionHintHandlers()
    tub.addConnectionHintHandler("tor", h)
    furl = "pb://%s@tor:%s:%d/calculator" % (TUBID, ONION, ONIONPORT)
else:
    print "run as 'check-connections-client.py [tcp|socks|tor]'"
    sys.exit(1)
print "using %s: %s" % (which, furl)

class Observer(Referenceable):
    def remote_event(self, msg):
        pass

@inlineCallbacks
def go():
    tub.startService()
    start = time.time()
    rtts = []
    remote = yield tub.getReference(furl)
    t_connect = time.time() - start

    o = Observer()
    start = time.time()
    yield remote.callRemote("addObserver", observer=o)
    rtts.append(time.time() - start)

    start = time.time()
    yield remote.callRemote("removeObserver", observer=o)
    rtts.append(time.time() - start)

    start = time.time()
    yield remote.callRemote("push", num=2)
    rtts.append(time.time() - start)

    start = time.time()
    yield remote.callRemote("push", num=3)
    rtts.append(time.time() - start)

    start = time.time()
    yield remote.callRemote("add")
    rtts.append(time.time() - start)

    start = time.time()
    number = yield remote.callRemote("pop")
    rtts.append(time.time() - start)
    print "the result is", number

    print "t_connect:", t_connect
    print "avg rtt:", sum(rtts) / len(rtts)

d = go()
def _oops(f):
    print "error", f
d.addErrback(_oops)
d.addCallback(lambda res: reactor.stop())

reactor.run()
