# Database Skills — Comprehensive Skill Guide

## Table of Contents
1. PostgreSQL (Indexing, Query Optimization, CTEs, Window Functions, Full-Text Search, Partitioning)
2. MySQL / MariaDB Differences
3. MongoDB (Aggregation Pipeline, Indexing, Schema Design)
4. Redis (Data Structures, Caching Patterns, Pub/Sub, Rate Limiting)
5. SQLite Optimization
6. Database Design (Normalization, Denormalization, ER Diagrams)
7. Migration Strategies (Alembic, Flyway)
8. Connection Pooling
9. Read Replicas
10. Sharding
11. ACID vs BASE
12. CAP Theorem

---

## 1. PostgreSQL

### Indexing Strategies

```sql
-- B-Tree (default) — equality and range queries
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created ON users(created_at DESC);

-- Composite index — column order matters (equality first, then range)
CREATE INDEX idx_users_status_created
  ON users(status, created_at DESC);
-- Best for: WHERE status = 'active' ORDER BY created_at DESC

-- Partial index — only index relevant rows
CREATE INDEX idx_users_active
  ON users(email)
  WHERE is_active = true;
-- Best for: queries that always filter by is_active = true

-- Covering index — includes all needed columns
CREATE INDEX idx_users_list
  ON users(status, created_at DESC)
  INCLUDE (name, email, avatar_url);
-- Best for: SELECT name, email FROM users WHERE status = 'active'

-- Expression index — index function results
CREATE INDEX idx_users_lower_email
  ON users(LOWER(email));
-- Best for: WHERE LOWER(email) = 'tom@example.com'

-- GIN index — for JSONB, arrays, full-text
CREATE INDEX idx_metadata
  ON documents USING GIN (metadata jsonb_path_ops);

-- BRIN index — for large, naturally-ordered tables
CREATE INDEX idx_logs_created
  ON logs USING BRIN (created_at)
  WITH (pages_per_range = 32);
-- Best for: huge append-only tables (logs, events)

-- GiST index — for geometric/range data
CREATE INDEX idx_locations
  ON places USING GIST (coordinates);
```

### Query Optimization

```sql
-- Analyze query plans
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT u.name, COUNT(o.id) as order_count
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
WHERE u.created_at > '2025-01-01'
  AND u.is_active = true
GROUP BY u.id, u.name
HAVING COUNT(o.id) > 5
ORDER BY order_count DESC;

-- Look for:
--   Seq Scan on large tables → needs index
--   Nested Loop with large row estimates → needs JOIN tuning
--   Sort with high memory → needs index or sort reduction
--   "Rows Removed" filters → inefficient filtering

-- Query rewrite patterns
-- Bad: SELECT COUNT(*) FROM (SELECT DISTINCT ...)
-- Good: SELECT COUNT(DISTINCT ...)

-- Bad: WHERE id IN (SELECT user_id FROM ...)
-- Good: WHERE EXISTS (SELECT 1 FROM ... WHERE user_id = users.id)

-- Use LATERAL for complex per-row operations
SELECT u.*, recent_orders.*
FROM users u
CROSS JOIN LATERAL (
  SELECT o.id, o.total, o.created_at
  FROM orders o
  WHERE o.user_id = u.id
  ORDER BY o.created_at DESC
  LIMIT 3
) recent_orders;
```

### CTEs (Common Table Expressions)

```sql
-- Basic CTE
WITH active_users AS (
  SELECT id, name, email
  FROM users
  WHERE is_active = true
    AND last_login > NOW() - INTERVAL '30 days'
),
user_stats AS (
  SELECT
    user_id,
    COUNT(*) as order_count,
    SUM(total) as total_spent
  FROM orders
  WHERE created_at > NOW() - INTERVAL '90 days'
  GROUP BY user_id
)
SELECT
  au.name,
  au.email,
  COALESCE(us.order_count, 0) as orders,
  COALESCE(us.total_spent, 0) as total
FROM active_users au
LEFT JOIN user_stats us ON us.user_id = au.id
ORDER BY total DESC;

-- Recursive CTE (hierarchy traversal)
WITH RECURSIVE org_chart AS (
  -- Base: top-level manager
  SELECT id, name, manager_id, 1 as level
  FROM employees
  WHERE manager_id IS NULL

  UNION ALL

  -- Recursive: direct reports
  SELECT e.id, e.name, e.manager_id, oc.level + 1
  FROM employees e
  INNER JOIN org_chart oc ON e.manager_id = oc.id
)
SELECT * FROM org_chart ORDER BY level, name;

-- Data modification CTE
WITH deleted AS (
  DELETE FROM sessions
  WHERE expires_at < NOW()
  RETURNING user_id, session_data
)
INSERT INTO session_archive (user_id, session_data, deleted_at)
SELECT user_id, session_data, NOW()
FROM deleted;
```

