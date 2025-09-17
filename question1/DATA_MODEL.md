# Data Model & Schema Documentation

## Overview

This document describes the data model and schema used for collecting, storing, and visualizing proxy usage telemetry from Kubernetes crawler pods.

## Metrics Collection Architecture

```
Crawler Pods → Prometheus Metrics → Prometheus Server → Grafana Dashboards
     ↓
Network Traffic → Cilium/Hubble → Hubble Metrics → Prometheus Server
```

## Application Metrics

### 1. Request Count Metrics

**Metric Name**: `crawler_requests_total`
**Type**: Counter
**Description**: Total number of HTTP/HTTPS requests made by crawler pods

**Labels**:
- `pod_name`: Name of the crawler pod (e.g., `crawler-app-7d8f9b5c4-xyz12`)
- `proxy_vendor`: Proxy vendor identifier (`vendor-a`, `vendor-b`, `vendor-c`)
- `destination_domain`: Target domain being crawled (e.g., `httpbin.org`)
- `protocol`: Request protocol (`http`, `https`)
- `status_code`: HTTP response status code (`200`, `404`, `500`, `error`)

**Example**:
```promql
crawler_requests_total{pod_name="crawler-app-7d8f9b5c4-xyz12",proxy_vendor="vendor-a",destination_domain="httpbin.org",protocol="https",status_code="200"} 142
```

### 2. Request Duration Metrics

**Metric Name**: `crawler_request_duration_seconds`
**Type**: Histogram
**Description**: Request duration in seconds with percentile buckets

**Labels**:
- `pod_name`: Name of the crawler pod
- `proxy_vendor`: Proxy vendor identifier
- `destination_domain`: Target domain
- `protocol`: Request protocol

**Buckets**: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, +Inf]

**Example**:
```promql
crawler_request_duration_seconds_bucket{pod_name="crawler-app-7d8f9b5c4-xyz12",proxy_vendor="vendor-b",destination_domain="jsonplaceholder.typicode.com",protocol="https",le="0.5"} 89
```

### 3. Outbound Bandwidth Metrics

**Metric Name**: `crawler_bytes_sent_total`
**Type**: Counter
**Description**: Total bytes sent (outbound traffic) per proxy per pod

**Labels**:
- `pod_name`: Name of the crawler pod
- `proxy_vendor`: Proxy vendor identifier
- `destination_domain`: Target domain

**Example**:
```promql
crawler_bytes_sent_total{pod_name="crawler-app-7d8f9b5c4-xyz12",proxy_vendor="vendor-c",destination_domain="reqres.in"} 45672
```

### 4. Inbound Bandwidth Metrics

**Metric Name**: `crawler_bytes_received_total`
**Type**: Counter
**Description**: Total bytes received (inbound traffic) per proxy per pod

**Labels**:
- `pod_name`: Name of the crawler pod
- `proxy_vendor`: Proxy vendor identifier
- `destination_domain`: Target domain

**Example**:
```promql
crawler_bytes_received_total{pod_name="crawler-app-7d8f9b5c4-xyz12",proxy_vendor="vendor-a",destination_domain="postman-echo.com"} 123456
```

### 5. Active Connections Metrics

**Metric Name**: `crawler_active_connections`
**Type**: Gauge
**Description**: Number of active connections per proxy vendor

**Labels**:
- `pod_name`: Name of the crawler pod
- `proxy_vendor`: Proxy vendor identifier

**Example**:
```promql
crawler_active_connections{pod_name="crawler-app-7d8f9b5c4-xyz12",proxy_vendor="vendor-b"} 3
```

## Network Flow Metrics (Cilium/Hubble)

### 1. Network Flow Count

**Metric Name**: `hubble_flows_total`
**Type**: Counter
**Description**: Total network flows observed by Hubble

**Labels**:
- `source`: Source pod/service
- `destination`: Destination IP/domain
- `protocol`: Network protocol (TCP, UDP)
- `verdict`: Flow verdict (ALLOWED, DENIED)

### 2. Network Flow Bytes

**Metric Name**: `hubble_flows_bytes_total`
**Type**: Counter
**Description**: Total bytes transferred in network flows

**Labels**:
- `source`: Source pod/service
- `destination`: Destination IP/domain
- `direction`: Traffic direction (INGRESS, EGRESS)

## Data Retention and Storage

### Prometheus Configuration
- **Retention Period**: 15 days (default)
- **Storage**: Local storage (suitable for demo/development)
- **Scrape Interval**: 30 seconds
- **Evaluation Interval**: 30 seconds

