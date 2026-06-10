# System Design — Comprehensive Guide

## 1. Microservices

### Architecture Overview

```
                    ┌──────────┐
                    │  API GW  │
                    └────┬─────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
    ┌─────▼────┐  ┌─────▼────┐  ┌─────▼────┐
    │  User    │  │  Order   │  │ Payment  │
    │ Service  │  │ Service  │  │ Service  │
    └────┬─────┘  └────┬─────┘  └────┬─────┘
         │             │             │
    ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
    │  User   │   │  Order  │   │Payment  │
    │   DB    │   │   DB    │   │   DB    │
    └─────────┘   └─────────┘   └─────────┘
```

### Service Design Principles

| Principle | Description |
|---|---|
| Single Responsibility | One service, one bounded context |
| Database per service | Each service owns its data store |
| Loose coupling | Services communicate via APIs/events, not shared code |
| High cohesion | Related behavior stays together |
| Smart endpoints, dumb pipes | Logic in services, transport is thin |
| Decentralized governance | Each team chooses its own tech stack |
| Infrastructure automation | CI/CD, containers, orchestration |
| Design for failure | Circuit breakers, retries, fallbacks |

### Service Boundaries (Bounded Contexts)

```
Domain: E-commerce
├── Product Catalog    (products, categories, inventory)
├── User Management    (accounts, auth, profiles)
├── Order Processing   (cart, orders, fulfillment)
├── Payment            (transactions, refunds, billing)
├── Notification       (email, SMS, push)
├── Shipping           (rates, labels, tracking)
└── Recommendation     (personalization, ML models)
```

### Inter-Service Communication

#### Synchronous (HTTP/gRPC)

```python
# HTTP call with circuit breaker
import requests
from pybreaker import CircuitBreaker

breaker = CircuitBreaker(fail_max=5, reset_timeout=30)

@breaker
def get_user(user_id: str) -> dict:
    resp = requests.get(
        f"http://user-service:8080/api/users/{user_id}",
        timeout=5,
        headers={"X-Request-ID": generate_request_id()}
    )
    resp.raise_for_status()
    return resp.json()

# Fallback
def get_user_safe(user_id: str):
    try:
        return get_user(user_id)
    except Exception:
        return get_cached_user(user_id)
```

#### Asynchronous (Events/Message Queue)

```python
# Publisher (Order Service)
import json
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers=['kafka:9092'],
    value_serializer=lambda v: json.dumps(v).encode()
)

def create_order(order_data):
    order = save_order_to_db(order_data)
    producer.send('order.evt', {
        'event': 'order.created',
        'order_id': str(order.id),
        'user_id': order.user_id,
        'total': order.total,
        'timestamp': datetime.utcnow().isoformat()
    })
    return order
```

```python
# Consumer (Notification Service)
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    'order.evt',
    bootstrap_servers=['kafka:9092'],
    group_id='notification-service',
    value_deserializer=lambda m: json.loads(m.decode())
)

for message in consumer:
    event = message.value
    if event['event'] == 'order.created':
        send_confirmation_email(event['user_id'], event['order_id'])
    elif event['event'] == 'order.shipped':
        send_shipping_update(event['user_id'], event['order_id'])
```

### Service Discovery

```yaml
# Consul service registration
service:
  name: "user-service"
  port: 8080
  tags: ["api", "v1"]
  check:
    http: "http://localhost:8080/health"
    interval: "10s"
    timeout: "2s"
```

```python
# Python service discovery via DNS
import socket

def discover_service(service_name):
    _, _, ip_list = socket.gethostbyname_ex(f"{service_name}.service.consul")
    return ip_list

# Or via Consul HTTP API
import requests

def get_service_endpoints(service_name):
    resp = requests.get(
        f"http://consul:8500/v1/health/service/{service_name}?passing=true"
    )
    resp.raise_for_status()
    services = resp.json()
    endpoints = []
    for s in services:
        addr = s['Service']['Address']
        port = s['Service']['Port']
        endpoints.append(f"{addr}:{port}")
    return endpoints
```

## 2. Event-Driven Architecture, CQRS & Event Sourcing

### Event-Driven Architecture

```
Service A ──emits──> Event Bus ──consumed──> Service B
                      (Kafka)                  (Notification)
                         │
                         └───────── consumed──> Service C
                                                  (Analytics)
```

### Event Types

| Type | Description | Example |
|---|---|---|
| Domain Event | Something significant happened | OrderPlaced, PaymentReceived |
| Command | Request to perform action | CreateOrder, RefundPayment |
| Query | Request for data | GetOrderById, SearchProducts |
| Event Notification | Something happened, check for details | "order.created" |