### Window Functions

```sql
-- ROW_NUMBER — deduplication
WITH ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY email
      ORDER BY created_at DESC
    ) as rn
  FROM contacts
)
DELETE FROM contacts
WHERE (email, created_at) IN (
  SELECT email, created_at FROM ranked WHERE rn > 1
);

-- Running totals
SELECT
  date,
  amount,
  SUM(amount) OVER (ORDER BY date) as running_total,
  AVG(amount) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as moving_avg_7d
FROM daily_revenue;

-- Rank and dense rank
SELECT
  name,
  revenue,
  RANK() OVER (ORDER BY revenue DESC) as rank,
  DENSE_RANK() OVER (ORDER BY revenue DESC) as dense_rank,
  NTILE(4) OVER (ORDER BY revenue DESC) as quartile
FROM products
WHERE status = 'active';

-- First/last value in group
SELECT
  user_id,
  order_date,
  amount,
  FIRST_VALUE(amount) OVER (
    PARTITION BY user_id
    ORDER BY order_date
  ) as first_order_amount,
  LAST_VALUE(amount) OVER (
    PARTITION BY user_id
    ORDER BY order_date
    RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
  ) as last_order_amount,
  LAG(amount, 1) OVER (
    PARTITION BY user_id
    ORDER BY order_date
  ) as prev_order_amount
FROM orders;

-- Percent rank and distribution
SELECT
  score,
  PERCENT_RANK() OVER (ORDER BY score) as percentile,
  CUME_DIST() OVER (ORDER BY score) as cumulative_distribution
FROM test_results;
```

### Full-Text Search

```sql
-- Create search index
ALTER TABLE articles ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (
    to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, ''))
  ) STORED;

CREATE INDEX idx_articles_search ON articles USING GIN (search_vector);

-- Search query
SELECT title, excerpt,
  ts_rank(search_vector, query) as relevance
FROM articles, plainto_tsquery('english', 'database indexing optimization') query
WHERE search_vector @@ query
ORDER BY relevance DESC
LIMIT 20;

-- Highlight results
SELECT
  title,
  ts_headline('english', content, query,
    'StartSel = <mark>, StopSel = </mark>,
     MaxWords = 50, MinWords = 30'
  ) as highlighted
FROM articles, plainto_tsquery('english', $search_term) query
WHERE search_vector @@ query
ORDER BY ts_rank(search_vector, query) DESC;
```

### Partitioning

```sql
-- Range partitioning (by date)
CREATE TABLE orders (
  id UUID NOT NULL,
  user_id UUID NOT NULL,
  total DECIMAL(10,2),
  created_at TIMESTAMPTZ NOT NULL
) PARTITION BY RANGE (created_at);

CREATE TABLE orders_2025_q1
  PARTITION OF orders
  FOR VALUES FROM ('2025-01-01') TO ('2025-04-01');

CREATE TABLE orders_2025_q2
  PARTITION OF orders
  FOR VALUES FROM ('2025-04-01') TO ('2025-07-01');

-- List partitioning (by category)
CREATE TABLE events (
  id UUID NOT NULL,
  event_type TEXT NOT NULL,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL
) PARTITION BY LIST (event_type);

CREATE TABLE events_click PARTITION OF events
  FOR VALUES IN ('click', 'dblclick');
CREATE TABLE events_scroll PARTITION OF events
  FOR VALUES IN ('scroll', 'resize');

-- Hash partitioning (for load distribution)
CREATE TABLE user_sessions (
  id UUID NOT NULL,
  user_id UUID NOT NULL,
  session_data JSONB
) PARTITION BY HASH (user_id);

CREATE TABLE user_sessions_p0 PARTITION OF user_sessions
  FOR VALUES WITH (MODULUS 4, REMAINDER 0);
CREATE TABLE user_sessions_p1 PARTITION OF user_sessions
  FOR VALUES WITH (MODULUS 4, REMAINDER 1);
```

