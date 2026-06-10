# Networking Skills — Deep Dive

## 1. TCP/IP Stack

The TCP/IP model has 4 layers: Link, Internet, Transport, Application.

### Layer 4: Application
Protocols: HTTP, HTTPS, FTP, SSH, DNS, SMTP, WebSocket, gRPC

### Layer 3: Transport
- **TCP** — connection-oriented, reliable, ordered, flow control, congestion avoidance
- **UDP** — connectionless, unreliable, low-latency, no ordering guarantees
- **QUIC** — built on UDP, multiplexed streams, 0-RTT handshake

### Layer 2: Internet
- IP (IPv4 / IPv6), ICMP, ARP
- Routing via BGP, OSPF

### Layer 1: Link
- Ethernet, Wi-Fi, PPP
- MAC addresses, ARP resolution

### TCP Three-Way Handshake

```
CLIENT                    SERVER
  |  ---- SYN (seq=x) ----> |
  | <-- SYN+ACK (seq=y, ack=x+1) -- |
  |  ---- ACK (ack=y+1) ---> |
```

```
Connection established — data transfer begins
```

### TCP State Diagram

```
CLOSED
   | passive open
   v
LISTEN
   | recv SYN / send SYN+ACK
   v
SYN_RCVD
   | recv ACK
   v
ESTABLISHED
   | application close
   v
FIN_WAIT_1 ---- FIN+ACK --> CLOSE_WAIT
   | ACK                    | application close
   v                        v
FIN_WAIT_2 <-- FIN ------- LAST_ACK
   | ACK                    | ACK
   v                        v
TIME_WAIT                CLOSED
   | timeout
   v
CLOSED
```

### TCP Flow Control — Sliding Window

The receiver advertises a `rwnd` (receive window). The sender cannot send more than `rwnd` bytes without acknowledgment.

```
Sender window:
[ sent & acked | sent & unacked | unsent & within window | unsent & beyond window ]
```

### TCP Congestion Control

| Algorithm | Trigger | Response |
|---|---|---|
| Slow Start | Connection start | Double window per RTT until ssthresh |
| Congestion Avoidance | After ssthresh | Additive increase (1 MSS per RTT) |
| Fast Retransmit | 3 duplicate ACKs | Retransmit lost segment immediately |
| Fast Recovery | After Fast Retransmit | Halve congestion window, enter CA |

### Socket Programming (Python)

```python
# TCP Server
import socket

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(("0.0.0.0", 8080))
server.listen(128)
server.settimeout(5.0)

while True:
    try:
        client, addr = server.accept()
        data = client.recv(4096)
        if data:
            print(f"Received from {addr}: {data.decode()}")
            client.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK")
        client.close()
    except socket.timeout:
        pass
```

```python
# UDP Server
import socket

udp_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_server.bind(("0.0.0.0", 5353))

while True:
    data, addr = udp_server.recvfrom(1024)
    print(f"Received {len(data)} bytes from {addr}")
    udp_server.sendto(b"ACK", addr)
```

## 2. DNS Resolution

### Resolution Flow

```
Browser
  | 1. Check browser cache
  | 2. Check OS cache
  | 3. Check /etc/hosts (or C:\Windows\System32\drivers\etc\hosts)
  | 4. Recursive resolver (ISP or 8.8.8.8)
  |    |
  |    +--> 5. Root server (.) -> returns TLD nameserver
  |    +--> 6. TLD server (.com) -> returns authoritative nameserver
  |    +--> 7. Authoritative server -> returns A or AAAA record
  |
  v
IP address returned
```

### DNS Record Types

| Record | Purpose | Example |
|---|---|---|
| A | IPv4 address | 93.184.216.34 |
| AAAA | IPv6 address | 2606:2800:220:1:248:1893:25c8:1946 |
| CNAME | Canonical name (alias) | www -> example.com |
| MX | Mail exchange | 10 mail.example.com |
| TXT | Arbitrary text | SPF, DKIM, DMARC values |
| NS | Nameserver | ns1.example.com |
| SRV | Service location | _sip._tcp.example.com |
| SOA | Start of authority | zone serial, refresh, retry |

### DNS with dig

```bash
# A record lookup
dig example.com A

# Trace the full resolution path
dig +trace example.com

# Reverse DNS
dig -x 8.8.8.8

# Short answer only
dig +short example.com

# Query specific nameserver
dig @8.8.8.8 example.com

# Check DNSSEC
dig example.com +dnssec
```

