# Data Engineering — Comprehensive Skill Guide

## Table of Contents
1. ETL Pipeline Design
2. ELT Patterns
3. Apache Spark (DataFrames, RDDs, Optimizations)
4. Apache Airflow (DAGs, Operators, Sensors)
5. dbt (Data Transformations, Testing, Documentation)
6. Streaming (Kafka, Flink, Pulsar)
7. Data Warehouse Design (Star Schema, Snowflake, Dimensional Modeling)
8. Data Lake Architecture
9. Batch vs Streaming
10. Data Quality Checks
11. Monitoring and Alerting
12. Orchestration Best Practices

---

## 1. ETL Pipeline Design

### Pipeline Architecture

```
Source Systems → Extract → (Staging) → Transform → Load → Data Warehouse
     |              |                       |            |
  Databases      Incremental/Full        Clean         Star Schema
  APIs           Change Data Capture     Enrich        Snowflake
  Files (CSV)    Batch Timestamps        Aggregate     Columnar
  Streams (Kafka)                       Deduplicate
  SaaS (Salesforce)
```

### Extraction Patterns

```python
# Incremental extraction with watermark
class IncrementalExtractor:
    def __init__(self, connection, table, watermark_column):
        self.conn = connection
        self.table = table
        self.watermark = watermark_column

    def get_last_watermark(self):
        # Read from metadata table
        return self.conn.execute("""
            SELECT last_value FROM etl_watermarks
            WHERE table_name = %s
        """, (self.table,)).scalar()

    def update_watermark(self, value):
        self.conn.execute("""
            UPDATE etl_watermarks SET last_value = %s
            WHERE table_name = %s
        """, (value, self.table))

    def extract(self, batch_size=10000):
        last_value = self.get_last_watermark()
        offset = 0

        while True:
            rows = self.conn.execute(f"""
                SELECT * FROM {self.table}
                WHERE {self.watermark} > %s
                ORDER BY {self.watermark}
                LIMIT %s OFFSET %s
            """, (last_value, batch_size, offset)).fetchall()

            if not rows:
                break

            yield rows
            offset += batch_size

            # Update watermark after processing
            new_max = max(row[self.watermark] for row in rows)
            self.update_watermark(new_max)

# API extraction with pagination
async def extract_from_api(base_url, api_key, endpoint):
    headers = {'Authorization': f'Bearer {api_key}'}
    page = 1
    has_more = True

    while has_more:
        response = await httpx.get(
            f'{base_url}/{endpoint}',
            headers=headers,
            params={'page': page, 'per_page': 100},
        )
        data = response.json()

        if not data['items']:
            break

        yield data['items']
        page += 1
        has_more = data['has_more']
```

### Transformation Layer

```python
# Clean, validate, enrich pipeline
class TransformPipeline:
    def __init__(self):
        self.steps = []

    def add_step(self, func, name=None):
        self.steps.append((func, name or func.__name__))
        return self

    def run(self, df):
        for func, name in self.steps:
            try:
                df = func(df)
                log_transform(name, df.count())
            except Exception as e:
                raise TransformError(f"Failed at step '{name}': {e}")
        return df

# Usage
pipeline = TransformPipeline()
pipeline.add_step(drop_duplicates, "dedup")
pipeline.add_step(validate_schema, "schema_check")
pipeline.add_step(enrich_with_dimensions, "enrichment")
pipeline.add_step(aggregate_metrics, "aggregation")

result = pipeline.run(raw_data)
```

---

## 2. ELT Patterns

### ELT vs ETL

```
ETL (Traditional): Extract → Transform → Load
  - Transform before loading (heavy transformation server)
  - Good for complex transformations on limited warehouse compute
  - Data comes pre-cleaned to warehouse

ELT (Modern): Extract → Load → Transform
  - Load raw data first, transform in warehouse
  - Leverages warehouse compute power (Snowflake, BigQuery, Redshift)
  - More flexible, easier to backfill
  - Raw data always available for reprocessing
```

### ELT Implementation