### Event Sourcing

Instead of storing current state, store all events and derive state by replaying them.

```
Events stream:
[AccountCreated] -> [Deposited(100)] -> [Withdrew(30)] -> [Deposited(50)]

Current balance = 100 - 30 + 50 = 120
```

```python
# Event Store implementation
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
import json

@dataclass
class Event:
    aggregate_id: str
    event_type: str
    data: dict
    version: int
    timestamp: datetime = field(default_factory=datetime.utcnow)

class EventStore:
    def __init__(self):
        self._events: dict[str, list[Event]] = {}

    def append(self, aggregate_id: str, events: list[Event]):
        if aggregate_id not in self._events:
            self._events[aggregate_id] = []
        self._events[aggregate_id].extend(events)

    def get_events(self, aggregate_id: str) -> list[Event]:
        return self._events.get(aggregate_id, [])

    def replay_all(self, aggregate_id: str) -> dict:
        """Replay events to reconstruct aggregate state."""
        state = {}
        for event in self.get_events(aggregate_id):
            state = self._apply(state, event)
        return state

    def _apply(self, state: dict, event: Event) -> dict:
        if event.event_type == "AccountCreated":
            state["account_id"] = event.data["account_id"]
            state["owner"] = event.data["owner"]
            state["balance"] = 0
        elif event.event_type == "Deposited":
            state["balance"] += event.data["amount"]
        elif event.event_type == "Withdrew":
            state["balance"] -= event.data["amount"]
        return state
```

### CQRS (Command Query Responsibility Segregation)

```
Command Side (writes)                    Query Side (reads)
┌────────────┐  ┌────────────┐          ┌────────────┐
│  Command   │  │   Event    │          │   Query    │
│  Handler   │──▶   Store    │──────────▶  Handler   │
└────────────┘  └────────────┘          └────────────┘
       │                │                      │
       ▼                ▼                      ▼
┌────────────┐  ┌────────────┐          ┌────────────┐
│  Write DB  │  │ Event Bus  │          │  Read DB   │
└────────────┘  └────────────┘          └────────────┘
                      │                       ▲
                      └─────── Projector ─────┘
```

```python
# Command (write model)
class CreateOrderCommand:
    def __init__(self, user_id: str, items: list[dict]):
        self.user_id = user_id
        self.items = items

class OrderCommandHandler:
    def __init__(self, event_store: EventStore, event_bus: EventBus):
        self.event_store = event_store
        self.event_bus = event_bus

    def handle(self, command: CreateOrderCommand) -> str:
        order_id = str(uuid.uuid4())

        # Validate
        if not command.items:
            raise ValueError("Order must have at least one item")

        # Store events
        events = [
            Event(aggregate_id=order_id, event_type="OrderCreated", data={
                "order_id": order_id,
                "user_id": command.user_id,
                "items": command.items,
            }, version=1),
        ]
        self.event_store.append(order_id, events)

        # Publish
        for event in events:
            self.event_bus.publish("order", event)

        return order_id
```

```python
# Query (read model)
class OrderProjection:
    """Denormalized read model, updated by consuming events."""
    def __init__(self, db_connection):
        self.db = db_connection

    def on_order_created(self, event):
        self.db.execute("""
            INSERT INTO order_summaries (order_id, user_id, item_count, status, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            event.data['order_id'],
            event.data['user_id'],
            len(event.data['items']),
            'pending',
            event.timestamp
        ))

    def get_user_orders(self, user_id: str):
        return self.db.fetchall(
            "SELECT * FROM order_summaries WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,)
        )

    def get_order_detail(self, order_id: str):
        return self.db.fetchone(
            "SELECT * FROM order_summaries WHERE order_id = %s",
            (order_id,)
        )
```

## 3. Saga Pattern

Managing distributed transactions across microservices.

### Choreography-Based Saga

```
Service A: Create Order
    │
    ├── emit: OrderCreated
    │
    ▼
Service B: Reserve Inventory ← consumes OrderCreated
    │
    ├── emit: InventoryReserved  OR  InventoryFailed
    │
    ▼
Service C: Process Payment ← consumes InventoryReserved
    │
    ├── emit: PaymentProcessed  OR  PaymentFailed
    │
    ▼
Service D: Confirm Order ← consumes PaymentProcessed
```

### Orchestration-Based Saga

