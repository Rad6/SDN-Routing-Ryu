from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSKernelSwitch, \
    UserSwitch, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import Link, TCLink

def create_topo():
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
        ip='127.0.0.1',
        port=9967,
    )

    # Establishing connection via links
    connections = [
        (switch[1], host[1]), (switch[1], switch[3]), (switch[1], switch[2]),
        (switch[2], host[2]), (switch[2], switch[3]), (switch[2], switch[4]),
        (switch[3], host[3]), (switch[3], host[4]), (switch[3], switch[4]),
        (switch[4], host[5]), (switch[4], host[6]), (switch[4], host[7]),
    ]
    bandwidth = (5, 1)
    for item in connections:
        net.addLink(item[0], item[1], bw=bandwidth[0], loss=0)
    

    net.build()
    controller.start()
    for _, item in switch.items():
        item.start([controller])

    CLI(net)
    net.stop()
    
if __name__ == '__main__':
    setLogLevel('info')
    create_topo()