### Python DNS Resolution

```python
import socket
import dns.resolver

# Basic resolution
ip = socket.gethostbyname("example.com")
print(f"IPv4: {ip}")

# Resolve all IPs
ips = socket.getaddrinfo("example.com", 80, socket.AF_INET)
for info in ips:
    print(f"Family={info[0]}, Type={info[1]}, IP={info[4][0]}")

# Using dnspython
answers = dns.resolver.resolve("example.com", "MX")
for rdata in answers:
    print(f"Priority {rdata.preference} -> {rdata.exchange}")
```

## 3. HTTP/1.1 vs HTTP/2 vs HTTP/3/QUIC

### HTTP/1.1 (1997)

| Feature | Detail |
|---|---|
| Connections | One request per connection (or pipelining, rarely used) |
| Head-of-line blocking | Yes — one slow response blocks all subsequent |
| Multiplexing | None |
| Header compression | None — plaintext headers every request |
| Server push | None |
| Binary/Text | Text-based |

### HTTP/2 (2015)

| Feature | Detail |
|---|---|
| Connections | Single connection, multiplexed streams |
| Head-of-line blocking | TCP-level only (lost packet blocks all streams) |
| Multiplexing | Yes — multiple streams over one TCP connection |
| Header compression | HPACK (static + dynamic table) |
| Server push | Yes (deprecated in Chrome 106+) |
| Binary/Text | Binary framing layer |
| Stream prioritization | Dependency tree |

### HTTP/3 (2022)

| Feature | Detail |
|---|---|
| Connections | Multiplexed over QUIC (UDP) |
| Head-of-line blocking | Eliminated — lost packet only blocks its stream |
| Multiplexing | Native QUIC streams |
| Header compression | QPACK (separate uni-directional streams) |
| Connection establishment | 0-RTT for returning clients |
| Migration | Connection migration across IP addresses |
| Encryption | Mandatory (TLS 1.3 built into QUIC) |

### HTTP/2 Frame Types

```
+----------------------------------+
| Length (24 bits)                  |
+----------------------------------+
| Type (8 bits)                     |   0 = DATA
+----------------------------------+   1 = HEADERS
| Flags (8 bits)                    |   2 = PRIORITY
+----------------------------------+   4 = SETTINGS
| Stream Identifier (31 bits)      |   8 = GOAWAY
+----------------------------------+   9 = PING
| Frame Payload (variable)         |
+----------------------------------+
```

### Go HTTP/3 Server

```go
package main

import (
    "log"
    "net/http"
    "github.com/quic-go/quic-go/http3"
)

func main() {
    mux := http.NewServeMux()
    mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Alt-Svc", `h3=":443"`)
        w.Write([]byte("Hello from HTTP/3!"))
    })

    err := http3.ListenAndServeQUIC(":443", "/path/to/cert.pem",
        "/path/to/key.pem", mux)
    if err != nil {
        log.Fatal(err)
    }
}
```

### HTTP/2 Server (Node.js)

```javascript
const http2 = require('http2');
const fs = require('fs');

const server = http2.createSecureServer({
    key: fs.readFileSync('server.key'),
    cert: fs.readFileSync('server.crt')
});

server.on('stream', (stream, headers) => {
    const path = headers[':path'];
    stream.respond({
        'content-type': 'text/plain',
        ':status': 200
    });
    stream.end(`Served ${path} via HTTP/2`);
});

server.listen(443);
```

## 4. WebSockets

Full-duplex communication over a single TCP connection.

### Handshake

```
CLIENT -> SERVER:
GET /ws HTTP/1.1
Host: example.com
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
Sec-WebSocket-Version: 13

SERVER -> CLIENT:
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
```

### WebSocket Data Frame

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|F|R|R|R| opcode|M| Payload len |    Extended payload length    |
|I|S|S|S|  (4)  |A|     (7)     |             (16/64)           |
|N|V|V|V|       |S|             |   if payload len == 126/127  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|     Extended payload length continued     | Masking-key (if MASK set) |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          Masking-key (continued)          |    Payload Data         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

| Opcode | Type |
|---|---|
| 0x0 | Continuation frame |
| 0x1 | Text frame |
| 0x2 | Binary frame |
| 0x8 | Connection close |
| 0x9 | Ping |
| 0xA | Pong |

### Python WebSocket Server

