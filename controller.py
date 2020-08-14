
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.topology import event
from ryu.topology.api import get_all_link, get_all_switch
from ryu.lib.packet import ethernet, ether_types
import copy


switches = []
links = []
sw_topo = []


class Controller(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    sw_update_events = [event.EventSwitchEnter, event.EventSwitchLeave]
    links_update_events = [event.EventLinkAdd, event.EventLinkDelete]

    def __init__(self, *args, **kwargs):
        super(Controller, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=0, command=ofproto.OFPFC_ADD,
                                match=match, instructions=inst)
        datapath.send_msg(mod)


    def update_topology(self):
        global sw_topo, switches, links

        sw_cnt = len(switches)
        tmp_sw_topo = [ [None for i in range(sw_cnt)] for j in range(sw_cnt) ]
        for link in links:
            tmp_sw_topo[link['src_dpid']-1][link['dst_dpid']-1] = link['src_port_no']
            tmp_sw_topo[link['dst_dpid']-1][link['src_dpid']-1] = link['dst_port_no']
        sw_topo = copy.deepcopy(tmp_sw_topo)
        # print(sw_topo)

    
    @set_ev_cls(sw_update_events)
    def _get_all_switches(self, ev):
        global switches
        print( "getting all switches ...")

        switches = get_all_switch(self)
        sw_ids = []
        for sw in switches:
            sw_ids.append(sw.dp.id)
        print( "Switches: " , sw_ids)

        self.update_topology()

    
    @set_ev_cls(links_update_events)
    def _get_all_links(self, ev):
        global links
        print( "getting all links ...")

        tmp = get_all_link(self)
        tmp_links = [
                        {
                            'src_dpid': link.src.dpid,
                            'dst_dpid': link.dst.dpid,
                            'src_port_no': link.src.port_no,
                            'dst_port_no': link.dst.port_no
                        }
                        for link in tmp
                    ]
        links = copy.deepcopy(tmp_links)
        print( "Links: ")
        for link in links:
            print(link)

        self.update_topology()


    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)[0]
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return

        dst = eth.dst
        src = eth.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        stored_src = False
        src_sw_dpid = None
        for sw in switches:
            if src in self.mac_to_port[sw.dp.id]:
                stored_src = True
                src_sw_dpid = sw.dp.id
                break
        if not stored_src:
            self.mac_to_port[dpid][src] = in_port
            src_sw_dpid = dpid
        
        stored_dst = False
        dst_sw_dpid = None
        for sw in switches:
            if dst in self.mac_to_port[sw.dp.id]:
                stored_dst = True
                dst_sw_dpid = sw.dp.id
                break

        if stored_dst:
            path = self.get_dijkstra_path(src, src_sw_dpid, dst, dst_sw_dpid)
            out_port = path[0][2]
            self.install_path(src, dst, path, datapath, 1)
        else:
            out_port = ofproto.OFPP_FLOOD

        # Now tell the switch to send the packet
        actions = [parser.OFPActionOutput(out_port)]
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
           data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)


    def get_dijkstra_path(self, src, src_sw_dpid, dst, dst_sw_dpid):
        # TODO : return a path
        # path format should be: list of (in_port, sw, out_port) tuples
        return

    
    def install_path(self, src, dst, path, datapath, priority):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        print("installing a path from " + str(src), " to " + str(dst))
        for in_port, sw, out_port in path:
            print("in_port: " + str(in_port) + " , switch: " + str(sw) + " , out_port: " + str(out_port))
            match = parser.OFPMatch(in_port=in_port, eth_src=src_mac, eth_dst=dst_mac)
            actions = [parser.OFPActionOutput(out_port)]
            datapath = sw.dp
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS , actions)]
            mod = parser.OFPFlowMod(datapath=datapath, match=match,
                                    priority=priority, instructions=inst)
            datapath.send_msg(mod)

    