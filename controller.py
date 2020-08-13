
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.topology import event
from ryu.topology.api import get_switch, get_link
import copy


switches = []
links = []
sw_topo = []


class Controller(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Controller, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
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


    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        # TODO: add dijsktra's paths to flow table or flood
        pass

    
    def update_topology(self):
        # TODO : update network topology graph
        pass


    sw_update_events = [event.EventSwitchEnter,
                        event.EventSwitchLeave]
    @set_ev_cls(sw_update_events)
    def get_all_switches(self, ev):

        global switches
        print( "getting all switches ...")

        tmp = get_switch(self, None)
        tmp_switches = [switch.dp.id for switch in tmp]
        switches = copy.deepcopy(tmp_switches)
        print( "Switches: ", switches)

        self.update_topology()


    links_update_events = [event.EventLinkAdd,
                        event.EventLinkDelete]
    @set_ev_cls(links_update_events)
    def get_all_links(self, ev):

        global links
        print( "getting all links ...")

        tmp = get_link(self, None)
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