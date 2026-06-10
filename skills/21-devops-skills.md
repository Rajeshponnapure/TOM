# DevOps Skills — Mastery Guide

## Overview
DevOps bridges development and operations through automation, containerization, orchestration, CI/CD, monitoring, and infrastructure as code. This guide covers core technologies and practices.

---

## Docker

### Dockerfile Best Practices

```dockerfile
# Multi-stage build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 appuser
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
USER appuser
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1
CMD ["node", "dist/server.js"]
```

### docker-compose.yml

```yaml
version: "3.8"

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      target: runner
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DB_HOST=db
      - REDIS_HOST=redis
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - backend
    volumes:
      - uploads:/app/uploads
    restart: unless-stopped
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: "0.5"
          memory: 512M

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: app
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - backend

  redis:
    image: redis:7-alpine
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
    networks:
      - backend

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - app
    networks:
      - backend

volumes:
  pgdata:
  redisdata:
  uploads:

networks:
  backend:
    driver: bridge
```

### Docker Networking

| Network Driver | Scope | Use Case |
|---------------|-------|----------|
| bridge | Single host | Default for containers on same host |
| host | Single host | Direct host networking (no isolation) |
| overlay | Multi-host | Swarm/Kubernetes cluster networking |
| macvlan | Multi-host | Assign MAC addresses, direct VLAN |
| none | None | Complete isolation |

### Docker Security

- Run as non-root (`USER appuser` in Dockerfile)
- Use read-only root filesystem (`read_only: true`)
- Drop capabilities: `cap_drop: [ALL]` then add only needed ones
- Use secrets for sensitive data: `docker secret create`
- Scan images: `docker scan` or `trivy image`
- Use distroless or Alpine base images
- Enable Content Trust: `export DOCKER_CONTENT_TRUST=1`

---

## Kubernetes

### Pod Configuration

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-app
  labels:
    app: web
    tier: frontend
spec:
  containers:
  - name: app
    image: myapp:latest
    ports:
    - containerPort: 3000
    env:
    - name: DB_HOST
      value: postgres-service
    - name: DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: db-secret
          key: password
    resources:
      requests:
        memory: "256Mi"
        cpu: "250m"
      limits:
        memory: "512Mi"
        cpu: "500m"
    livenessProbe:
      httpGet:
        path: /health
        port: 3000
      initialDelaySeconds: 10
      periodSeconds: 30
    readinessProbe:
      httpGet:
        path: /ready
        port: 3000
      initialDelaySeconds: 5
      periodSeconds: 10
  restartPolicy: Always
```

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deployment
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 1
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: web
        image: myapp:${BUILD_TAG}
        ports:
        - containerPort: 3000
```

### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-service
spec:
  type: ClusterIP
  selector:
    app: web
  ports:
  - protocol: TCP
    port: 80
    targetPort: 3000
---
apiVersion: v1
kind: Service
metadata:
  name: web-loadbalancer
spec:
  type: LoadBalancer
  selector:
    app: web
  ports:
  - port: 443
    targetPort: 3000
```

### Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - app.example.com
    secretName: app-tls
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-service
            port:
              number: 80
```

### ConfigMaps and Secrets

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_ENV: production
  LOG_LEVEL: info
  API_URL: https://api.example.com
---
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
data:
  DB_PASSWORD: c3VwZXJzZWNyZXQ=  # base64 encoded
  API_KEY: c2VjcmV0LWtleS0xMjM=
```

### Helm Chart Structure

```
mychart/
├── Chart.yaml          # Metadata
├── values.yaml         # Default values
├── values.prod.yaml    # Environment overrides
├── charts/             # Sub-charts
├── templates/
│   ├── _helpers.tpl    # Named templates
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   └── NOTES.txt       # Install notes
└── .helmignore
```

### Helm Values

```yaml
# values.yaml
replicaCount: 3

image:
  repository: myapp
  tag: latest
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: true
  host: app.example.com
  tls: true

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 250m
    memory: 256Mi

config:
  APP_ENV: production
  LOG_LEVEL: info