```python
import asyncio
import websockets
import json

connected = set()

async def handler(websocket, path=None):
    connected.add(websocket)
    try:
        async for message in websocket:
            data = json.loads(message)
            broadcast = {
                "sender": id(websocket),
                "data": data["text"]
            }
            websockets.broadcast(connected, json.dumps(broadcast))
    finally:
        connected.remove(websocket)

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        await asyncio.Future()  # run forever

asyncio.run(main())
```

### JS Client

```javascript
const ws = new WebSocket("wss://example.com/ws");

ws.onopen = () => {
    ws.send(JSON.stringify({ text: "Hello server" }));
};

ws.onmessage = (event) => {
    console.log("Received:", event.data);
};

ws.onclose = () => {
    console.log("Connection closed");
};

// Ping/pong keepalive
setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "ping" }));
    }
}, 30000);
```

## 5. gRPC

High-performance RPC framework using Protocol Buffers and HTTP/2.

### Service Definition (protobuf)

```protobuf
syntax = "proto3";

service UserService {
    rpc GetUser (GetUserRequest) returns (User);
    rpc ListUsers (ListUsersRequest) returns (stream User);
    rpc UpdateUser (stream UpdateUserRequest) returns (User);
    rpc Chat (stream ChatMessage) returns (stream ChatMessage);
}

message GetUserRequest {
    string user_id = 1;
}

message User {
    string id = 1;
    string name = 2;
    string email = 3;
    int64 created_at = 4;
}

message ChatMessage {
    string room_id = 1;
    string user_id = 2;
    string text = 3;
    int64 timestamp = 4;
}
```

### gRPC Service Patterns

| Pattern | Client | Server | Use Case |
|---|---|---|---|
| Unary | Single request | Single response | Standard RPC |
| Server streaming | Single request | Stream of responses | Real-time feed |
| Client streaming | Stream of requests | Single response | File upload, batch |
| Bidirectional streaming | Stream of requests | Stream of responses | Chat, real-time game |

### Python gRPC Server

```python
import grpc
from concurrent import futures
import user_pb2
import user_pb2_grpc

class UserService(user_pb2_grpc.UserServiceServicer):
    def GetUser(self, request, context):
        return user_pb2.User(
            id=request.user_id,
            name="Alice",
            email="alice@example.com",
            created_at=1700000000
        )

    def ListUsers(self, request, context):
        users = [
            user_pb2.User(id="1", name="Alice", email="alice@example.com", created_at=1700000000),
            user_pb2.User(id="2", name="Bob", email="bob@example.com", created_at=1700000001),
        ]
        for user in users:
            yield user

    def Chat(self, request_iterator, context):
        for req in request_iterator:
            yield user_pb2.ChatMessage(
                room_id=req.room_id,
                user_id=req.user_id,
                text=f"Echo: {req.text}",
                timestamp=req.timestamp
            )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    user_pb2_grpc.add_UserServiceServicer_to_server(UserService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()
```

### Go gRPC Client

```go
package main

import (
    "context"
    "log"
    "time"
    "google.golang.org/grpc"
    "google.golang.org/grpc/credentials/insecure"
    pb "path/to/protobuf"
)

func main() {
    conn, err := grpc.NewClient("localhost:50051",
        grpc.WithTransportCredentials(insecure.NewCredentials()))
    if err != nil {
        log.Fatal(err)
    }
    defer conn.Close()

    client := pb.NewUserServiceClient(conn)
    ctx, cancel := context.WithTimeout(context.Background(), time.Second)
    defer cancel()

    user, err := client.GetUser(ctx, &pb.GetUserRequest{UserId: "1"})
    if err != nil {
        log.Fatal(err)
    }
    log.Printf("User: %s <%s>", user.Name, user.Email)
}
```

### Interceptors (Middleware)

```python
import grpc
import time

class LoggingInterceptor(grpc.ServerInterceptor):
    def intercept_service(self, continuation, handler_call_details):
        start = time.time()
        try:
            return continuation(handler_call_details)
        finally:
            duration = time.time() - start
            method = handler_call_details.method
            print(f"[gRPC] {method} took {duration*1000:.2f}ms")
```

## 6. REST vs GraphQL

| Aspect | REST | GraphQL |
|---|---|---|
| Data fetching | Fixed response shape per endpoint | Client specifies exact fields |
| Over/under-fetching | Common | Eliminated |
| Versioning | URL versioning (/v1/users) | Evolve schema, deprecate fields |
| Number of requests | May need N requests for N resources | Single request for many resources |
| Caching | HTTP caching (ETag, Cache-Control) | Requires custom caching layer |
| Tooling | cURL, Postman, browser native | GraphiQL, Apollo DevTools |
| Schema | Implicit (documentation) | Explicit (SDL) |
| Learning curve | Lower | Higher |
| N+1 problem | Client-side | Server-side (needs batching) |