```
                           Saga Orchestrator
                         ┌──────────────────┐
                         │  OrderSaga       │
                         │  ┌──────────┐   │
                         │  │  Step 1  │   │
                         │  │  Step 2  │   │
                         │  │  Step 3  │   │
                         │  └──────────┘   │
                         └────────┬─────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
    ┌────▼────┐             ┌─────▼────┐             ┌─────▼────┐
    │  Order  │             │Inventory │             │ Payment  │
    │ Service │             │ Service  │             │ Service  │
    └─────────┘             └──────────┘             └──────────┘
```

```python
# Orchestrator
class OrderSagaOrchestrator:
    def __init__(self):
        self.saga_log = []

    def execute(self, order_data: dict):
        saga_id = str(uuid.uuid4())

        try:
            # Step 1: Create Order
            order_id = self.create_order(order_data)
            self.saga_log.append(("order_created", order_id))

            # Step 2: Reserve Inventory
            self.reserve_inventory(order_data['items'])
            self.saga_log.append(("inventory_reserved", order_id))

            # Step 3: Process Payment
            payment_id = self.process_payment(order_data['payment'])
            self.saga_log.append(("payment_processed", payment_id))

            # Step 4: Confirm Order
            self.confirm_order(order_id)
            self.saga_log.append(("order_confirmed", order_id))

            return order_id

        except Exception as e:
            self.compensate(saga_id)
            raise SagaFailedError(str(e))

    def compensate(self, saga_id):
        """Roll back all completed steps in reverse order."""
        for step, entity_id in reversed(self.saga_log):
            try:
                if step == "payment_processed":
                    self.refund_payment(entity_id)
                elif step == "inventory_reserved":
                    self.restore_inventory(entity_id)
                elif step == "order_created":
                    self.cancel_order(entity_id)
            except Exception as e:
                log_error(f"Compensation failed for {step}: {entity_id}", e)
```

```python
# Choreography example — each service publishes events and handles compensation
class InventoryService:
    def handle_order_created(self, event):
        """Try to reserve inventory. If it fails, publish InventoryReservationFailed."""
        try:
            for item in event.data['items']:
                if not self.inventory.check_available(item['product_id'], item['quantity']):
                    raise OutOfStockError(item['product_id'])
                self.inventory.reserve(item['product_id'], item['quantity'])

            self.event_bus.publish("inventory", InventoryEvent(
                type="InventoryReserved",
                order_id=event.data['order_id']
            ))
        except Exception:
            self.event_bus.publish("inventory", InventoryEvent(
                type="InventoryReservationFailed",
                order_id=event.data['order_id']
            ))

    def handle_payment_failed(self, event):
        """Compensate — release the reserved inventory."""
        for item in event.data['items']:
            self.inventory.release(item['product_id'], item['quantity'])
```

## 4. Sharding & Partitioning

### Horizontal Partitioning (Sharding) Strategies

| Strategy | Description | Best For | Cons |
|---|---|---|---|
| Range-based | Partition by key range (e.g., user_id 1-1000 -> shard 1) | Range queries, ordered data | Hot spots, uneven distribution |
| Hash-based | Hash(key) % N shards | Even distribution | Re-sharding costly |
| Consistent Hashing | Hash ring with virtual nodes | Minimal rebalancing on scale | Complexity |
| Directory-based | Lookup table maps key to shard | Flexible mapping | Single point of failure |
| Geo-based | Partition by geographic region | Multi-region apps | Cross-region queries |
| Time-based | Partition by time range (e.g., monthly) | Time-series data | Hot latest partition |

### Consistent Hashing Implementation

```python
import hashlib
import bisect

class ConsistentHash:
    def __init__(self, virtual_nodes=150):
        self.virtual_nodes = virtual_nodes
        self.ring = {}
        self.sorted_keys = []
        self.nodes = set()

    def _hash(self, key: str) -> int:
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def add_node(self, node: str):
        if node in self.nodes:
            return
        self.nodes.add(node)
        for i in range(self.virtual_nodes):
            vnode_key = f"{node}:{i}"
            hash_val = self._hash(vnode_key)
            self.ring[hash_val] = node
            bisect.insort(self.sorted_keys, hash_val)

    def remove_node(self, node: str):
        if node not in self.nodes:
            return
        self.nodes.remove(node)
        for i in range(self.virtual_nodes):
            vnode_key = f"{node}:{i}"
            hash_val = self._hash(vnode_key)
            del self.ring[hash_val]
            self.sorted_keys.remove(hash_val)

    def get_node(self, key: str) -> str:
        if not self.ring:
            return None
        hash_val = self._hash(key)
        idx = bisect.bisect_right(self.sorted_keys, hash_val)
        if idx == len(self.sorted_keys):
            idx = 0
        return self.ring[self.sorted_keys[idx]]

# Usage
ring = ConsistentHash(virtual_nodes=200)
ring.add_node("shard1.example.com")
ring.add_node("shard2.example.com")
ring.add_node("shard3.example.com")

node = ring.get_node("user_12345")
print(f"user_12345 -> {node}")
```