```

---

## CI/CD — GitHub Actions

### Workflow Structure

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  workflow_dispatch:

env:
  NODE_VERSION: "20"
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_PASSWORD: testpass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
    - uses: actions/checkout@v4
    
    - uses: actions/setup-node@v4
      with:
        node-version: ${{ env.NODE_VERSION }}
        cache: 'npm'
    
    - run: npm ci
    - run: npm run lint
    - run: npm run typecheck
    - run: npm test
    - run: npm run test:e2e
      env:
        DATABASE_URL: postgresql://postgres:testpass@localhost:5432/test
    
    - name: Upload coverage
      uses: actions/upload-artifact@v4
      with:
        name: coverage
        path: coverage/

  build:
    needs: [test]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    
    - name: Log in to registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=semver,pattern={{version}}
          type=sha,format=short
          type=ref,event=branch
    
    - name: Build and push
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  deploy:
    needs: [build]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Configure kubectl
      uses: azure/setup-kubectl@v3
      with:
        version: 'latest'
    
    - name: Set kubeconfig
      run: echo "${{ secrets.KUBE_CONFIG }}" > $HOME/.kube/config
    
    - name: Deploy to Kubernetes
      run: |
        helm upgrade --install myapp ./helm \
          --namespace production \
          --values ./helm/values.yaml \
          --values ./helm/values.prod.yaml \
          --set image.tag=${{ github.sha }} \
          --wait --timeout 5m
```

### Matrix Builds

```yaml
jobs:
  test:
    strategy:
      matrix:
        node: [18, 20, 22]
        os: [ubuntu-latest, windows-latest]
        exclude:
          - os: windows-latest
            node: 22
    
    runs-on: ${{ matrix.os }}
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: ${{ matrix.node }}
    - run: npm ci
    - run: npm test
```

### Caching

```yaml
- name: Cache dependencies
  uses: actions/cache@v4
  with:
    path: |
      ~/.npm
      node_modules
    key: ${{ runner.os }}-node-${{ hashFiles('package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-

- name: Cache Docker layers
  uses: actions/cache@v4
  with:
    path: /tmp/.buildx-cache
    key: ${{ runner.os }}-buildx-${{ github.sha }}
    restore-keys: |
      ${{ runner.os }}-buildx-
```

### Environments and Deployment Gates

```yaml
deploy-staging:
  runs-on: ubuntu-latest
  environment:
    name: staging
    url: https://staging.example.com
  steps:
  - run: ./deploy.sh staging

deploy-production:
  needs: [deploy-staging]
  runs-on: ubuntu-latest
  environment:
    name: production
    url: https://example.com
  steps:
  - run: ./deploy.sh production
```

Environment protection rules:
- Required reviewers
- Wait timer
- Deployment branches (e.g., main only)

---

## Infrastructure as Code

### Terraform

```hcl
# main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    bucket = "myapp-terraform-state"
    key    = "production/terraform.tfstate"
    region = "us-west-2"
    dynamodb_table = "terraform-locks"
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region
}

# VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = {
    Name = "myapp-${var.environment}"
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "myapp-${var.environment}"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# ECS Service
resource "aws_ecs_service" "app" {
  name            = "app-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.app_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.app.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "app"
    container_port   = 3000
  }

  deployment_controller {
    type = "ECS"
  }
}

# variables.tf
variable "environment" {
  description = "Environment name"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "app_count" {
  description = "Number of app containers"
  type        = number
  default     = 2
}

# outputs.tf
output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}
```

### Pulumi (TypeScript)

```typescript
import * as aws from "@pulumi/aws";
import * as pulumi from "@pulumi/pulumi";

const config = new pulumi.Config();
const environment = config.require("environment");

const vpc = new aws.ec2.Vpc("main", {
  cidrBlock: "10.0.0.0/16",
  enableDnsHostnames: true,
  enableDnsSupport: true,
  tags: { Name: `myapp-${environment}` },
});

const cluster = new aws.ecs.Cluster("main", {
  name: `myapp-${environment}`,
  settings: [{ name: "containerInsights", value: "enabled" }],
});

const taskDef = new aws.ecs.TaskDefinition("app", {
  family: `myapp-${environment}`,
  cpu: "512",
  memory: "1024",
  networkMode: "awsvpc",
  requiresCompatibilities: ["FARGATE"],
  executionRoleArn: executionRole.arn,
  containerDefinitions: JSON.stringify([{
    name: "app",
    image: "myapp:latest",
    portMappings: [{ containerPort: 3000 }],
    environment: [
      { name: "NODE_ENV", value: environment },
      { name: "DB_HOST", value: dbHost },
    ],
  }]),
});
```

### AWS CloudFormation

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'MyApp Infrastructure'

Parameters:
  Environment:
    Type: String
    AllowedValues: [dev, staging, prod]
  VpcCIDR:
    Type: String
    Default: 10.0.0.0/16

