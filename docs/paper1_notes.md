# Paper 1 Draft Notes
# Title: A Lightweight Peer-to-Peer Mesh Communication Protocol 
#        for Infrastructure-Independent Networks

## Status: Early Draft

---

## Abstract (write last)
To be written after all sections are complete.

## 1. Introduction
- Problem: Billions lack internet access
- Current solutions are centralized and fragile  
- We propose: device-to-device mesh communication
- Key contribution: lightweight protocol that works on commodity hardware

## 2. Related Work
Research to read and cite:
- [ ] Delay Tolerant Networks (DTN) papers
- [ ] Disaster.radio project
- [ ] Meshtastic protocol
- [ ] goTenna Mesh
- [ ] Batman-adv routing protocol

## 3. System Design
### 3.1 Node Identity
- Each node generates a UUID on startup
- Future: replace with cryptographic keypair (Ed25519)

### 3.2 Discovery Protocol
- UDP broadcast on local network
- Announcement interval: 5 seconds
- Announcement payload: node_id, name, host, port, peer_count, uptime

### 3.3 Message Format
- Fields: message_id, sender_id, recipient_id, content, timestamp, hop_count
- Duplicate suppression via seen_messages set
- TTL via max_hops field (default: 10)

### 3.4 Relay Logic
- Flooding with duplicate suppression
- Hop count limit prevents infinite loops

## 4. Implementation
- Language: Python 3.11
- Key libraries: asyncio, socket, json
- Platform: tested on Linux (Ubuntu) and macOS

## 5. Evaluation (to be done after testing)
- Metrics: discovery time, message delivery rate, latency
- Test setup: X devices on same WiFi network
- Results: TBD

## 6. Conclusion
TBD

## References
TBD
```

---

## Where We Are Now
```
✅ GitHub repo created with professional README
✅ Codespaces environment set up
✅ Project folder structure in place
✅ First mesh node written and explained line by line
✅ Node discovery via UDP broadcast implemented
✅ Paper 1 outline started

🔜 Next: Message passing between nodes (send/receive text)
🔜 Next: Multi-hop relay (A → B → C)
🔜 Next: File transfer support
🔜 Next: Connect Flutter app to the mesh backend