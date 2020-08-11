from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSKernelSwitch, \
    UserSwitch, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import Link, TCLink
import threading, random, time
from utils import *

e_random_bw = None
t_random_bw = None
end = False
link = None
lock = threading.Lock()

def create_topo():
    global link, e_random_bw, end, lock
    net = Mininet(controller=RemoteController, link=TCLink, switch=OVSSwitch)

    # Creating hosts
    host = {}
    for i in range(1, 8):
        host[i] = net.addHost(
            name='h%s'%(i), 
            mac='00:00:00:00:00:0%s'%(i),
            ip='10.0.0.%s'%(i)
        )
    
    # Creating Switches    
    switch = {}
    for i in range(1, 5):
        switch[i] = net.addSwitch( name='s%s'%(i))

    controller = net.addController(
        name='controller',
        controller=RemoteController,
        ip=IP_CONTROLLER,
        port=PORT_CONTROLLER,
    )

    # Establishing connection via links
    connections = [
        (switch[1], host[1]), (switch[1], switch[3]), (switch[1], switch[2]),
        (switch[2], host[2]), (switch[2], switch[3]), (switch[2], switch[4]),
        (switch[3], host[3]), (switch[3], host[4]), (switch[3], switch[4]),
        (switch[4], host[5]), (switch[4], host[6]), (switch[4], host[7]),
    ]
    link = {}
    for i, item in enumerate(connections):
        link[i] = net.addLink(item[0], item[1], cls=TCLink, bw=BANDWIDTH[0], loss=0)


    net.build()
    controller.start()
    for _, item in switch.items():
        item.start([controller])

    CLI(net)
    end = True
    e_random_bw.set()
    with lock:
        print "net is done..."
        net.stop()
    
def random_bandwidth():
    global e_random_bw, lock, end, link
    while True:
        lock.acquire()
        e_random_bw.wait(T_CHBW)
        if end:
            lock.release()
            break
        # TODO: randomly changing the Bandwidth of all Links.
        for _, item in link.items():
            # try:
            #     cmd1, _ = item.intf1.bwCmds(bw=1)
            #     cmd2, _ = item.intf2.bwCmds(bw=1)
            #     outs = [item.intf1.tc(cmd1), item.intf2.tc(cmd2)]
            #     for out in outs:
            #         if out != '':
            #             print " ********************* ERROR: %s"%out
            # except Exception, e:
            #     # lock.release()
            #     print "hhhhhhooooooooshhhaaaaaaaaa ", e
            rnd = random.randint(0, 1)
            item.intf1.config(bw=BANDWIDTH[rnd])
            item.intf2.config(bw=BANDWIDTH[rnd])
        lock.release()
    print "end of random bandwidth..."

if __name__ == '__main__':
    setLogLevel('info')
    e_random_bw = threading.Event()
    t_random_bw = threading.Thread(target=random_bandwidth)
    t_random_bw.start()
    create_topo()