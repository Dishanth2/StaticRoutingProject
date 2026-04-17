# SDN Static Routing using Mininet + Ryu Controller

## Problem Statement
Implement static routing paths in an SDN network using a Ryu OpenFlow controller.
Flow rules are manually installed by the controller to define fixed paths between hosts,
demonstrating controller-switch interaction, flow rule design (match-action), and network behavior observation.

## Network Topology

```
h1 (10.0.0.1) --- |
                   S1 ---------- S2 --- h3 (10.0.0.3)
h2 (10.0.0.2) --- |  (port 3)  (port 1) |
                                          --- h4 (10.0.0.4)
```

| Switch | Port 1 | Port 2 | Port 3 |
|--------|--------|--------|--------|
| S1     | h1     | h2     | S2     |
| S2     | S1     | h3     | h4     |

- **2 Switches:** s1, s2 (OpenFlow 1.3)
- **4 Hosts:** h1 (10.0.0.1), h2 (10.0.0.2), h3 (10.0.0.3), h4 (10.0.0.4)
- **Controller:** Ryu (Remote, port 6633)
- **Static routes** installed by controller as soon as each switch connects

---

## Setup & Installation

### Requirements
- Ubuntu 20.04+
- Python 3.9
- Mininet
- Ryu Controller

### Step 1 — Install Python 3.9
```bash
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.9 python3.9-venv python3.9-distutils -y
```

### Step 2 — Install Mininet
```bash
sudo apt install mininet -y
sudo mn --version  # verify
```

### Step 3 — Create virtual environment and install Ryu
```bash
python3.9 -m venv ~/ryu-env
source ~/ryu-env/bin/activate
pip install setuptools==45.0.0 wheel==0.37.0
pip install ryu eventlet==0.30.2
ryu-manager --version  # verify
```

---

## Project Structure

```
sdn-static-routing/
├── topology.py                    # Mininet topology (2 switches, 4 hosts)
├── static_routing_controller.py   # Ryu OpenFlow controller
├── README.md                      # This file
└── screenshots/
    ├── 01_pingall.png             # pingall result
    ├── 02_flowtable_s1.png        # Flow table of S1
    ├── 03_flowtable_s2.png        # Flow table of S2
    ├── 04_iperf.png               # iperf throughput
    ├── 05_ping_h1_h3.png          # h1 to h3 ping
    ├── 06_regression_test.png     # Regression test result
    └── 07_ryu_logs.png            # Ryu controller logs
```

---

## How to Run

### Terminal 1 — Start Ryu Controller FIRST
```bash
source ~/ryu-env/bin/activate
cd ~/sdn-project
ryu-manager --ofp-tcp-listen-port 6633 static_routing_controller.py
```

Wait until you see:
```
instantiating app static_routing_controller.py of StaticRoutingController
Static Routing Controller Started
```

### Terminal 2 — Start Mininet
```bash
cd ~/sdn-project
sudo python3 topology.py
```

---

## Testing

### Test 1 — Verify all hosts can reach each other
```bash
# Inside Mininet CLI:
pingall
```
**Expected:** 0% dropped (12/12 received)

### Test 2 — Individual host pings
```bash
h1 ping h3 -c 5
h2 ping h4 -c 5
```
**Expected:** 0% packet loss, ~0.5ms RTT

### Test 3 — Check flow tables
```bash
sh sudo ovs-ofctl -O OpenFlow13 dump-flows s1
sh sudo ovs-ofctl -O OpenFlow13 dump-flows s2
```
**Expected:** Static IP routing rules installed with priority=10

### Test 4 — iperf Throughput
```bash
h3 iperf -s &
h1 iperf -c 10.0.0.3 -t 10
```
**Expected:** Throughput result in Mbits/sec

### Test 5 — Regression Test (path unchanged after rule reinstall)
```bash
sh sudo ovs-ofctl -O OpenFlow13 del-flows s1
sh sudo ovs-ofctl -O OpenFlow13 del-flows s2
sh sleep 4
sh sudo ovs-ofctl -O OpenFlow13 dump-flows s1
h1 ping h3 -c 5
```
**Expected:** Controller reinstalls rules automatically, ping still works

---

## Expected Output

### pingall
```
h1 -> h2 h3 h4
h2 -> h1 h3 h4
h3 -> h1 h2 h4
h4 -> h1 h2 h3
*** Results: 0% dropped (12/12 received)
```

### Flow Table (S1)
```
priority=10,ip,nw_dst=10.0.0.1 actions=output:1
priority=10,ip,nw_dst=10.0.0.2 actions=output:2
priority=10,ip,nw_dst=10.0.0.3 actions=output:3
priority=10,ip,nw_dst=10.0.0.4 actions=output:3
priority=0  actions=CONTROLLER:65535
```

### Ryu Controller Logs
```
Switch connected: S1
[S1] Flow installed: dst=10.0.0.1 -> port 1
[S1] Flow installed: dst=10.0.0.2 -> port 2
[S1] Flow installed: dst=10.0.0.3 -> port 3
[S1] Flow installed: dst=10.0.0.4 -> port 3
Switch connected: S2
[S2] Flow installed: dst=10.0.0.1 -> port 1
[S2] Flow installed: dst=10.0.0.2 -> port 1
[S2] Flow installed: dst=10.0.0.3 -> port 2
[S2] Flow installed: dst=10.0.0.4 -> port 3
```

---

## SDN Flow Rule Design

### Match-Action Logic
| Priority | Match Field | Action |
|----------|-------------|--------|
| 10 | IPv4 dst = 10.0.0.x | Output to specific port |
| 0  | Any (default) | Send to controller |

### Why Static Routing?
- Routes are predefined and do not change dynamically
- Controller installs rules once on switch connect
- Path remains fixed regardless of traffic — validated by regression test
- ARP packets are handled separately via flooding + MAC learning

---

## Performance Observations

| Metric | Tool | Result |
|--------|------|--------|
| Latency | ping | ~0.5ms RTT |
| Throughput | iperf | See screenshots |
| Flow table entries | ovs-ofctl | 5 rules per switch |
| Packet loss | pingall | 0% |

---

## Validation & Regression Testing

**Validation:** `pingall` confirms all 12 host pairs communicate successfully via statically defined routes.

**Regression Test:** Flow rules were manually deleted using `ovs-ofctl del-flows`. The Ryu controller automatically reinstalled all rules within seconds (on switch reconnect), and `h1 ping h3` confirmed the path remained unchanged — same ports, same routing behavior.

---

## References
- [Mininet Official Documentation](http://mininet.org)
- [Ryu SDN Controller Documentation](https://ryu.readthedocs.io/en/latest/)
- [OpenFlow 1.3 Specification](https://opennetworking.org/wp-content/uploads/2014/10/openflow-spec-v1.3.0.pdf)
- [Open vSwitch Documentation](https://docs.openvswitch.org)
- Kurose & Ross, *Computer Networking: A Top-Down Approach*, 8th Edition