```sql
-- Stage 1: Load raw data
CREATE TABLE raw.events (
  _id VARCHAR(256),
  _ ingested_at TIMESTAMPTZ DEFAULT NOW(),
  raw_payload VARIANT,  -- Semi-structured
  source_file VARCHAR(1024)
);

COPY INTO raw.events (raw_payload, source_file)
FROM @my_stage/events/
FILE_FORMAT = (TYPE = JSON);

-- Stage 2: Transform in warehouse
CREATE TABLE staging.events AS
SELECT
  raw_payload:event_id::STRING AS event_id,
  raw_payload:event_type::STRING AS event_type,
  raw_payload:user_id::STRING AS user_id,
  raw_payload:properties::VARIANT AS properties,
  TO_TIMESTAMP(raw_payload:timestamp::STRING) AS event_time,
  _ingested_at
FROM raw.events
WHERE raw_payload:event_id IS NOT NULL;

-- Stage 3: Build dimensional model
CREATE TABLE mart.daily_events AS
SELECT
  DATE(event_time) AS event_date,
  event_type,
  COUNT(DISTINCT user_id) AS unique_users,
  COUNT(*) AS total_events
FROM staging.events
GROUP BY 1, 2;
```

---

## 3. Apache Spark

### DataFrame API

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, when, lit, count, sum, avg,
    window, date_trunc, to_date, from_json,
    explode, collect_list, to_timestamp,
    row_number, rank, lag, lead,
)
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType
from pyspark.sql.window import Window

spark = SparkSession.builder \
    .appName("ETL Pipeline") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
    .config("spark.sql.adaptive.skewJoin.enabled", "true") \
    .config("spark.sql.parquet.compression.codec", "snappy") \
    .getOrCreate()

# Read with schema
schema = StructType([
    StructField("user_id", StringType(), True),
    StructField("event_type", StringType(), True),
    StructField("timestamp", TimestampType(), True),
    StructField("properties", StringType(), True),
])

df = spark.read \
    .schema(schema) \
    .option("header", "true") \
    .parquet("s3://data-lake/events/*.parquet")

# Transformations
result = df \
    .filter(col("event_type").isin(["purchase", "signup"])) \
    .withColumn("event_date", to_date(col("timestamp"))) \
    .withColumn("purchase_value",
        when(col("event_type") == "purchase",
            from_json(col("properties"), "value DOUBLE").getField("value")
        ).otherwise(lit(0))
    ) \
    .groupBy("event_date", "event_type") \
    .agg(
        count("*").alias("event_count"),
        countDistinct("user_id").alias("unique_users"),
        sum("purchase_value").alias("total_revenue"),
    ) \
    .orderBy("event_date", "event_type")

# Window functions
window_spec = Window.partitionBy("user_id").orderBy("event_date")
result_with_rank = result.withColumn(
    "user_event_rank",
    row_number().over(window_spec)
)

# Write output
result.write \
    .mode("overwrite") \
    .partitionBy("event_date") \
    .parquet("s3://data-warehouse/daily_events/")
```

### Spark Optimizations

```python
# Partition tuning
df = spark.read.parquet("data/")
df.repartition(200, "event_date")  # Hash partition
df.coalesce(50)  # Reduce partitions (no shuffle)

# Bucketing for join optimization
df.write \
    .bucketBy(100, "user_id") \
    .sortBy("event_date") \
    .saveAsTable("events_bucketed")

# Caching strategies
df.cache()  # Memory
df.persist(StorageLevel.MEMORY_AND_DISK)  # Spill to disk
df.unpersist()

# Broadcast join for small tables
from pyspark.sql.functions import broadcast
result = large_df.join(broadcast(small_df), "user_id")

# AQE (Adaptive Query Execution) — automatically tunes
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.parallelismFirst", "false")
```

### RDD vs DataFrame

| Feature | RDD | DataFrame |
|---------|-----|-----------|
| API | Low-level, type-safe | High-level, SQL-like |
| Optimization | Manual | Catalyst optimizer |
| Serialization | Java/Kryo | Tungsten (off-heap) |
| Schema | No | Yes (structured) |
| Performance | Slower | 2-5x faster |
| Use case | Custom processing | Standard ETL |

---

## 4. Apache Airflow

### DAG Definition

```python
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.operators.postgres_operator import PostgresOperator
from airflow.sensors.filesystem import FileSensor
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator

default_args = {
    'owner': 'data_team',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
    'sla': timedelta(hours=1),
}