Resources:
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: !Ref VpcCIDR
      EnableDnsHostnames: true
      EnableDnsSupport: true
      Tags:
        - Key: Name
          Value: !Sub "myapp-${Environment}"

  ECSCluster:
    Type: AWS::ECS::Cluster
    Properties:
      ClusterName: !Sub "myapp-${Environment}"
      ClusterSettings:
        - Name: containerInsights
          Value: enabled

  TaskDefinition:
    Type: AWS::ECS::TaskDefinition
    Properties:
      Family: !Sub "myapp-${Environment}"
      Cpu: "512"
      Memory: "1024"
      NetworkMode: awsvpc
      RequiresCompatibilities:
        - FARGATE
      ExecutionRoleArn: !GetAtt ExecutionRole.Arn
      ContainerDefinitions:
        - Name: app
          Image: myapp:latest
          PortMappings:
            - ContainerPort: 3000
```

---

## Monitoring and Observability

### Prometheus and Grafana

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'kubernetes'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: myapp
      - source_labels: [__address__]
        action: replace
        regex: ([^:]+)(?::\d+)?
        replacement: $1:3000
        target_label: __address__
```

```yaml
# docker-compose monitoring
version: "3.8"
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana-data:/var/lib/grafana
      - ./dashboards:/etc/grafana/provisioning/dashboards
    ports:
      - "3000:3000"

  node-exporter:
    image: prom/node-exporter
    ports:
      - "9100:9100"
```

### OpenTelemetry

```typescript
// OpenTelemetry setup (Node.js)
import { NodeSDK } from '@opentelemetry/sdk-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { Resource } from '@opentelemetry/resources';
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';

const sdk = new NodeSDK({
  resource: new Resource({
    [SemanticResourceAttributes.SERVICE_NAME]: 'myapp',
    [SemanticResourceAttributes.DEPLOYMENT_ENVIRONMENT]: process.env.ENV,
  }),
  traceExporter: new OTLPTraceExporter({
    url: 'http://otel-collector:4318/v1/traces',
  }),
  instrumentations: [getNodeAutoInstrumentations()],
});

sdk.start();
```

### Structured Logging

```javascript
// Winston structured logging
const winston = require('winston');

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  defaultMeta: { 
    service: 'myapp',
    environment: process.env.NODE_ENV 
  },
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ 
      filename: 'logs/error.log', 
      level: 'error',
      maxsize: 5242880, // 5MB
      maxFiles: 5
    }),
    new winston.transports.File({ 
      filename: 'logs/combined.log',
      maxsize: 5242880,
      maxFiles: 10
    }),
  ],
});
```

### ELK Stack

```
Filebeat (log agent) → Logstash (processor) → Elasticsearch (storage) → Kibana (visualization)
```

```yaml
# filebeat.yml
filebeat.inputs:
- type: container
  paths:
    - /var/log/containers/*.log
  processors:
    - add_kubernetes_metadata:
        host: ${NODE_NAME}
        matchers:
        - logs_path:
            logs_path: "/var/log/containers/"

output.elasticsearch:
  hosts: ['${ELASTICSEARCH_HOST:elasticsearch}:9200']
  username: ${ELASTICSEARCH_USERNAME}
  password: ${ELASTICSEARCH_PASSWORD}
```

---

## Configuration Management

### Ansible

```yaml
---
- name: Configure web servers
  hosts: webservers
  become: yes
  vars:
    app_version: "1.2.3"
    nginx_port: 443
  
  tasks:
    - name: Update apt cache
      apt:
        update_cache: yes
        cache_valid_time: 3600
    
    - name: Install packages
      apt:
        name:
          - nginx
          - nodejs
          - certbot
        state: present
    
    - name: Create app directory
      file:
        path: /opt/myapp
        state: directory
        owner: appuser
        group: appuser
        mode: '0755'
    
    - name: Deploy application
      copy:
        src: /dist/app-v{{ app_version }}.tar.gz
        dest: /opt/myapp/app.tar.gz
      notify: restart app
    
    - name: Configure Nginx
      template:
        src: nginx.conf.j2
        dest: /etc/nginx/sites-available/myapp
      notify: reload nginx
    
    - name: Enable site
      file:
        src: /etc/nginx/sites-available/myapp
        dest: /etc/nginx/sites-enabled/myapp
        state: link
    
    - name: Start services
      systemd:
        name: "{{ item }}"
        state: started
        enabled: yes
      loop:
        - nginx
        - myapp
  
  handlers:
    - name: reload nginx
      systemd:
        name: nginx
        state: reloaded
    
    - name: restart app
      systemd:
        name: myapp
        state: restarted
```

