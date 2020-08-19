from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSKernelSwitch, \
    UserSwitch, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import Link, TCLink
import threading, random, time
from utils import *

link = None

def create_topo():
    global link
    net = Mininet(controller=RemoteController, link=TCLink, switch=OVSSwitch)

    # Creating hosts
    host = {}
    for i in range(1, 4):
        host[i] = net.addHost(
            name='h%s'%(i), 
            mac='00:00:00:00:00:0%s'%(i),
            ip='10.0.0.%s'%(i)
        )
    
    server = {}
    for i in range(0, 12):
        server[i + 1] = net.addHost(
            name='s%s'%(i + 1), 
            mac='00:00:00:00:0%s:0%s'%(int(i/4) + 1, i%4 + 1),
            ip='10.0.%s.%s'%(int(i/4) + 1, i%4 + 1)
        )

    # Creating Switches    
    switch = {}
    for i in range(1, 17):
        switch[i] = net.addSwitch( name='sw%s'%(i))

    controller = net.addController(
        name='controller',
        controller=RemoteController,
        ip=IP_CONTROLLER,
        port=PORT_CONTROLLER,
    )

    # Establishing connection via links
    # connections = [
    #     (server[1], switch[1]), (server[2], switch[1]), (server[3], switch[2]),
    #     (server[4], switch[2]), (switch[1], switch[3]), (switch[2], switch[4]),
    #     (switch[2], switch[3]), (switch[1], switch[4]), (server[5], switch[5]),
    #     (server[6], switch[5]), (server[7], switch[6]), (server[8], switch[6]),
    #     (switch[5], switch[7]), (switch[6], switch[8]), (switch[6], switch[7]),
    #     (switch[5], switch[8]), (server[9], switch[9]), (server[10], switch[9]),
    #     (server[11], switch[10]), (server[12], switch[10]), (switch[9], switch[11]),
    #     (switch[10], switch[12]), (switch[10], switch[11]), (switch[9], switch[12]),
    #     (host[1], switch[13]), (host[2], switch[14]), (host[3], switch[16]),
    #     (switch[3], switch[13]), (switch[3], switch[14]), (switch[4], switch[14]),
    #     (switch[7], switch[13]), (switch[7], switch[14]), (switch[7], switch[15]),
    #     (switch[8], switch[15]), (switch[8], switch[16]), (switch[11], switch[14]),
    #     (switch[12], switch[15]), (switch[12], switch[16])
    # ]
    connections = [
        (server[1], switch[1]), (server[2], switch[1]), (server[3], switch[2]),
        (server[4], switch[2]), (switch[1], switch[3]),
        (switch[2], switch[3]), (switch[1], switch[4]), (server[5], switch[5]),
        (server[6], switch[5]), (server[7], switch[6]), (server[8], switch[6]),
        (switch[5], switch[7]), (switch[6], switch[7]),
        (switch[5], switch[8]), (server[9], switch[9]), (server[10], switch[9]),
        (server[11], switch[10]), (server[12], switch[10]), (switch[9], switch[11]),
        (switch[10], switch[11]),
        (host[1], switch[13]), (host[2], switch[14]), (host[3], switch[16]),
        (switch[3], switch[13]), (switch[3], switch[14]),
        (switch[7], switch[13]), (switch[7], switch[15]),
        (switch[8], switch[16]), (switch[11], switch[14]),
        (switch[12], switch[15])
    ]
    link = {}
    for i, item in enumerate(connections):
        link[i] = net.addLink(item[0], item[1], cls=TCLink, bw=BANDWIDTH[0], loss=0)


    net.build()
    # controller.start()
    for controller in net.controllers:
        controller.start()
    for _, item in switch.items():
        item.start([controller])
    # net.start()
    CLI(net)
    print "net is done..."
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    create_topo()