---

## 2. MySQL vs MariaDB Differences

| Feature | MySQL 8.x | MariaDB 11.x |
|---------|-----------|--------------|
| JSON | Native JSON type | JSON as LONGTEXT alias |
| Sequences | No (use AUTO_INCREMENT) | Yes (SEQUENCE) |
| CTE | Yes (non-recursive + recursive) | Yes |
| Window functions | Yes (8.0+) | Yes (10.2+) |
| Invisible columns | Yes | Yes |
| CHECK constraints | Yes (8.0.16+) | Yes |
| Full-text parser | Built-in | Built-in + Sphinx |
| Storage engines | InnoDB (default), MyISAM, etc | InnoDB (default), Aria, MyISAM, etc |
| System versioned tables | Yes | Yes (Temporal tables) |
| GIS | Yes | Yes |
| Performance schema | Yes | Yes |
| Group by ASC/DESC | Yes | Yes |
| LATERAL joins | Yes | No (yet) |

---

## 3. MongoDB

### Aggregation Pipeline

```javascript
// Pipeline stages in order
db.orders.aggregate([
  // Stage 1: Filter documents
  { $match: { status: 'completed', total: { $gte: 50 } } },

  // Stage 2: Join with users collection
  {
    $lookup: {
      from: 'users',
      localField: 'user_id',
      foreignField: '_id',
      as: 'user',
    }
  },
  { $unwind: '$user' },

  // Stage 3: Group by user
  {
    $group: {
      _id: '$user.email',
      total_spent: { $sum: '$total' },
      order_count: { $sum: 1 },
      avg_order: { $avg: '$total' },
      first_order: { $min: '$created_at' },
      last_order: { $max: '$created_at' },
      categories: { $addToSet: '$category' },
    }
  },

  // Stage 4: Filter groups
  { $match: { order_count: { $gte: 3 } } },

  // Stage 5: Calculate additional fields
  {
    $addFields: {
      lifetime_value: { $multiply: ['$total_spent', 0.1] },
      customer_segment: {
        $switch: {
          branches: [
            { case: { $gte: ['$total_spent', 10000] }, then: 'VIP' },
            { case: { $gte: ['$total_spent', 5000] }, then: 'Premium' },
          ],
          default: 'Standard',
        }
      }
    }
  },

  // Stage 6: Sort results
  { $sort: { total_spent: -1 } },

  // Stage 7: Paginate
  { $skip: 0 },
  { $limit: 20 },

  // Stage 8: Shape output
  {
    $project: {
      email: '$_id',
      total_spent: 1,
      order_count: 1,
      avg_order: { $round: ['$avg_order', 2] },
      lifetime_value: { $round: ['$lifetime_value', 2] },
      segment: '$customer_segment',
      _id: 0,
    }
  }
]);
```

### MongoDB Indexing

```javascript
// Single field
db.users.createIndex({ email: 1 }, { unique: true });

// Compound — order matters (equality, sort, range)
db.orders.createIndex(
  { user_id: 1, created_at: -1 },
  { name: 'idx_user_created' }
);

// Multikey (arrays)
db.posts.createIndex({ tags: 1 });

// Text index
db.articles.createIndex(
  { title: 'text', content: 'text' },
  { weights: { title: 10, content: 5 }, name: 'idx_text_search' }
);

// Geospatial
db.places.createIndex({ location: '2dsphere' });

// TTL (auto-expire)
db.sessions.createIndex(
  { created_at: 1 },
  { expireAfterSeconds: 86400 }
);

// Partial index
db.users.createIndex(
  { email: 1 },
  { partialFilterExpression: { is_active: true } }
);

// Covered query (all fields in index)
db.users.createIndex(
  { email: 1, name: 1, avatar: 1 },
  { name: 'idx_user_covered' }
);
```