### GraphQL Schema Definition

```graphql
type Query {
    user(id: ID!): User
    users(limit: Int, offset: Int): [User!]!
    searchPosts(query: String!): [Post!]!
}

type Mutation {
    createUser(input: CreateUserInput!): User!
    updateProfile(input: UpdateProfileInput!): Profile!
    deletePost(id: ID!): Boolean!
}

type Subscription {
    messageAdded(roomId: ID!): Message!
    notificationReceived: Notification!
}

type User {
    id: ID!
    name: String!
    email: String!
    profile: Profile
    posts(limit: Int = 10): [Post!]!
}

type Post {
    id: ID!
    title: String!
    body: String!
    author: User!
    comments: [Comment!]!
    createdAt: DateTime!
}

input CreateUserInput {
    name: String!
    email: String!
    password: String!
}
```

### GraphQL Server (Python — Strawberry)

```python
import strawberry
from typing import Optional

@strawberry.type
class User:
    id: strawberry.ID
    name: str
    email: str

@strawberry.input
class CreateUserInput:
    name: str
    email: str
    password: str

@strawberry.type
class Query:
    @strawberry.field
    def user(self, id: strawberry.ID) -> Optional[User]:
        return User(id=id, name="Alice", email="alice@example.com")

    @strawberry.field
    def users(self, limit: int = 10, offset: int = 0) -> list[User]:
        return [User(id="1", name="Alice", email="a@ex.com")]

@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_user(self, input: CreateUserInput) -> User:
        return User(id="new-id", name=input.name, email=input.email)

schema = strawberry.Schema(query=Query, mutation=Mutation)
```

### Solving N+1 with DataLoader

```python
from promise import Promise
from promise.dataloader import DataLoader

class UserLoader(DataLoader):
    def batch_load_fn(self, keys):
        users = db.query(User).filter(User.id.in_(keys)).all()
        user_map = {str(u.id): u for u in users}
        return Promise.resolve([user_map.get(str(k)) for k in keys])

# In resolver:
@strawberry.field
def author(self, root) -> User:
    return user_loader.load(root.author_id)
```

## 7. Load Balancing Algorithms

| Algorithm | How It Works | Best For | Caveats |
|---|---|---|---|
| Round Robin | Sequential distribution | Equal-capacity servers | Ignores load |
| Least Connections | Pick server with fewest active connections | Variable request duration | Connection tracking overhead |
| IP Hash | Hash(client IP) % N -> server | Session persistence | Uneven distribution on small N |
| Weighted Round Robin | Servers have weights, proportional distribution | Heterogeneous capacity | Static weights |
| Least Response Time | Pick server with lowest latency | Latency-sensitive apps | Requires continuous metrics |
| Random | Random selection | Stateless services | Unpredictable distribution |
| Consistent Hashing | Hash ring with virtual nodes | Cache affinity, sharding | Complexity |

### Nginx Load Balancing Config

```nginx
upstream backend {
    least_conn;
    # or ip_hash, random, etc.
    server 10.0.1.1:8080 weight=3;
    server 10.0.1.2:8080 weight=2;
    server 10.0.1.3:8080 backup;
    keepalive 64;
}

server {
    listen 80;
    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Consistent Hashing (Python)

```python
import hashlib
import bisect

class ConsistentHashRing:
    def __init__(self, nodes=None, virtual_nodes=150):
        self.virtual_nodes = virtual_nodes
        self.ring = {}
        self.sorted_keys = []
        if nodes:
            for node in nodes:
                self.add_node(node)

    def _hash(self, key):
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def add_node(self, node):
        for i in range(self.virtual_nodes):
            virtual_key = f"{node}:{i}"
            hash_val = self._hash(virtual_key)
            self.ring[hash_val] = node
            bisect.insort(self.sorted_keys, hash_val)

    def remove_node(self, node):
        for i in range(self.virtual_nodes):
            virtual_key = f"{node}:{i}"
            hash_val = self._hash(virtual_key)
            del self.ring[hash_val]
            self.sorted_keys.remove(hash_val)

    def get_node(self, key):
        if not self.ring:
            return None
        hash_val = self._hash(key)
        idx = bisect.bisect_right(self.sorted_keys, hash_val)
        if idx == len(self.sorted_keys):
            idx = 0
        return self.ring[self.sorted_keys[idx]]