with DAG(
    'daily_etl_pipeline',
    default_args=default_args,
    description='Daily ETL from sources to warehouse',
    schedule_interval='0 3 * * *',    # Daily at 3 AM
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['production', 'etl'],
    max_active_runs=1,                 # No concurrent runs
    doc_md=__doc__,
) as dag:

    start = DummyOperator(task_id='start_pipeline')

    # Sensor — wait for source files
    wait_for_source = S3KeySensor(
        task_id='wait_for_source_files',
        bucket_name='data-lake',
        bucket_key='sources/events/{{ ds }}/_SUCCESS',
        poke_interval=60,
        timeout=3600,
        mode='reschedule',
    )

    # Extract
    extract_data = PythonOperator(
        task_id='extract_source_data',
        python_callable=extract_events,
        op_kwargs={'execution_date': '{{ ds }}'},
        pool='extract_pool',
    )

    # Branch — full vs incremental
    def check_full_load(**context):
        ds = context['ds']
        if ds == '2025-01-01' or ds.endswith('-01'):  # First of month
            return 'full_load_transform'
        return 'incremental_transform'

    check_load_type = BranchPythonOperator(
        task_id='check_load_type',
        python_callable=check_full_load,
    )

    full_load = SnowflakeOperator(
        task_id='full_load_transform',
        sql='sql/full_refresh.sql',
        params={'execution_date': '{{ ds }}'},
    )

    incremental_load = SnowflakeOperator(
        task_id='incremental_transform',
        sql='sql/incremental_load.sql',
        params={'execution_date': '{{ ds }}'},
    )

    # Quality checks
    run_quality_checks = PythonOperator(
        task_id='run_quality_checks',
        python_callable=execute_quality_checks,
        trigger_rule='none_failed',
    )

    # Notification
    notify_success = PythonOperator(
        task_id='notify_success',
        python_callable=send_slack_notification,
        op_kwargs={'status': 'success'},
    )

    notify_failure = PythonOperator(
        task_id='notify_failure',
        python_callable=send_slack_notification,
        op_kwargs={'status': 'failure'},
        trigger_rule='one_failed',
    )

    # Dependencies
    start >> wait_for_source >> extract_data >> check_load_type
    check_load_type >> [full_load, incremental_load]
    [full_load, incremental_load] >> run_quality_checks
    run_quality_checks >> [notify_success, notify_failure]