### Re-sharding Strategy

```python
class ShardManager:
    def __init__(self):
        self.shards = {}
        self.config_version = 1

    def add_shard(self, shard_id: str, capacity: int = 1000):
        self.shards[shard_id] = {
            'capacity': capacity,
            'load': 0,
            'ranges': []
        }

    def rebalance(self, threshold: float = 0.8):
        """Rebalance when any shard exceeds threshold."""
        overloaded = [s for s, info in self.shards.items()
                      if info['load'] / info['capacity'] > threshold]

        if not overloaded:
            return

        # Find underloaded shards
        underloaded = [s for s, info in self.shards.items()
                       if info['load'] / info['capacity'] < 0.5]

        # Move ranges from overloaded to underloaded
        for overloaded_shard in overloaded:
            if not underloaded:
                # Add new shard instead
                new_shard = self.add_shard(f"shard-{len(self.shards)+1}")
                underloaded.append(new_shard)

            target = underloaded.pop(0)
            self.migrate_ranges(overloaded_shard, target)
            self.config_version += 1
            self.notify_clients()

    def migrate_ranges(self, source: str, target: str):
        """Move some key ranges from source to target."""
        ranges = self.shards[source]['ranges']
        if len(ranges) > 1:
            # Move half of the ranges
            mid = len(ranges) // 2
            moved = ranges[:mid]
            self.shards[source]['ranges'] = ranges[mid:]
            self.shards[target]['ranges'] = moved
```

## 5. Caching Strategies

### Caching Patterns

| Pattern | How It Works | Use Case |
|---|---|---|
| Cache Aside | App checks cache, on miss loads from DB and writes to cache | General purpose |
| Read-Through | Cache layer loads from DB on miss automatically | DB-backed caches |
| Write-Through | Every write goes to cache first, then DB | Consistency-critical |
| Write-Behind | Writes go to cache, async flush to DB | High write throughput |
| Refresh-Ahead | Cache proactively refreshes before expiry | Predictable access patterns |

### Cache Aside (Python)

```python
import redis
import json

cache = redis.Redis(host='localhost', port=6379, db=0)
TTL = 3600  # 1 hour

def get_user(user_id: str) -> dict:
    cache_key = f"user:{user_id}"

    # Try cache first
    cached = cache.get(cache_key)
    if cached is not None:
        return json.loads(cached)

    # Cache miss — load from DB
    user = db.fetch_one("SELECT * FROM users WHERE id = %s", (user_id,))
    if user is None:
        return None

    # Write to cache
    cache.setex(cache_key, TTL, json.dumps(user))
    return user

def update_user(user_id: str, data: dict):
    # Update DB
    db.execute("UPDATE users SET name = %s WHERE id = %s",
               (data['name'], user_id))

    # Invalidate cache
    cache.delete(f"user:{user_id}")
```

### Cache Eviction Policies

| Policy | Description | Best For |
|---|---|---|
| LRU (Least Recently Used) | Evict oldest accessed item | General workloads |
| LFU (Least Frequently Used) | Evict least accessed item | Content with popularity skew |
| FIFO | Evict oldest item by insertion time | Time-series data |
| TTL | Expire after fixed time | Stale-data tolerant apps |
| Random | Random eviction | Simplicity, uniform access |

### Multi-Level Cache

```python
class MultiLevelCache:
    def __init__(self):
        self.l1 = {}           # In-memory dict (fast, small)
        self.l2 = redis.Redis() # Redis (fast, larger)
        self.l1_max = 100

    def get(self, key: str):
        # L1 (memory)
        if key in self.l1:
            return self.l1[key]

        # L2 (Redis)
        val = self.l2.get(key)
        if val is not None:
            self._add_to_l1(key, val)
            return val

        return None

    def set(self, key: str, value, ttl: int = 300):
        self._add_to_l1(key, value)
        self.l2.setex(key, ttl, value)

    def _add_to_l1(self, key: str, value):
        if len(self.l1) >= self.l1_max:
            # Evict random key from L1
            self.l1.pop(next(iter(self.l1)))
        self.l1[key] = value
```

