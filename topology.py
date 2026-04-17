from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.topo import Topo
from mininet.cli import CLI
from mininet.log import setLogLevel

class StaticTopo(Topo):
    def build(self):
        s1 = self.addSwitch('s1', dpid='0000000000000001')
        s2 = self.addSwitch('s2', dpid='0000000000000002')
        h1 = self.addHost('h1', ip='10.0.0.1/24', mac='00:00:00:00:00:01')
        h2 = self.addHost('h2', ip='10.0.0.2/24', mac='00:00:00:00:00:02')
        h3 = self.addHost('h3', ip='10.0.0.3/24', mac='00:00:00:00:00:03')
        h4 = self.addHost('h4', ip='10.0.0.4/24', mac='00:00:00:00:00:04')
        # s1 ports: 1=h1, 2=h2, 3=s2
        self.addLink(h1, s1, port1=1, port2=1)
        self.addLink(h2, s1, port1=1, port2=2)
        self.addLink(s1, s2, port1=3, port2=1)
        # s2 ports: 1=s1, 2=h3, 3=h4
        self.addLink(h3, s2, port1=1, port2=2)
        self.addLink(h4, s2, port1=1, port2=3)

if __name__ == '__main__':
    setLogLevel('info')
    topo = StaticTopo()
    net = Mininet(
        topo=topo,
        controller=None,
        switch=OVSSwitch
    )
    net.addController(
        'c0',
        controller=RemoteController,
        ip='127.0.0.1',
        port=6633
    )
    net.start()

    # Force OpenFlow 1.3 on both switches
    import os
    os.system('sudo ovs-vsctl set bridge s1 protocols=OpenFlow13')
    os.system('sudo ovs-vsctl set bridge s2 protocols=OpenFlow13')

    CLI(net)
    net.stop()
