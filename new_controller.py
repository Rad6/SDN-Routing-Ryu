# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ryu.base import app_manager
from ryu.controller import mac_to_port
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib import mac

from ryu.topology.api import get_switch, get_link
from ryu.app.wsgi import ControllerBase
from ryu.topology import event, switches
from collections import defaultdict

#switches
switches = []

#mymac[srcmac]->(switch, port)
mymac={}

#adjacency map [sw1][sw2]->port from sw1 to sw2
adjacency=defaultdict(lambda:defaultdict(lambda:None))

# a function that finds and returns the Q element which
# has the minimum distance value in distance list
def minimum_distance(distance, Q):
    min = float('Inf') # initializing min
    tmp = list(Q)
    node = tmp[0] # # initializing node
    for v in Q:
        if distance[v] <= min:
            min = distance[v]
            node = v
    return node

 
 # Dijkstra's algorithm,
 # given the source and destination switches and input ports 
 # to them from host, it will find you a dijkstra minimal path 
 # which has the following return format:
 # List of (switch dpid, switch in-port, switch out-port)
def get_path (src,dst,first_port,final_port):
    #Dijkstra's algorithm
    print( "get_path is called, src=",src," dst=",dst, " first_port=", first_port, " final_port=", final_port)
    distance = {}
    previous = {}

    for dpid in switches:
        # initialize all distances to Inf
        distance[dpid] = float('Inf')
        # initialize all previous nodes to None
        previous[dpid] = None

    # source node distance should be 0
    distance[src]=0
    Q=set(switches)
    # print( "Q=", Q)

    while len(Q)>0: # untill Q is empty
        # removing an element from Q which has minimum distance
        u = minimum_distance(distance, Q)
        Q.remove(u)   
        for p in switches:
            # check whether p and u are connected or not
            if adjacency[u][p]!=None:
                # assuming all nodes have same weight = 1
                w = 1
                # if the path from source to p and then from p to u is 
                # cheaper than from source to u, then it gets updated
                if distance[u] + w < distance[p]:
                    distance[p] = distance[u] + w
                    previous[p] = u

    r=[] # a list for path's switches
    p=dst
    r.append(p)
    q=previous[p]
    # starting form the end and adding previous nodes of the path to it
    while q is not None:
        if q == src:
            r.append(q)
            break
        p=q
        r.append(p)
        # current node goes one step back
        q=previous[p]

    # while the path is reversed, we need to reverse it again to get it right
    r.reverse()
    if src==dst:
        path=[src]
    else:
        path=r

    # Now add the ports
    r = []
    in_port = first_port
    # getting paths switched in 2 by 2 tuples
    for s1,s2 in zip(path[:-1],path[1:]):
        out_port = adjacency[s1][s2]
        r.append((s1,in_port,out_port))
        # updating out_port for the next iteration
        in_port = adjacency[s2][s1]
    # while the last route which leads to the dst host is
    # not included in the loop above, we add it separately
    r.append((dst,in_port,final_port))
    return r