# Usage
ring = ConsistentHashRing(["node1", "node2", "node3"])
server = ring.get_node("user_12345")
```

## 8. API Gateways

An API gateway is a reverse proxy that sits between clients and backend services.

### Responsibilities

| Concern | Description |
|---|---|
| Routing | Route requests to correct backend service |
| Authentication | Validate JWT, API keys, OAuth tokens |
| Rate limiting | Throttle by IP, user, endpoint |
| Caching | Cache responses at gateway level |
| Load balancing | Distribute across service instances |
| Circuit breaking | Fail fast when backend is degraded |
| Request/response transformation | Modify headers, bodies |
| Protocol translation | REST -> gRPC, HTTP -> WebSocket |
| Aggregation | Combine multiple service responses |
| Canary/blue-green | Route percentage of traffic |
| Logging & monitoring | Structured logging, metrics |

### Kong Gateway Config (Declarative)

```yaml
_format_version: "3.0"
services:
  - name: user-service
    url: http://user-svc:8080
    routes:
      - name: user-routes
        paths:
          - /api/users
        methods: [GET, POST, PUT, DELETE]
    plugins:
      - name: rate-limiting
        config:
          minute: 60
          hour: 1000
          policy: local
      - name: jwt
        config:
          claims_to_verify:
            - exp
            - nbf
      - name: cors
        config:
          origins: ["*"]
          methods: ["GET", "POST", "PUT", "DELETE"]
          headers: ["Authorization", "Content-Type"]
```

### Custom API Gateway (Go — Minimal)

```go
package main

import (
    "net/http"
    "net/http/httputil"
    "net/url"
    "strings"
)

type Gateway struct {
    services map[string]*httputil.ReverseProxy
}

func NewGateway() *Gateway {
    return &Gateway{
        services: map[string]*httputil.ReverseProxy{
            "users": mustNewProxy("http://user-svc:8080"),
            "orders": mustNewProxy("http://order-svc:8081"),
            "payments": mustNewProxy("http://payment-svc:8082"),
        },
    }
}

func (g *Gateway) ServeHTTP(w http.ResponseWriter, r *http.Request) {
    prefix := strings.Split(strings.TrimPrefix(r.URL.Path, "/api/"), "/")[0]
    if proxy, ok := g.services[prefix]; ok {
        r.URL.Path = strings.TrimPrefix(r.URL.Path, "/api/"+prefix)
        proxy.ServeHTTP(w, r)
        return
    }
    http.NotFound(w, r)
}

func mustNewProxy(target string) *httputil.ReverseProxy {
    u, _ := url.Parse(target)
    return httputil.NewSingleHostReverseProxy(u)
}
```

## 9. CDN Architecture

### How a CDN Works

```
User
  |
  | DNS resolves to CDN edge (via CNAME)
  v
CDN Edge (Point of Presence)
  |--- Cache hit? Serve from edge cache
  |--- Cache miss? Forward to origin server
  v
Origin Server (your backend)
```

### CDN Components

| Component | Role |
|---|---|
| Points of Presence (PoPs) | Globally distributed edge servers |
| Reverse proxy | Accept end-user requests |
| Cache storage | RAM, SSD, or disk-based content storage |
| Origin shield | Layer between edge and origin to reduce load |
| DNS resolver | Geo-aware DNS routing |
| Load balancer | Distribute across edge servers in PoP |
| SSL termination | TLS at edge, re-encrypt to origin |
| WAF | Web application firewall |
| DDoS protection | Absorb volumetric attacks |
| Purge API | Invalidates cached content |

### Cache Control Headers

```http
# Static assets — cache aggressively
Cache-Control: public, max-age=31536000, immutable

# HTML — short cache, revalidate
Cache-Control: public, max-age=60, must-revalidate

# API responses — no cache or short TTL
Cache-Control: no-cache
# OR
Cache-Control: private, max-age=10

# Set expiry manually (for old proxies)
Expires: Wed, 21 Oct 2026 07:28:00 GMT

# Surrogate keys for tag-based purging
Surrogate-Key: user:123 article:456
```

### Cache Invalidation Strategies

| Strategy | Mechanism | Latency |
|---|---|---|
| TTL expiry | Content auto-expires | Passive |
| Purge by URL | Remove specific URL | Immediate |
| Purge by tag | Remove all tagged content | Immediate |
| Purge by regex | Remove matching patterns | Immediate |
| Versioned URLs | /static/main.v2.js | Zero cost |
| Cache busting query | /style.css?v=123 | Zero cost |

### Python: Programmatic Cache Invalidation

```python
import requests
import time