### Schema Design Patterns

```javascript
// 1. Embedded (denormalized) — for one-to-few
const user = {
  _id: ObjectId("..."),
  name: "Tom",
  email: "tom@example.com",
  addresses: [
    { type: "home", street: "123 Main", city: "NYC" },
    { type: "work", street: "456 Wall", city: "NYC" },
  ],
};

// 2. Reference (normalized) — for one-to-many / many-to-many
const user = { _id: ObjectId("..."), name: "Tom" };
const orders = [
  { _id: ObjectId("..."), user_id: ObjectId("..."), total: 100 },
  { _id: ObjectId("..."), user_id: ObjectId("..."), total: 200 },
];

// 3. Bucket pattern — for time-series data
const sensor_readings = {
  sensor_id: "temp-01",
  date: ISODate("2026-05-25"),
  readings: [
    { time: "00:00", value: 22.5 },
    { time: "00:05", value: 22.7 },
    // ... 288 readings per day
  ],
  count: 288,
  avg: 22.6,
};

// 4. Polymorphic pattern
const products = [
  { _id: "...", type: "book", title: "...", author: "...", pages: 300 },
  { _id: "...", type: "electronics", title: "...", brand: "...", warranty: 12 },
];
```

---

## 4. Redis

### Data Structures

```bash
# Strings — caching, counters
SET user:123:name "Tom"
GET user:123:name
SET page:home:views 0
INCR page:home:views
INCRBY page:home:views 5

# Lists — queues, recent items
LPUSH notifications:user:123 "New message"
RPUSH notifications:user:123 "New like"
LPOP notifications:user:123
LRANGE notifications:user:123 0 -1
LLEN notifications:user:123

# Sets — unique items, tags
SADD post:456:tags "database" "redis" "tutorial"
SMEMBERS post:456:tags
SISMEMBER post:456:tags "redis"
SINTER post:456:tags post:789:tags  # Common tags

# Sorted Sets — leaderboards, rate limiting
ZADD leaderboard:daily 100 "user:1"
ZADD leaderboard:daily 85 "user:2"
ZINCRBY leaderboard:daily 10 "user:1"
ZREVRANGE leaderboard:daily 0 9 WITHSCORES
ZRANK leaderboard:daily "user:2"

# Hashes — objects
HSET user:123 name "Tom" email "tom@example.com" age 30
HGET user:123 name
HGETALL user:123
HINCRBY user:123 age 1

# HyperLogLog — unique count estimation
PFADD page:visits:today "ip:1.2.3.4" "ip:5.6.7.8"
PFCOUNT page:visits:today

# Bitmaps — binary features, tracking
SETBIT user:123:days-active 0 1  # Day 0 active
SETBIT user:123:days-active 1 1  # Day 1 active
BITCOUNT user:123:days-active    # Total active days

# Streams — event log, messaging
XADD events * user_id 123 action "login"
XREAD COUNT 10 STREAMS events 0
XRANGE events - +
```

### Caching Patterns

```javascript
// Cache-Aside (lazy loading)
async function getUser(id) {
  const key = `user:${id}`;

  // 1. Try cache
  let user = await redis.get(key);
  if (user) return JSON.parse(user);

  // 2. Miss — load from DB
  user = await db.users.findUnique({ where: { id } });
  if (!user) return null;

  // 3. Populate cache
  await redis.setex(key, 3600, JSON.stringify(user));
  return user;
}

// Write-Through
async function updateUser(id, data) {
  // 1. Update database
  const user = await db.users.update({ where: { id }, data });

  // 2. Update cache (or invalidate)
  await redis.setex(`user:${id}`, 3600, JSON.stringify(user));
  return user;
}

// Cache Invalidation (using Redis pub/sub)
async function invalidateUserCache(userId) {
  await redis.del(`user:${userId}`);
  await redis.publish('cache:invalidate', JSON.stringify({
    type: 'user',
    id: userId,
  }));
}

// Rate Limiting
async function checkRateLimit(userId, limit, windowSec) {
  const key = `ratelimit:${userId}`;
  const current = await redis.incr(key);

  if (current === 1) {
    await redis.expire(key, windowSec);
  }

  return {
    allowed: current <= limit,
    remaining: Math.max(0, limit - current),
    reset: await redis.ttl(key),
  };
}
```