```

### Sensors & Operators

```python
# Custom sensor
class EventCompleteSensor(BaseSensorOperator):
    def __init__(self, event_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event_name = event_name

    def poke(self, context):
        return check_event_complete(self.event_name)

# Custom operator
class DataQualityOperator(BaseOperator):
    template_fields = ('sql', 'expectations')

    def __init__(self, sql, expectations, conn_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sql = sql
        self.expectations = expectations
        self.conn_id = conn_id

    def execute(self, context):
        records = execute_sql(self.sql, self.conn_id)
        for expectation in self.expectations:
            if not expectation.check(records):
                raise AirflowException(f"Quality check failed: {expectation.name}")
```

---

## 5. dbt (Data Build Tool)

### Project Structure

```
dbt_project/
├── models/
│   ├── staging/
│   │   ├── stg_orders.sql
│   │   ├── stg_users.sql
│   │   └── schema.yml
│   ├── marts/
│   │   ├── marketing/
│   │   │   ├── dim_users.sql
│   │   │   └── schema.yml
│   │   └── finance/
│   │       ├── fct_orders.sql
│   │       └── schema.yml
│   └── intermediate/
│       └── int_order_items_joined.sql
├── tests/
│   ├── not_null_customers_email.sql
│   └── relationships.yml
├── analyses/
├── snapshots/
│   └── scd_users.sql
├── seeds/
│   └── country_codes.csv
├── macros/
│   ├── grant_permissions.sql
│   └── pivot_columns.sql
├── docs/
│   └── data_dictionary.md
└── dbt_project.yml
```

### Model Definitions

```sql
-- models/staging/stg_orders.sql
WITH source AS (
    SELECT * FROM {{ source('ecommerce', 'orders') }}
),

renamed AS (
    SELECT
        id AS order_id,
        user_id AS customer_id,
        order_date,
        status,
        amount::DECIMAL(10,2) AS order_amount,
        _loaded_at
    FROM source
    WHERE _loaded_at > (
        SELECT MAX(_loaded_at) FROM {{ this }}
    )
)

SELECT * FROM renamed

-- models/marts/finance/fct_orders.sql
WITH orders AS (
    SELECT * FROM {{ ref('stg_orders') }}
),

order_items AS (
    SELECT * FROM {{ ref('stg_order_items') }}
),

joined AS (
    SELECT
        o.order_id,
        o.customer_id,
        o.order_date,
        o.status,
        COUNT(DISTINCT oi.product_id) AS unique_products,
        SUM(oi.quantity) AS total_items,
        SUM(oi.subtotal) AS subtotal,
        o.order_amount AS total,
        {{ calculate_tax('o.order_amount') }} AS tax
    FROM orders o
    LEFT JOIN order_items oi ON o.order_id = oi.order_id
    GROUP BY 1, 2, 3, 4, 8
)

SELECT * FROM joined
```

### Testing & Documentation

```yaml
# models/staging/schema.yml
version: 2

models:
  - name: stg_orders
    description: "Cleaned orders from the ecommerce source"
    columns:
      - name: order_id
        description: "Primary key"
        tests:
          - unique
          - not_null
      - name: customer_id
        description: "Foreign key to customers"
        tests:
          - not_null
          - relationships:
              to: ref('stg_users')
              field: user_id
      - name: order_amount
        description: "Total order amount"
        tests:
          - not_null
          - dbt_utils.accepted_range:
              min_value: 0
              max_value: 100000
    tests:
      - dbt_utils.expression_is_true:
          expression: "order_date >= '2020-01-01'"

  - name: fct_orders
    description: "Fact table with order aggregates"
    columns:
      - name: order_id
        tests:
          - unique
          - not_null
      - name: tax
        tests:
          - dbt_utils.expression_is_true:
              expression: "tax >= 0"
```

---

## 6. Streaming (Kafka, Flink, Pulsar)

### Kafka Basics

```python
from kafka import KafkaProducer, KafkaConsumer
import json

# Producer
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    acks='all',             # Wait for all replicas
    compression_type='snappy',
    linger_ms=10,           # Batch for 10ms
    batch_size=16384,       # 16KB batches
)

producer.send('events', {
    'user_id': '123',
    'event_type': 'page_view',
    'timestamp': '2026-05-25T10:00:00Z',
    'properties': {'page': '/home'}
})

# Consumer
consumer = KafkaConsumer(
    'events',
    bootstrap_servers=['localhost:9092'],
    auto_offset_reset='earliest',
    enable_auto_commit=False,
    group_id='etl-processor',
    max_poll_records=500,
)

for message in consumer:
    data = json.loads(message.value)
    process_event(data)
    consumer.commit()
```

### Kafka Configuration

```properties
# Server config
num.partitions=6
default.replication.factor=3
min.insync.replicas=2
log.retention.hours=168
log.segment.bytes=1073741824

# Topic with 12 partitions for high throughput
# bin/kafka-topics.sh --create \
#   --topic user-events \
#   --partitions 12 \
#   --replication-factor 3 \
#   --config cleanup.policy=delete \
#   --config retention.ms=604800000
```

### Flink Stream Processing

```python
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors import FlinkKafkaConsumer
from pyflink.common.serialization import SimpleStringSchema
from pyflink.datastream.window import TumblingEventTimeWindows, Time
from pyflink.common.typeinfo import Types

env = StreamExecutionEnvironment.get_execution_environment()
env.set_parallelism(4)

# Source
stream = env.add_source(
    FlinkKafkaConsumer(
        topics='events',
        deserialization_schema=SimpleStringSchema(),
        properties={
            'bootstrap.servers': 'localhost:9092',
            'group.id': 'flink-processor',
        }
    )
)

# Windowed aggregation
stream \
    .map(lambda x: (json.loads(x)['event_type'], 1)) \
    .key_by(lambda x: x[0]) \
    .window(TumblingEventTimeWindows.of(Time.minutes(5))) \
    .sum(1) \
    .print()

env.execute('event_counter')
```

---

## 7. Data Warehouse Design

### Star Schema

```
Fact Table: fct_orders
  order_id (PK)
  customer_id (FK → dim_customers)
  product_id (FK → dim_products)
  store_id (FK → dim_stores)
  date_id (FK → dim_date)
  quantity
  unit_price
  discount
  total_amount

Dimension: dim_customers
  customer_id (PK)
  name
  email
  segment
  first_purchase_date
  customer_tenure_days

Dimension: dim_products
  product_id (PK)
  product_name
  category
  subcategory
  brand
  unit_cost
  unit_price

Dimension: dim_date
  date_id (PK)
  full_date
  year
  quarter
  month
  week
  day_of_week
  is_holiday
```

### Snowflake Schema

```
dim_product (normalized into sub-dimensions)
  product_id (PK)
  product_name
  category_id (FK → dim_category)
  supplier_id (FK → dim_supplier)

dim_category
  category_id (PK)
  category_name
  department_id (FK → dim_department)

dim_department
  department_id (PK)
  department_name
```

### Slowly Changing Dimensions (SCD)

| Type | Strategy | Example |
|------|----------|---------|
| 0 | Fixed (never changes) | Date of birth |
| 1 | Overwrite (no history) | Customer email |
| 2 | Add new row (full history) | Customer address |
| 3 | Add new column (limited history) | Previous address |
| 4 | Separate history table | Full audit trail |

```sql
-- SCD Type 2 Implementation
CREATE TABLE dim_customers_scd2 (
  customer_sk INTEGER PRIMARY KEY,  -- Surrogate key
  customer_id INTEGER,               -- Business key
  name VARCHAR(100),
  email VARCHAR(200),
  address VARCHAR(500),
  valid_from TIMESTAMPTZ,
  valid_to TIMESTAMPTZ,
  is_current BOOLEAN DEFAULT true,
  dbt_updated_at TIMESTAMPTZ,
  dbt_valid_from TIMESTAMPTZ,
  dbt_valid_to TIMESTAMPTZ
);
```

---

## 8. Data Lake Architecture

### Lakehouse Architecture

```
Raw Zone (Bronze)
├── sources/
│   ├── database/
│   │   └── orders/YYYY/MM/DD/orders_001.parquet
│   ├── api/
│   │   └── events/event_dt=2026-05-25/part-00001.parquet
│   └── streaming/
│       └── clicks/YYYY/MM/DD/HH/clicks_001.parquet

Enriched Zone (Silver)
├── cleaned/
│   └── orders/
│       └── year=2026/month=05/day=25/
├── deduplicated/
│   └── events/
└── joined/
    └── order_items/

Analytics Zone (Gold)
├── aggregates/
│   └── daily_kpis/
├── marts/
│   ├── marketing/
│   └── finance/
└── ml_features/
    └── user_features/
```

### Table Format: Delta Lake

```python
from delta.tables import DeltaTable

# Write with Delta
df.write \
    .format("delta") \
    .mode("append") \
    .partitionBy("event_date") \
    .save("/data/lake/events/")

# Time travel
df_historical = spark.read \
    .format("delta") \
    .option("versionAsOf", 42) \
    .load("/data/lake/events/")

# Upsert (merge)
delta_table = DeltaTable.forPath(spark, "/data/lake/events/")
delta_table.alias("target") \
    .merge(
        updates_df.alias("source"),
        "target.event_id = source.event_id"
    ) \
    .whenMatchedUpdateAll() \
    .whenNotMatchedInsertAll() \
    .execute()

# Vacuum (clean old files)
delta_table.vacuum(retentionHours=168)
```

---

## 9. Batch vs Streaming

| Characteristic | Batch | Streaming |
|---------------|-------|-----------|
| Latency | Minutes to hours | Milliseconds to seconds |
| Processing | Fixed intervals | Continuous |
| Storage | Data Lake/Warehouse | Message queue + state |
| Complexity | Lower | Higher |
| Fault tolerance | Easier (reprocess) | Harder (state management) |
| Cost | Lower per event | Higher per event |
| Use cases | Reports, ML training | Real-time dashboards, alerts |

### Lambda Architecture

```
Batch Layer → Serving Layer → Query
  (complete, accurate)     (batch + real-time views)
                                      ↑
Stream Layer → Real-time View →───────┘
  (low-latency, approximate)
```

### Kappa Architecture

```
Stream Layer → Serving Layer → Query
  (single pipeline, no batch)
```

---

## 10. Data Quality Checks

### Quality Dimensions

| Dimension | Description | Check |
|-----------|-------------|-------|
| Completeness | No missing values | `COUNT(*) = COUNT(column)` |
| Uniqueness | No duplicates | `COUNT(DISTINCT col) = COUNT(*)` |
| Timeliness | Data is fresh | `MAX(updated_at) > NOW() - interval` |
| Validity | Values match format/schema | Regex, type checks |
| Accuracy | Values match reality | Cross-reference with source |
| Consistency | No contradictions | `SUM(order_items) = order.total` |

### Automated Checks

```python
def check_data_quality(df, checks):
    results = {}

    for check in checks:
        if check.type == 'not_null':
            nulls = df.filter(col(check.column).isNull()).count()
            results[check.name] = nulls == 0

        elif check.type == 'unique':
            total = df.count()
            distinct = df.select(check.column).distinct().count()
            results[check.name] = total == distinct

        elif check.type == 'freshness':
            max_date = df.agg(max(check.column)).collect()[0][0]
            results[check.name] = max_date >= datetime.now() - check.threshold

        elif check.type == 'row_count':
            count = df.count()
            results[check.name] = check.min <= count <= check.max

        elif check.type == 'referential_integrity':
            fk_values = df.select(check.column).distinct().collect()
            pk_values = lookup_df.select(check.references).distinct().collect()
            missing = set(fk_values) - set(pk_values)
            results[check.name] = len(missing) == 0

    return results
```

---

## 11. Monitoring & Alerting

### Pipeline Metrics

```python
# Structured logging for monitoring
import structlog

logger = structlog.get_logger()

def monitor_pipeline_step(step_name, df_before, df_after, duration):
    logger.info("pipeline_step_completed",
        step=step_name,
        rows_before=df_before.count(),
        rows_after=df_after.count(),
        rows_dropped=df_before.count() - df_after.count(),
        duration_seconds=duration,
    )
```

### Alert Conditions

- **Row count deviation** > 20% from expected
- **Pipeline duration** > 2x historical average
- **Null rate** > 1% on NOT NULL columns
- **Duplicate rate** > 0.1% on unique columns
- **Schema mismatch** — column type or count changed
- **Source unavailable** — connection timeout
- **Watermark not advancing** — stuck extraction

---

## 12. Orchestration Best Practices

### Workflow Design Principles

1. **Idempotency** — Running twice produces same result
2. **Retry logic** — 3 retries with exponential backoff
3. **Dead letter queue** — Failed records stored for analysis
4. **Backfill capability** — Reprocess any date range
5. **Dependency management** — Upstream failures cascade properly
6. **SLA tracking** — Measure and alert on run duration
7. **Resource tagging** — Owner, cost center, environment
8. **Immutable datasets** — Append-only or versioned

### Error Handling

```python
class PipelineError(Exception):
    def __init__(self, message, step, records_affected=0):
        self.message = message
        self.step = step
        self.records_affected = records_affected
        super().__init__(self.message)

class RetryableError(PipelineError):
    """Can be retried (connection timeout, rate limit)"""
    pass

class NonRetryableError(PipelineError):
    """Must fail (schema mismatch, missing data)"""
    pass
```

### Configuration Management

```yaml
# pipeline_config.yaml
pipeline:
  name: daily_orders_etl
  version: 2.1.0
  schedule: "0 3 * * *"
  timezone: UTC

sources:
  - name: orders_db
    type: postgres
    connection: ${ORDERS_DB_URL}  # Environment variable
    extraction:
      method: incremental
      watermark_column: updated_at
      batch_size: 50000

  - name: events_api
    type: rest_api
    base_url: https://api.example.com/v2
    rate_limit: 100  # requests per minute

quality_checks:
  row_count:
    min_expected: 10000
    max_expected: 500000
    alert_if_below: 5000
  null_checks:
    - column: order_id
      max_null_pct: 0
    - column: amount
      max_null_pct: 0.01

notifications:
  slack:
    webhook: ${SLACK_WEBHOOK}
    on_success: false
    on_failure: true
    on_retry: true
```
