from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, arp, ipv4

class StaticRoutingController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.info("Static Routing Controller Started")

        # Topology port mapping:
        # S1: port1=h1, port2=h2, port3=s2
        # S2: port1=s1, port2=h3, port3=h4

        self.static_routes = {
            (1, '10.0.0.1'): 1,  # s1 -> h1
            (1, '10.0.0.2'): 2,  # s1 -> h2
            (1, '10.0.0.3'): 3,  # s1 -> s2 -> h3
            (1, '10.0.0.4'): 3,  # s1 -> s2 -> h4
            (2, '10.0.0.1'): 1,  # s2 -> s1 -> h1
            (2, '10.0.0.2'): 1,  # s2 -> s1 -> h2
            (2, '10.0.0.3'): 2,  # s2 -> h3
            (2, '10.0.0.4'): 3,  # s2 -> h4
        }

        # MAC table for ARP handling
        self.mac_to_port = {}

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(
            ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=inst
        )
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        self.logger.info(f"Switch connected: S{dpid}")

        # Default rule: send unknown packets to controller
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(
            ofproto.OFPP_CONTROLLER,
            ofproto.OFPCML_NO_BUFFER
        )]
        self.add_flow(datapath, 0, match, actions)

        # Install static IP routing rules
        for (switch_id, dst_ip), out_port in self.static_routes.items():
            if switch_id != dpid:
                continue
            match = parser.OFPMatch(eth_type=0x0800, ipv4_dst=dst_ip)
            actions = [parser.OFPActionOutput(out_port)]
            self.add_flow(datapath, 10, match, actions)
            self.logger.info(
                f"[S{dpid}] Flow installed: dst={dst_ip} -> port {out_port}"
            )

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.id

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth is None:
            return

        dst_mac = eth.dst
        src_mac = eth.src

        # Learn MAC -> port mapping
        if dpid not in self.mac_to_port:
            self.mac_to_port[dpid] = {}
        self.mac_to_port[dpid][src_mac] = in_port

        # Handle ARP
        if eth.ethertype == 0x0806:
            if dst_mac in self.mac_to_port[dpid]:
                out_port = self.mac_to_port[dpid][dst_mac]
            else:
                out_port = ofproto.OFPP_FLOOD

            actions = [parser.OFPActionOutput(out_port)]
            out = parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=msg.buffer_id,
                in_port=in_port,
                actions=actions,
                data=msg.data
            )
            datapath.send_msg(out)
            self.logger.info(
                f"[S{dpid}] ARP {'flooded' if out_port == ofproto.OFPP_FLOOD else f'sent to port {out_port}'}"
            )
            return

        # For IP packets not matched by flow rules, drop
        self.logger.info(
            f"[S{dpid}] Unmatched IP packet from {src_mac} to {dst_mac} on port {in_port}"
        )