### Pub/Sub

```javascript
// Publisher
async function publishEvent(channel, data) {
  await redis.publish(channel, JSON.stringify(data));
}

// Subscriber
const subscriber = redis.duplicate();
await subscriber.connect();

await subscriber.subscribe('notifications', (message) => {
  const data = JSON.parse(message);
  console.log(`Notification for ${data.userId}: ${data.message}`);
});

await subscriber.subscribe('system:events', (message) => {
  const event = JSON.parse(message);
  handleSystemEvent(event);
});
```

---

## 5. SQLite Optimization

```sql
-- Enable WAL mode (concurrent readers)
PRAGMA journal_mode = WAL;

-- Increase cache size
PRAGMA cache_size = -64000;  -- 64MB

-- Set synchronous mode (balance safety vs speed)
PRAGMA synchronous = NORMAL;  -- Full safety vs fast
-- Use: OFF for bulk imports, FULL for critical data

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- Optimize temp storage
PRAGMA temp_store = MEMORY;

-- Analyze query plans
PRAGMA optimize;

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Use WITHOUT ROWID for lookup tables
CREATE TABLE lookup (
  code TEXT PRIMARY KEY,
  value TEXT NOT NULL
) WITHOUT ROWID;

-- Bulk insert performance
BEGIN TRANSACTION;
INSERT INTO logs VALUES ...;  -- Many rows
COMMIT;
```

---

## 6. Database Design

### Normalization Forms

| Form | Rule | Example Violation |
|------|------|-------------------|
| 1NF | Atomic values, no repeating groups | Column `phone1, phone2, phone3` |
| 2NF | 1NF + all non-key cols depend on full PK | Composite PK with partial dependency |
| 3NF | 2NF + no transitive dependencies | `order → customer_id → customer_name` |
| BCNF | 3NF + every determinant is a candidate key | Overlapping composite keys |

### Denormalization Patterns

```sql
-- When to denormalize:
-- 1. High-read, low-write data (product catalog)
-- 2. Avoid expensive joins (dashboard aggregates)
-- 3. Pre-computed values (order total with line items)

-- Example: denormalized order summary
CREATE TABLE order_summary (
  order_id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  user_name TEXT NOT NULL,  -- Denormalized from users
  item_count INTEGER NOT NULL,
  total_amount DECIMAL(10,2) NOT NULL,
  status TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  full_name TEXT GENERATED ALWAYS AS (
    user_name || ' (' || user_id::text || ')'
  ) STORED  -- Generated column
);
```

### ER Diagrams (Text Notation)

```
USERS ----< ORDERS ----< ORDER_ITEMS >---- PRODUCTS
  |          |
  |          +----< PAYMENTS
  |
  +----< REVIEWS >---- PRODUCTS

USERS
  id (PK, UUID)
  email (UQ, NOT NULL)
  name (NOT NULL)
  created_at (TIMESTAMPTZ, DEFAULT NOW())

ORDERS
  id (PK, UUID)
  user_id (FK -> USERS.id, NOT NULL)
  total (DECIMAL(10,2), NOT NULL)
  status (ENUM: pending, paid, shipped, delivered, cancelled)
  created_at (TIMESTAMPTZ, DEFAULT NOW())

ORDER_ITEMS
  id (PK, UUID)
  order_id (FK -> ORDERS.id, NOT NULL)
  product_id (FK -> PRODUCTS.id, NOT NULL)
  quantity (INT, NOT NULL)
  unit_price (DECIMAL(10,2), NOT NULL)
```

---

## 7. Migration Strategies

### Alembic (Python)

```python
"""alembic/versions/abc123_add_user_preferences.py"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'abc123'
down_revision = 'prev_revision'

def upgrade():
    # Create new table
    op.create_table(
        'user_preferences',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('preferences', postgresql.JSONB(), server_default='{}'),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
    )

    # Add column
    op.add_column('users', sa.Column('timezone', sa.String(50), nullable=True))

    # Backfill data
    op.execute("UPDATE users SET timezone = 'UTC' WHERE timezone IS NULL")

    # Make column NOT NULL after backfill
    op.alter_column('users', 'timezone', nullable=False)

def downgrade():
    op.drop_column('users', 'timezone')
    op.drop_table('user_preferences')
```