---

## SRE Principles

### SLIs, SLOs, and Error Budgets

| Term | Definition | Example |
|------|------------|---------|
| **SLI** (Service Level Indicator) | Measured metric of service quality | Request latency P99 |
| **SLO** (Service Level Objective) | Target value for SLI | P99 latency < 500ms (99.9%) |
| **SLA** (Service Level Agreement) | Contractual commitment to customer | 99.95% uptime |
| **Error Budget** | Accepted failure = 1 - SLO | 0.1% = 43 minutes/month |

### Common SLO Targets

| Service Type | SLO | Error Budget |
|-------------|-----|-------------|
| Critical (auth, payments) | 99.99% | 52 minutes/year |
| Standard (API, web) | 99.9% | 8.76 hours/year |
| Internal tools | 99.0% | 3.65 days/year |

---

## Deployment Strategies

### Blue-Green Deployment

```
Before:
  [Router] → [Blue] (v1, live)
  [Green] (v2, idle)

After:
  [Router] → [Green] (v2, live)
  [Blue] (v1, idle/standby)
```

### Canary Release

```yaml
# Istio canary routing
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: myapp
spec:
  hosts:
  - myapp
  http:
  - match:
    - headers:
        canary:
          exact: "true"
    route:
    - destination:
        host: myapp
        subset: v2
      weight: 100
  - route:
    - destination:
        host: myapp
        subset: v1
      weight: 90
    - destination:
        host: myapp
        subset: v2
      weight: 10
```

### Feature Flags

```javascript
// LaunchDarkly example
const launchdarkly = require('launchdarkly-node-server-sdk');

const client = launchdarkly.init(process.env.LD_SDK_KEY);

app.get('/api/new-feature', async (req, res) => {
  const user = { key: req.user.id, email: req.user.email };
  
  const flagValue = await client.variation(
    'new-checkout-flow', 
    user, 
    false
  );
  
  if (flagValue) {
    return handleNewCheckout(req, res);
  }
  return handleOldCheckout(req, res);
});
```

---

## Security Scanning

### SAST (Static Analysis)

```yaml
# GitHub CodeQL
name: "CodeQL"
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  analyze:
    name: Analyze
    runs-on: ubuntu-latest
    permissions:
      security-events: write
    strategy:
      fail-fast: false
      matrix:
        language: ['javascript', 'typescript']

    steps:
    - uses: actions/checkout@v4
    - uses: github/codeql-action/init@v3
      with:
        languages: ${{ matrix.language }}
    - uses: github/codeql-action/analyze@v3
```

### Container Scanning

```yaml
# Trivy in CI
- name: Scan container image
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: 'myapp:${{ github.sha }}'
    format: 'sarif'
    output: 'trivy-results.sarif'
    severity: 'CRITICAL,HIGH'
    exit-code: '1'

- name: Upload results
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: 'trivy-results.sarif'
```

---

## Best Practices Summary

```
CI/CD
    [ ] Pipeline runs on every push
    [ ] All tests pass before deploy
    [ ] Build artifacts are immutable
    [ ] Deployments are idempotent
    [ ] Secrets never in code

Containers
    [ ] Multi-stage builds
    [ ] Minimal base images
    [ ] Non-root user
    [ ] Health checks
    [ ] Read-only filesystem where possible
    [ ] Pin base image versions

Kubernetes
    [ ] Use Deployments, not bare Pods
    [ ] Resource requests and limits on all containers
    [ ] Liveness and readiness probes
    [ ] PodDisruptionBudget for critical services
    [ ] Network policies for isolation
    [ ] RBAC for API access

Infrastructure
    [ ] IaC for everything (no manual changes)
    [ ] State files backed up and locked
    [ ] Secrets in vault/secret store
    [ ] Immutable infrastructure pattern
    [ ] Regular disaster recovery drills

Monitoring
    [ ] Four golden signals: latency, traffic, errors, saturation
    [ ] Alerts have runbooks
    [ ] Dashboards for every service
    [ ] Logs centrally collected and searchable
    [ ] Distributed tracing for critical paths

Security
    [ ] Dependency scanning
    [ ] Container vulnerability scanning
    [ ] SAST in CI pipeline
    [ ] Secrets scanning pre-commit
    [ ] Regular penetration testing
```