class CDNManager:
    def __init__(self, api_token, base_url):
        self.api_token = api_token
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_token}"}

    def purge_url(self, url: str):
        resp = requests.post(
            f"{self.base_url}/cache/purge",
            json={"urls": [url]},
            headers=self.headers
        )
        resp.raise_for_status()
        return resp.json()

    def purge_tag(self, tag: str):
        resp = requests.post(
            f"{self.base_url}/cache/purge",
            json={"tags": [tag]},
            headers=self.headers
        )
        resp.raise_for_status()
        return resp.json()

    def purge_all(self):
        resp = requests.post(
            f"{self.base_url}/cache/purge_all",
            headers=self.headers
        )
        resp.raise_for_status()

    def add_surrogate_key(self, response, tags: list[str]):
        response.headers["Surrogate-Key"] = " ".join(tags)
        return response
```

## 10. SSL/TLS Handshake

### TLS 1.3 Handshake (1-RTT)

```
CLIENT                                    SERVER
  | ---- ClientHello -------------------> |
  |     (TLS version, cipher suites,      |
  |      key share, random)               |
  |                                       |
  | <-- ServerHello -------------------- |
  |     (chosen cipher, key share, cert)  |
  |                                       |
  | <-- {Finished} --------------------- |
  |     (encrypted handshake messages)    |
  |                                       |
  | ---- {Finished, application data} --> |
  |     (encrypted)                       |
  |                                       |
  ======== Secure communication ==========
```

### TLS 1.3 0-RTT (for returning clients)

```
CLIENT                                    SERVER
  | ---- ClientHello -------------------> |
  |     (early data — already encrypted!) |
  |                                       |
  | <-- ServerHello -------------------- |
  | <-- {Finished} --------------------- |
  |                                       |
  | ---- {Finished} --------------------> |
  |                                       |
  ======== Secure communication ==========
```

### Cipher Suites

```
# TLS 1.3 (simplified)
TLS_AES_128_GCM_SHA256
TLS_AES_256_GCM_SHA384
TLS_CHACHA20_POLY1305_SHA256

# TLS 1.2
TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256
TLS_DHE_RSA_WITH_AES_128_GCM_SHA256
```

### Certificate Chain

```
Root CA (self-signed, trusted by OS)
  └── Intermediate CA (signed by Root)
       └── Leaf/Server Certificate (signed by Intermediate)
            - CN: example.com
            - SAN: example.com, www.example.com, api.example.com
            - Validity: notBefore, notAfter
            - Key Usage: Digital Signature, Key Encipherment
            - Extended Key Usage: Server Authentication
```

### TLS Best Practices (Nginx)

```nginx
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;

    ssl_certificate     /etc/ssl/certs/example.com.pem;
    ssl_certificate_key /etc/ssl/private/example.com.key;

    # Protocols
    ssl_protocols TLSv1.2 TLSv1.3;

    # Cipher suites
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305;

    # Prefer server cipher order
    ssl_prefer_server_ciphers on;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000" always;

    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;

    # Session caching
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;
}
```

### Python: SSL Context Configuration

```python
import ssl
import socket

context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
context.minimum_version = ssl.TLSVersion.TLSv1_2
context.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20")
context.load_verify_locations("ca-certificates.crt")
context.check_hostname = True
context.verify_mode = ssl.CERT_REQUIRED