# The controller class. 
# Must be inherited from the base Ryu app class 'app_manager.RyuApp'
# So that it will be run using ryu-manager command
class ProjectController(app_manager.RyuApp):
    # OpenFlow protocol for this app is set to v1.3
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(ProjectController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.topology_api_app = self # not really necessary
        self.datapath_list=[] # a list for storing all switches datapath pbjects


    # Handy function that lists all attributes in the given object
    def ls(self,obj):
        print(("\n".join([x for x in dir(obj) if x[0] != "_"])))


    # The function bellow is not used at all
    # add_flow functionality has been implemented directly in 
    # switch_features_handler and install_path functions.

    # def add_flow(self, datapath, in_port, dst, actions):
    #     ofproto = datapath.ofproto
    #     parser = datapath.ofproto_parser      
    #     match = datapath.ofproto_parser.OFPMatch(in_port=in_port, eth_dst=dst)
    #     inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)] 
    #     mod = datapath.ofproto_parser.OFPFlowMod(
    #         datapath=datapath, match=match, cookie=0,
    #         command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0,
    #         priority=ofproto.OFP_DEFAULT_PRIORITY, instructions=inst)
    #     datapath.send_msg(mod)


    # installs the the entire path which is generated by get_path function
    # on each switch included on the path
    def install_path(self, p, ev, src_mac, dst_mac):
        print( "\n\ninstall_path is called")
        print( "p=", p, " src_mac=", src_mac, " dst_mac=", dst_mac)
        msg = ev.msg # The OpenFlow message included in the event object
        datapath = msg.datapath # datapath representing the switch currently
                                # connected to the controller
        ofproto = datapath.ofproto # Referencing  the library for the chosen 
                                # version of the OpenFlow protocol used in 
                                # communicating between the OpenFlow elements
        parser = datapath.ofproto_parser # Referencing the message parsing library
                                        # used in our OpenFlow protocol version
        
        # iterating through all tuples contained in the path list, and installing them
        for sw, in_port, out_port in p:
            #print( src_mac,"->", dst_mac, "via ", sw, " in_port=", in_port, " out_port=", out_port)
            # A match object for the corresponding switch to be applied on its flow-table entry
            match=parser.OFPMatch(in_port=in_port, eth_src=src_mac, eth_dst=dst_mac)
            # an action object to tell the flow-table what to do next, when entry is matched.
            actions=[parser.OFPActionOutput(out_port)]
            # finding datapath object for the switch with dpid = sw
            for item in self.datapath_list:
                if item.id == sw:
                    datapath = item
            # datapath=self.datapath_list[int(sw)-1] # wrong !
            # creating an instruction object which consists of an action + a mode. here we use apply mode.
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS , actions)]
            # creating a FlowMod object to make the switch modify its flow table. while the given path 
            # is a one leading to dst, we use priority = 1, which is higher than table miss priority.
            mod = datapath.ofproto_parser.OFPFlowMod(
            datapath=datapath, match=match, idle_timeout=0, hard_timeout=0,
            priority=1, instructions=inst)
            # Finally sending the FLowMod object to the switch
            datapath.send_msg(mod)

 
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures , CONFIG_DISPATCHER)
    def switch_features_handler(self , ev):
        print( "switch_features_handler is called")
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = datapath.ofproto_parser.OFPFlowMod(
        datapath=datapath, match=match, cookie=0,
        command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0,
        priority=0, instructions=inst)
        datapath.send_msg(mod)

 
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        #print( "eth.ethertype=", eth.ethertype)

        #avodi broadcast from LLDP
        if eth.ethertype==35020:
            return

        dst = eth.dst
        src = eth.src
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        if src not in mymac.keys():
            mymac[src]=( dpid,  in_port)
            #print( "mymac=", mymac)

        if dst in mymac.keys():
            p = get_path(mymac[src][0], mymac[dst][0], mymac[src][1], mymac[dst][1])
            # print( p)
            self.install_path(p, ev, src, dst)
            out_port = p[0][2]
        else:
            out_port = ofproto.OFPP_FLOOD
        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        # TODO: --------------- UNUSED
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_src=src, eth_dst=dst)

        data=None
        if msg.buffer_id==ofproto.OFP_NO_BUFFER:
            data=msg.data
 
        out = parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port,
            actions=actions, data=data)
        datapath.send_msg(out)

    events = [event.EventSwitchEnter,
            event.EventSwitchLeave, event.EventPortAdd,
            event.EventPortDelete, event.EventPortModify,
            event.EventLinkAdd, event.EventLinkDelete
    ]
    @set_ev_cls(events)
    def get_topology_data(self, ev):
        global switches
        switch_list = get_switch(self.topology_api_app, None)  
        switches=[switch.dp.id for switch in switch_list]
        self.datapath_list=[switch.dp for switch in switch_list]
        #print( "self.datapath_list=", self.datapath_list)
        print( "switches=", switches)

        links_list = get_link(self.topology_api_app, None)
        mylinks=[(link.src.dpid,link.dst.dpid,link.src.port_no,link.dst.port_no) for link in links_list]
        for s1,s2,port1,port2 in mylinks:
            adjacency[s1][s2]=port1
            adjacency[s2][s1]=port2
            #print( s1,s2,port1,port2)