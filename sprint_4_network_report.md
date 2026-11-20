# Sprint 4: CML architecture verification

**Student Name:** Eli Povolny 
**Date:** 2026/9/16
**Course:** CS 457 - Computer Networks  
**Target Server Domain:** `server.povolny.edu`  

### Environment verification:

![CML topology screenshot showing alpine linux nodes ep_Client1 and ep_Client2 connected to ep_Server via router R1](sprint_4_images/topology.png)
*Figure 1: CML topology screenshot showing alpine linux nodes ep_Client1 and ep_Client2 connected to ep_Server via router R1*

![Client 1 ping and nslookup output](sprint_4_images/client_1_logs.png)
*Figure 2: Client 1 ping and nslookup output*

![Client 2 ping and nslookup output](sprint_4_images/client_2_logs.png)
*Figure 3: Client 2 ping and nslookup output*

![Router show ip int br, show ip route, and show ip dhcp binding output](sprint_4_images/router_logs.png)
*Figure 4: Router show ip int br, show ip route, and show ip dhcp binding output*

![Wireshark screenshot of a DNS request for 'server.povolny.edu'](sprint_4_images/DNS_query.png)
*Figure 5: Wireshark screenshot of captured DNS request for the A record for server.povolny.edu*

![Wireshark screenshot of a DNS response for 'server.povolny.edu'](sprint_4_images/DNS_response.png)
*Figure 5: Wireshark screenshot of captured DNS response containing the A record for server.povolny.edu*