# Connect
with socket.create_connection(("example.com", 443)) as sock:
    with context.wrap_socket(sock, server_hostname="example.com") as tls:
        tls.sendall(b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
        data = tls.read()
        print(tls.version())  # TLSv1.3
```

## 11. mTLS (Mutual TLS)

Both parties present certificates to each other.

### mTLS Flow

```
CLIENT (presents cert)                  SERVER (presents cert)
  |                                        |
  | ---- ClientHello ------------------> |
  | <-- ServerHello + ServerCert ------ |
  | ---- ClientCertificate -----------> |
  | ---- CertificateVerify ------------> |
  | <-- {Finished} -------------------- |
  | ---- {Finished} ------------------> |
  |                                        |
  ======== Both authenticated =============
```

### Go: mTLS Server

```go
package main

import (
    "crypto/tls"
    "crypto/x509"
    "log"
    "net/http"
    "os"
)

func main() {
    caCert, _ := os.ReadFile("ca-cert.pem")
    caPool := x509.NewCertPool()
    caPool.AppendCertsFromPEM(caCert)

    tlsConfig := &tls.Config{
        ClientAuth: tls.RequireAndVerifyClientCert,
        ClientCAs:  caPool,
        MinVersion: tls.VersionTLS12,
    }

    server := &http.Server{
        Addr:      ":8443",
        TLSConfig: tlsConfig,
        Handler:   http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            cert := r.TLS.PeerCertificates[0]
            w.Write([]byte("Authenticated: " + cert.Subject.CommonName))
        }),
    }

    log.Fatal(server.ListenAndServeTLS("server-cert.pem", "server-key.pem"))
}
```

### Go: mTLS Client

```go
package main

import (
    "crypto/tls"
    "crypto/x509"
    "log"
    "net/http"
    "os"
)

func main() {
    caCert, _ := os.ReadFile("ca-cert.pem")
    caPool := x509.NewCertPool()
    caPool.AppendCertsFromPEM(caCert)

    clientCert, _ := tls.LoadX509KeyPair("client-cert.pem", "client-key.pem")

    client := &http.Client{
        Transport: &http.Transport{
            TLSClientConfig: &tls.Config{
                RootCAs:      caPool,
                Certificates: []tls.Certificate{clientCert},
                MinVersion:   tls.VersionTLS12,
            },
        },
    }

    resp, _ := client.Get("https://server:8443/")
    log.Println(resp.Status)
}
```

### Kubernetes: mTLS with Istio

```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: prod
spec:
  mtls:
    mode: STRICT  # STRICT, PERMISSIVE, DISABLE
---
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: require-mtls
spec:
  selector:
    matchLabels:
      app: payment-service
  action: ALLOW
  rules:
    - from:
        - source:
            principals: ["cluster.local/ns/prod/sa/user-service"]
```

## 12. Zero Trust Networking

**Never trust, always verify.** No implicit trust based on network location.

### Zero Trust Principles

| Principle | Description |
|---|---|
| Verify explicitly | Always authenticate and authorize based on all data points |
| Least privilege | Minimum access required, JIT (just-in-time) |
| Assume breach | Segment access, encrypt all traffic, monitor continuously |
| Micro-segmentation | Isolate workloads at granular level |
| Device trust | Verify device posture before granting access |
| Identity-based access | Access bound to user/service identity, not IP |
| Encrypt everything | All traffic encrypted regardless of network |

### BeyondCorp / Google's Zero Trust

```
User -> Device (managed?)
    -> Identity (authenticated?)
    -> Context (location, time, sensitivity)
    -> Policy Engine (allow/deny)
    -> Application
```

### Zero Trust with OAuth2 + mTLS

```yaml
# Token exchange pattern
1. Client authenticates with IdP (OAuth 2.0)
2. Client receives access token + client certificate
3. Client connects to service with mTLS + token
4. Service validates:
   - TLS certificate (device identity)
   - JWT token (user identity)
   - Authorization policies
5. Service proxies request with its own identity
```

### WireGuard (VPN alternative for ZT)

```ini
# /etc/wireguard/wg0.conf
[Interface]
PrivateKey = client-private-key
Address = 10.0.0.2/24
DNS = 1.1.1.1

[Peer]
PublicKey = server-public-key
Endpoint = vpn.example.com:51820
AllowedIPs = 10.0.0.0/24, 192.168.1.0/24
PersistentKeepalive = 25
```

### OAuth 2.0 Device Authorization Grant

```python
import requests

# Step 1: Request device code
resp = requests.post("https://idp.example.com/device/code", data={
    "client_id": "my-app",
    "scope": "openid profile email"
})
device = resp.json()
# {"device_code": "...", "user_code": "ABCD-1234", "verification_uri": "..."}

# Step 2: User visits URL and enters code (out of band)
print(f"Visit {device['verification_uri']} and enter {device['user_code']}")

# Step 3: Poll for token
while True:
    resp = requests.post("https://idp.example.com/token", data={
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "device_code": device["device_code"],
        "client_id": "my-app"
    })
    if resp.status_code == 200:
        token = resp.json()
        print(f"Access token: {token['access_token']}")
        break
    elif resp.json()["error"] == "authorization_pending":
        time.sleep(device["interval"])