### Cache Stampede Prevention

```python
import random

def get_popular_article(article_id: str) -> dict:
    cache_key = f"article:{article_id}"

    # Try cache
    cached = cache.get(cache_key)
    if cached is not None:
        return json.loads(cached)

    # Lock to prevent stampede
    lock_key = f"lock:{cache_key}"
    if cache.setnx(lock_key, "1"):
        cache.expire(lock_key, 5)  # Auto-release

        try:
            # Compute value
            article = db.fetch_article(article_id)
            # Add jitter to TTL to prevent mass expiry
            jitter = random.uniform(0.8, 1.2)
            cache.setex(cache_key, int(3600 * jitter), json.dumps(article))
            return article
        finally:
            cache.delete(lock_key)
    else:
        # Wait and retry
        import time
        time.sleep(0.1)
        return get_popular_article(article_id)
```

## 6. Message Queues

### Kafka vs RabbitMQ

| Feature | Kafka | RabbitMQ |
|---|---|---|
| Architecture | Distributed commit log | Message broker (AMQP) |
| Message model | Pull-based, offset tracking | Push-based, consumer ack |
| Ordering | Per-partition guaranteed | Per-queue (with single consumer) |
| Throughput | Millions/sec | Thousands/sec |
| Persistence | Disk by default, configurable retention | In-memory or disk |
| Routing | Topic-based, consumer groups | Exchanges (direct, topic, fanout, headers) |
| Message retention | Configurable (time/size) | Deleted after ack |
| Use case | Event streaming, log aggregation | Task queues, RPC |
| Rebalancing | Automatic on consumer join/leave | Manual or HA queues |
| Latency | ~5ms (tunable) | <1ms |

### Kafka Producer/Consumer (Python)

```python
# Producer
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=['kafka1:9092', 'kafka2:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    acks='all',                     # Wait for all replicas
    compression_type='gzip',        # Compress messages
    batch_size=16384,               # Batch before sending
    linger_ms=10,                   # Wait up to 10ms for batch
)

# Send with callback
def on_send_success(record_metadata):
    print(f"Sent to {record_metadata.topic}:{record_metadata.partition}:{record_metadata.offset}")

def on_send_error(excp):
    print(f"Failed to send: {excp}")

producer.send(
    'user-events',
    {'user_id': 123, 'action': 'login'},
    partition=123 % 6  # Manual partitioning
).add_callback(on_send_success).add_errback(on_send_error)

producer.flush()
```

```python
# Consumer
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'user-events',
    bootstrap_servers=['kafka1:9092'],
    group_id='analytics-service',
    auto_offset_reset='earliest',
    enable_auto_commit=False,  # Manual commit for exactly-once
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    max_poll_records=100,
    session_timeout_ms=30000,
)

def process_batch(messages):
    for message in messages:
        event = message.value
        process_event(event)

    consumer.commit()  # Commit after successful processing

while True:
    messages = consumer.poll(timeout_ms=1000)
    for topic_partition, batch in messages.items():
        try:
            process_batch(batch)
        except Exception as e:
            log_error(f"Failed to process batch: {e}")
            # Don't commit — messages will be replayed
```

### RabbitMQ (Python)

```python
# Producer
import pika
import json

connection = pika.BlockingConnection(
    pika.ConnectionParameters('rabbitmq.example.com')
)
channel = connection.channel()

# Declare exchange and queue
channel.exchange_declare(exchange='orders', exchange_type='topic')
channel.queue_declare(queue='order.created', durable=True)
channel.queue_bind(exchange='orders', queue='order.created', routing_key='order.created')

# Publish
channel.basic_publish(
    exchange='orders',
    routing_key='order.created',
    body=json.dumps({'order_id': 123, 'total': 49.99}),
    properties=pika.BasicProperties(
        delivery_mode=2,  # Persistent
        content_type='application/json',
        priority=5,
    )
)
connection.close()
```

```python
# Consumer
import pika

def callback(ch, method, properties, body):
    try:
        process_order(json.loads(body))
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        log_error(f"Processing failed: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

connection = pika.BlockingConnection(
    pika.ConnectionParameters('rabbitmq.example.com')
)
channel = connection.channel()
channel.basic_qos(prefetch_count=1)  # Fair dispatch
channel.basic_consume(queue='order.created', on_message_callback=callback)
channel.start_consuming()
```

## 7. Circuit Breakers

### States