### Metric Cardinality Considerations

**High Cardinality Labels** (use with caution):
- `pod_name`: Can be high if pods are frequently recreated
- `destination_domain`: Limited by configured target domains

**Medium Cardinality Labels**:
- `proxy_vendor`: Fixed set of 3 vendors
- `protocol`: Limited to http/https
- `status_code`: Limited set of HTTP status codes

**Low Cardinality Labels**:
- `direction`: Only INGRESS/EGRESS

## Query Examples

### Business Intelligence Queries

#### 1. Proxy Vendor Usage Distribution
```promql
# Total requests per proxy vendor (last 5 minutes)
sum(rate(crawler_requests_total[5m])) by (proxy_vendor)

# Percentage distribution
sum(rate(crawler_requests_total[5m])) by (proxy_vendor) / 
sum(rate(crawler_requests_total[5m])) * 100
```

#### 2. Bandwidth Usage by Proxy
```promql
# Outbound bandwidth per proxy vendor (bytes/sec)
sum(rate(crawler_bytes_sent_total[5m])) by (proxy_vendor)

# Inbound bandwidth per proxy vendor (bytes/sec)
sum(rate(crawler_bytes_received_total[5m])) by (proxy_vendor)

# Total bandwidth per proxy vendor
sum(rate(crawler_bytes_sent_total[5m]) + rate(crawler_bytes_received_total[5m])) by (proxy_vendor)
```

#### 3. Top Destinations by Traffic
```promql
# Top 10 destinations by request count
topk(10, sum(rate(crawler_requests_total[5m])) by (destination_domain))

# Top 10 destinations by bandwidth
topk(10, sum(rate(crawler_bytes_sent_total[5m]) + rate(crawler_bytes_received_total[5m])) by (destination_domain))
```

#### 4. Performance Metrics
```promql
# 95th percentile response time by proxy vendor
histogram_quantile(0.95, sum(rate(crawler_request_duration_seconds_bucket[5m])) by (proxy_vendor, le))

# Error rate by proxy vendor
sum(rate(crawler_requests_total{status_code!~"2.."}[5m])) by (proxy_vendor) / 
sum(rate(crawler_requests_total[5m])) by (proxy_vendor) * 100
```

#### 5. Pod-level Analysis
```promql
# Requests per pod
sum(rate(crawler_requests_total[5m])) by (pod_name)

# Most active pods
topk(5, sum(rate(crawler_requests_total[5m])) by (pod_name))

# Pod resource utilization correlation
sum(rate(crawler_requests_total[5m])) by (pod_name) and on(pod_name) 
sum(rate(container_cpu_usage_seconds_total[5m])) by (pod_name)
```

## Alerting Rules

### Critical Alerts

#### High Error Rate
```yaml
- alert: HighProxyErrorRate
  expr: sum(rate(crawler_requests_total{status_code!~"2.."}[5m])) by (proxy_vendor) / sum(rate(crawler_requests_total[5m])) by (proxy_vendor) > 0.1
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "High error rate for proxy {{ $labels.proxy_vendor }}"
    description: "Proxy {{ $labels.proxy_vendor }} has error rate of {{ $value | humanizePercentage }}"
```

#### Proxy Vendor Down
```yaml
- alert: ProxyVendorDown
  expr: sum(rate(crawler_requests_total[5m])) by (proxy_vendor) == 0
  for: 10m
  labels:
    severity: critical
  annotations:
    summary: "Proxy vendor {{ $labels.proxy_vendor }} appears to be down"
```

### Warning Alerts

#### High Response Time
```yaml
- alert: HighResponseTime
  expr: histogram_quantile(0.95, sum(rate(crawler_request_duration_seconds_bucket[5m])) by (proxy_vendor, le)) > 5
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High response time for proxy {{ $labels.proxy_vendor }}"
```

## Data Export and Integration

### Supported Export Formats
- **Prometheus Remote Write**: For long-term storage
- **JSON API**: Real-time queries via Prometheus HTTP API
- **CSV Export**: Via Grafana dashboard export
- **Webhook Notifications**: Via Alertmanager

### Integration Points
- **External Monitoring**: Prometheus federation
- **Log Aggregation**: Structured logs via application
- **Business Intelligence**: Grafana API for dashboard embedding
- **Automation**: Prometheus API for programmatic access

## Schema Evolution

### Versioning Strategy
- Metric names include version prefix when breaking changes occur
- Backward compatibility maintained for 2 major versions
- Deprecation warnings provided 30 days before removal