```

### SPIRE (SPIFFE) — Workload Identity

```yaml
# Registration entry for a workload
entries:
  - spiffe_id: "spiffe://example.org/payment-service"
    parent_id: "spiffe://example.org/k8s/node"
    selector:
      - type: "k8s"
        value: "ns:prod"
      - type: "k8s"
        value: "sa:payment-sa"
    x509_svid_ttl: "1h"
    jwt_svid_ttl: "1h"
```

### Network Policy (Kubernetes — Zero Trust)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-allow-frontend-only
spec:
  podSelector:
    matchLabels:
      app: api-service
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
    - from:
        - namespaceSelector:
            matchLabels:
              name: monitoring
      ports:
        - protocol: TCP
          port: 9090
```

### OPA/Rego Policy Example

```rego
package zero_trust

default allow = false

allow {
    input.method == "GET"
    input.path == "/api/users"
    input.user.role == "admin"
    input.device.encrypted == true
    input.device.os_version >= 12.0
    time.clock(input.request_time) >= 9
    time.clock(input.request_time) <= 17
}

allow {
    input.service == "payment"
    input.client.spiffe_id == "spiffe://example.org/order-service"
    input.client.mtls == true
    input.token.exp - input.token.iat < 3600
}
```

## Performance & Debugging Tools

```bash
# tcpdump — capture traffic
tcpdump -i eth0 -w capture.pcap host example.com and port 443

# tcpdump — read with protocol decode
tcpdump -r capture.pcap -X -vv

# ss — socket statistics
ss -tulpn
ss -ti  # TCP info (cwnd, rtt, etc.)

# netstat (Windows)
netstat -ano | findstr :443

# traceroute
traceroute -n example.com

# mtr — continuous traceroute with statistics
mtr example.com

# curl with timing
curl -w "DNS: %{time_namelookup}s, TCP: %{time_connect}s, TLS: %{time_appconnect}s, Total: %{time_total}s\n" -so /dev/null https://example.com

# nmap — port scanning
nmap -sV -sC example.com

# openssl — inspect certificate
openssl s_client -connect example.com:443 -servername example.com -tlsextdebug
openssl x509 -in cert.pem -text -noout

# dig for DNS timing
dig example.com +stats

# httpie (modern curl alternative)
http https://api.example.com/users Authorization:"Bearer token"

# wrk — HTTP benchmarking
wrk -t12 -c400 -d30s https://example.com/api

# h2load — HTTP/2 benchmarking
h2load -n1000 -c100 https://example.com
```

## Common Issues & Troubleshooting

| Problem | Symptom | Likely Cause | Fix |
|---|---|---|---|
| High latency | Slow page loads | DNS resolution, TLS negotiation, or TCP congestion | Check DNS TTL, enable OCSP stapling, tune TCP buffers |
| Connection resets | "Connection reset by peer" | Firewall, reverse proxy timeout, or TCP RST | Check iptables/nftables, increase proxy timeouts |
| TLS handshake failure | SSL_ERROR_BAD_CERT_ALERT | Certificate expired, hostname mismatch, or weak cipher | Renew cert, check SANs, update cipher config |
| WebSocket drops | Intermittent disconnects | Proxy not configured for WebSocket, idle timeout | Add Upgrade/Connection headers, increase idle timeout |
| gRPC deadline exceeded | Streams timing out | Backend overloaded, no keepalive configured | Add keepalive pings, increase deadline |
| HTTP/2 stream reset | Random failures | Server or client hitting stream limits | Increase max concurrent streams setting |

```python
# Quick connectivity test
import socket, ssl, sys

def test_endpoint(host, port=443):
    print(f"Testing {host}:{port}...")

    # DNS
    try:
        ip = socket.gethostbyname(host)
        print(f"  DNS OK -> {ip}")
    except socket.gaierror as e:
        print(f"  DNS FAIL: {e}")
        return False

    # TCP connect
    try:
        sock = socket.create_connection((host, port), timeout=5)
        print(f"  TCP OK")
    except Exception as e:
        print(f"  TCP FAIL: {e}")
        return False

    # TLS
    try:
        ctx = ssl.create_default_context()
        tls = ctx.wrap_socket(sock, server_hostname=host)
        print(f"  TLS OK ({tls.version()})")
        tls.close()
    except Exception as e:
        print(f"  TLS FAIL: {e}")
        sock.close()
        return False

    return True

if __name__ == "__main__":
    for host in sys.argv[1:]:
        test_endpoint(host)
```