```
CLOSED (normal operation)
    │
    │ failures > threshold
    ▼
OPEN (fast-fail all requests)
    │
    │ timeout elapsed
    ▼
HALF_OPEN (try one request)
    │
    ├── success → CLOSED
    └── failure → OPEN (reset timeout)
```

### Implementation

```python
import time
from enum import Enum
from functools import wraps

class CircuitState(Enum):
    CLOSED = 1
    OPEN = 2
    HALF_OPEN = 3

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=30,
                 half_open_max_requests=3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_requests = half_open_max_requests

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_requests = 0

    def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_requests = 0
            else:
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")

        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_requests >= self.half_open_max_requests:
                raise CircuitBreakerOpenError("Too many half-open requests")
            self.half_open_requests += 1

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.half_open_requests = 0

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

# Decorator
def circuit_breaker(breaker: CircuitBreaker):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator
```

### Usage

```python
payment_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

@circuit_breaker(payment_breaker)
def process_payment(payment_data):
    return requests.post("https://payment-gateway.com/charge",
                        json=payment_data, timeout=10)

# With fallback
def charge_or_fallback(payment_data):
    try:
        return process_payment(payment_data)
    except CircuitBreakerOpenError:
        log_warning("Payment circuit open, using fallback")
        return queue_payment_for_retry(payment_data)
    except Exception as e:
        log_error(f"Payment failed: {e}")
        return {"status": "failed", "error": str(e)}
```

## 8. Distributed Tracing

### Trace Structure

```
Trace (root)
├── Span: handle_request (GET /users/123)
│   ├── Span: authenticate_request
│   │   └── Span: query_db (SELECT * FROM sessions)
│   ├── Span: get_user_from_db
│   │   └── Span: redis_get (cache check)
│   └── Span: call_user_service
│       └── Span: grpc_call (getUserOrders)
│           └── Span: query_orders_db
```

### OpenTelemetry Setup (Python)

```python
# Instrumentation
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

# Set up tracer
provider = TracerProvider()
processor = BatchSpanProcessor(
    OTLPSpanExporter(endpoint="http://jaeger:4317", insecure=True)
)
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

# Auto-instrument libraries
FlaskInstrumentor().instrument()
RequestsInstrumentor().instrument()
Psycopg2Instrumentor().instrument()

# Manual tracing
tracer = trace.get_tracer(__name__)

@app.route('/api/orders/<order_id>')
def get_order(order_id):
    with tracer.start_as_current_span("get_order") as span:
        span.set_attribute("order.id", order_id)
        span.set_attribute("user.id", request.headers.get("X-User-ID"))

        # Nested span
        with tracer.start_as_current_span("query_orders_db") as db_span:
            order = db.fetch_order(order_id)
            db_span.set_attribute("db.system", "postgresql")
            db_span.set_attribute("db.statement", "SELECT * FROM orders WHERE id = ?")

        # Record event
        span.add_event("order_retrieved", {
            "order_id": order_id,
            "timestamp": time.time()
        })

        return jsonify(order)
```

### Context Propagation

```python
# Trace context propagation via HTTP headers
from opentelemetry.propagate import inject, extract

# Outgoing request — inject context
def make_request(url):
    headers = {}
    inject(headers)  # Adds traceparent, tracestate
    return requests.get(url, headers=headers)

# Incoming request — extract context
def handle_request(request):
    ctx = extract(request.headers)
    with tracer.start_as_current_span("handle_request", context=ctx) as span:
        # Process request
        pass
```

### Jaeger Query

```python
# Programmatic trace query via Jaeger API
import requests

def find_traces_with_error(service: str, limit: int = 10):
    resp = requests.get(
        f"http://jaeger:16686/api/traces",
        params={
            "service": service,
            "limit": limit,
            "tags": json.dumps({"error": "true"})
        }
    )
    traces = resp.json()["data"]
    for trace in traces:
        for span in trace["spans"]:
            if span.get("tags", {}).get("error"):
                print(f"Error in {span['operationName']}: "
                      f"{span['logs'][0]['fields'][0]['value']}")
    return traces
```

## 9. CAP Theorem

### The Theorem

A distributed system can guarantee at most two of:

| Property | Meaning |
|---|---|
| **C**onsistency | Every read receives the most recent write or an error |
| **A**vailability | Every request receives a (non-error) response |
| **P**artition tolerance | System continues despite network partitions |

### CAP Trade-offs

```
                    CP (Consistency + Partition)
                    e.g., HBase, Zookeeper, etcd
                        │
                        │
     AP (Availability   │      CA (Consistency + Availability)
     + Partition)       │      e.g., Single-node DB
     e.g., Cassandra,   │      (Partition not tolerated)
     DynamoDB, Riak     │
```