### Flyway (Java/SQL)

```sql
-- V2__add_user_preferences.sql
CREATE TABLE user_preferences (
    user_id UUID PRIMARY KEY,
    preferences JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone VARCHAR(50);
UPDATE users SET timezone = 'UTC' WHERE timezone IS NULL;
ALTER TABLE users ALTER COLUMN timezone SET NOT NULL;
```

---

## 8. Connection Pooling

```python
# SQLAlchemy connection pool
from sqlalchemy import create_engine

engine = create_engine(
    'postgresql://user:pass@host:5432/db',
    pool_size=10,             # Connections to keep in pool
    max_overflow=20,          # Extra connections beyond pool_size
    pool_timeout=30,          # Seconds to wait for pool connection
    pool_recycle=1800,        # Recycle connections after 30 min
    pool_pre_ping=True,       # Test connections before using
    max_identifier_length=63,
)

# For serverless / short-lived apps
engine = create_engine(url, poolclass=NullPool)
```

### PgBouncer Configuration

```ini
[databases]
mydb = host=localhost port=5432 dbname=mydb

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt

# Pool modes:
# session — connection returned to pool after session ends
# transaction — returned after transaction (recommended for web apps)
# statement — returned after statement (rarely used)
pool_mode = transaction

default_pool_size = 25
max_client_conn = 100
max_db_connections = 50
reserve_pool_size = 5
reserve_pool_timeout = 5.0

server_idle_timeout = 600
query_timeout = 30
```

---

## 9. Read Replicas

```python
# SQLAlchemy read/write splitting
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

class DatabaseRouter:
    def __init__(self):
        self.write_engine = create_engine(WRITE_DATABASE_URL)
        self.read_engine = create_engine(READ_DATABASE_URL)

    def get_session(self, read_only=False):
        engine = self.read_engine if read_only else self.write_engine
        return Session(engine)

# Usage
db = DatabaseRouter()

# Write operations go to primary
with db.get_session(read_only=False) as session:
    session.add(new_user)
    session.commit()

# Read operations go to replica
with db.get_session(read_only=True) as session:
    users = session.query(User).all()
```

---

## 10. Sharding

### Sharding Strategies

```
Hash-based:
  shard = hash(user_id) % N

Range-based:
  shard_0: users with id 1-10000
  shard_1: users with id 10001-20000

Directory-based:
  lookup table: user_id → shard_id

Geographic:
  shard_us: North America
  shard_eu: Europe
  shard_ap: Asia Pacific
```

---

## 11. ACID vs BASE

| Property | ACID (SQL) | BASE (NoSQL) |
|----------|------------|--------------|
| **A**tomicity | All or nothing | Basically Available |
| **C**onsistency | Data always valid | Soft state (may change) |
| **I**solation | Concurrent transactions isolated | Eventual consistency |
| **D**urability | Committed data persists | Eventually consistent |

### When to Use Which

**ACID (PostgreSQL, MySQL):**
- Financial transactions
- Inventory management
- Any system requiring strict consistency

**BASE (MongoDB, Cassandra):**
- High-volume write systems
- User session data
- Content management systems
- Analytics/time-series data

---

## 12. CAP Theorem

```
          Consistency (CP)
          /              \
         /                \
        /                  \
  Consistency            Availability
       \                    /
        \                  /
         \                /
       Partition Tolerance (AP)

You can have at most 2 of 3:
  CP: PostgreSQL, MongoDB (with single-primary)
  AP: Cassandra, DynamoDB, CouchDB
  CA: (Can't exist in distributed systems — P is mandatory)
```

### Trade-off Decisions

| System | Choice | Reason |
|--------|--------|--------|
| Banking | CP | Consistency critical, can tolerate downtime |
| Social feed | AP | Availability critical, stale data acceptable |
| DNS | AP | Must always resolve, eventual consistency OK |
| E-commerce cart | AP | Must accept items, sync later |
| Inventory | CP | Double-selling unacceptable |