| System | CAP Choice | Rationale |
|---|---|---|
| Cassandra | AP | Eventually consistent, always writable |
| MongoDB | CP (default) | Strong consistency with primary reads |
| DynamoDB | AP | High availability DAX, eventually consistent reads |
| PostgreSQL | CA | Single-master, no partition tolerance |
| etcd | CP | Strongly consistent, unavailable during split |
| Redis Cluster | CP | Strong consistency within partition |
| S3 | AP | Read-after-write consistency since 2020 |

### PACELC Extension

In addition to CAP, trade-off between **L**atency and **C**onsistency when there's no partition:

```
PACELC: If Partition (P) → trade-off A vs C
        Else (E)          → trade-off L vs C
```

## 10. Consensus Algorithms

### Raft

#### States

```
    ┌────────────────┐
    │    FOLLOWER    │
    └────────┬───────┘
             │ election timeout
             ▼
    ┌────────────────┐
    │  CANDIDATE     │
    └────────┬───────┘
             │ majority votes
             ▼
    ┌────────────────┐
    │    LEADER      │  ──heartbeats──> Followers
    └────────────────┘
             │
             └── on Leader failure ──> new election
```

#### Log Replication

```
Client ──Set(x=1)──> Leader
                       │
                       │ Append entry to local log
                       │
                       ├── AppendEntries RPC ──> Follower 1 ──> ACK
                       ├── AppendEntries RPC ──> Follower 2 ──> ACK
                       │
                       │ (majority ACK'd)
                       │
                       │ Commit entry (apply to state machine)
                       │
                       └── Response to client: OK
```

### Python Raft (Minimal)

```python
# Raft Node (conceptual)
import threading
import time
import random
from enum import Enum

class NodeState(Enum):
    FOLLOWER = 1
    CANDIDATE = 2
    LEADER = 3

class RaftNode:
    def __init__(self, node_id: str, peers: list[str]):
        self.node_id = node_id
        self.peers = peers
        self.state = NodeState.FOLLOWER
        self.current_term = 0
        self.voted_for = None
        self.log = []
        self.commit_index = 0
        self.last_applied = 0
        self.election_timeout = random.uniform(150, 300) / 1000
        self.last_heartbeat = time.time()
        self.leader_id = None

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while True:
            if self.state == NodeState.FOLLOWER:
                self._run_follower()
            elif self.state == NodeState.CANDIDATE:
                self._run_candidate()
            elif self.state == NodeState.LEADER:
                self._run_leader()

    def _run_follower(self):
        time.sleep(0.01)
        if time.time() - self.last_heartbeat > self.election_timeout:
            self.state = NodeState.CANDIDATE

    def _run_candidate(self):
        self.current_term += 1
        self.voted_for = self.node_id
        self.last_heartbeat = time.time()

        # Request votes from peers
        votes_received = 1  # Vote for self
        for peer in self.peers:
            if self._request_vote(peer):
                votes_received += 1

        if votes_received > len(self.peers) // 2:
            self.state = NodeState.LEADER
            self.leader_id = self.node_id
        else:
            self.state = NodeState.FOLLOWER
            self.election_timeout = random.uniform(150, 300) / 1000

    def _run_leader(self):
        self._send_heartbeats()
        time.sleep(0.05)  # 50ms heartbeat interval

    def _request_vote(self, peer: str) -> bool:
        # RPC to peer asking for vote
        # Returns True if vote granted
        return True  # Simplified

    def _send_heartbeats(self):
        for peer in self.peers:
            self._append_entries(peer, leader_commit=self.commit_index)

    def _append_entries(self, peer: str, entries=None, leader_commit: int = 0):
        # RPC to replicate log entries
        pass

    def append_to_log(self, command: dict):
        if self.state != NodeState.LEADER:
            return self._redirect_to_leader(command)

        entry = {
            'term': self.current_term,
            'command': command,
            'index': len(self.log)
        }
        self.log.append(entry)

        # Wait for majority replication
        # Commit and apply to state machine
        return True

    def _redirect_to_leader(self, command):
        if self.leader_id:
            # Forward to leader
            pass
        return None

    def receive_heartbeat(self, term: int, leader_id: str):
        if term >= self.current_term:
            self.current_term = term
            self.state = NodeState.FOLLOWER
            self.leader_id = leader_id
            self.last_heartbeat = time.time()
```

### Paxos (Simplified)

```
Phase 1: Prepare
    Proposer ──Prepare(n)──> Acceptors (promise to reject < n)
    Proposer <──Promise(n, last_accepted)── Acceptors

Phase 2: Accept
    Proposer ──Accept(n, value)──> Acceptors
    Proposer <──Accepted(n)──────> Acceptors (majority = chosen)

Learn
    Proposer ──Chosen(value)──> Learners
```

## 11. Additional Patterns

### Idempotency Keys

```python
import hashlib

def process_order_with_idempotency(request, idempotency_key: str):
    """Ensure the request is processed exactly once."""

    # Check if already processed
    existing = cache.get(f"idempotency:{idempotency_key}")
    if existing:
        return json.loads(existing)  # Return previous result

    # Process the request
    result = process_order(request)

    # Store result
    cache.setex(f"idempotency:{idempotency_key}", 86400, json.dumps(result))
    return result

# Idempotency key generation
def generate_idempotency_key(request) -> str:
    content = f"{request.method}:{request.path}:{request.body}"
    return hashlib.sha256(content.encode()).hexdigest()
```

### Outbox Pattern

```python
# Guarantee at-least-once event delivery without 2PC
def create_order(order_data):
    # 1. Save order + outbox message in same DB transaction
    with db.transaction():
        order_id = db.execute("INSERT INTO orders ... RETURNING id")
        db.execute("""
            INSERT INTO outbox (aggregate_type, aggregate_id, event_type, payload)
            VALUES (%s, %s, %s, %s)
        """, ('order', order_id, 'order.created', json.dumps(order_data)))

# 2. Outbox relay (separate process)
def relay_outbox():
    while True:
        messages = db.fetch("""
            SELECT * FROM outbox
            WHERE processed_at IS NULL
            ORDER BY created_at ASC
            LIMIT 100
            FOR UPDATE SKIP LOCKED
        """)

        for msg in messages:
            try:
                kafka_producer.send(msg['event_type'], msg['payload'])
                db.execute("UPDATE outbox SET processed_at = NOW() WHERE id = %s", (msg['id'],))
            except Exception as e:
                log_error(f"Failed to relay message {msg['id']}: {e}")

        time.sleep(1)
```

### Bulkhead Pattern

```python
from concurrent.futures import ThreadPoolExecutor
import threading

class Bulkhead:
    """Isolate thread pools for different services."""

    def __init__(self):
        self.executors = {
            'payment': ThreadPoolExecutor(max_workers=5),
            'inventory': ThreadPoolExecutor(max_workers=10),
            'email': ThreadPoolExecutor(max_workers=3),
            'default': ThreadPoolExecutor(max_workers=20),
        }
        self.semaphores = {
            'payment': threading.Semaphore(5),
            'inventory': threading.Semaphore(10),
        }

    def execute(self, service: str, func, *args, **kwargs):
        sem = self.semaphores.get(service)
        if sem and not sem.acquire(blocking=False):
            raise BulkheadFullError(f"{service} bulkhead is full")

        try:
            executor = self.executors.get(service, self.executors['default'])
            future = executor.submit(func, *args, **kwargs)
            return future.result(timeout=30)
        finally:
            if sem:
                sem.release()
```

### Rate Limiting (Sliding Window)

```python
import time
import redis

class SlidingWindowRateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        now = int(time.time() * 1000)  # milliseconds
        window_start = now - window_seconds * 1000

        # Remove old entries
        self.redis.zremrangebyscore(f"ratelimit:{key}", 0, window_start)

        # Count current requests
        current = self.redis.zcard(f"ratelimit:{key}")

        if current >= max_requests:
            return False

        # Add current request
        self.redis.zadd(f"ratelimit:{key}", {str(now): now})
        self.redis.expire(f"ratelimit:{key}", window_seconds * 2)
        return True
```

## Design Review Checklist

| Concern | Check |
|---|---|
| Scalability | Can it handle 10x traffic? What breaks first? |
| Availability | What's the SLA? Single points of failure? |
| Consistency | Strong or eventual? What stale reads acceptable? |
| Resilience | Are circuit breakers, retries, fallbacks in place? |
| Observability | Metrics, traces, logs — can you debug in prod? |
| Security | Authentication, authorization, encryption, rate limiting |
| Cost | Compute, storage, bandwidth costs at scale |
| Maintainability | Is the system understandable by a new team member? |
| Testability | Can you test at unit, integration, and E2E levels? |
| Deployment | Canary deploys, blue-green, zero-downtime? |
