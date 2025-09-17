# Proxy Usage Telemetry for Kubernetes Crawlers

## Architecture Overview

This solution provides comprehensive observability for outbound proxy usage from crawler pods in a Kubernetes cluster. The architecture consists of the following components:

### Components Stack
- **Minikube**: 2-node local Kubernetes cluster
- **Cilium + Hubble**: Network observability and traffic monitoring
- **Prometheus Stack**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **Python Load Generator**: Simulates crawler traffic through various proxies
- **Helm Charts**: Deployment and configuration management

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Minikube Cluster                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Node 1    │    │   Node 2    │    │  Control    │     │
│  │             │    │             │    │   Plane     │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
├─────────────────────────────────────────────────────────────┤
│                  Crawlers Namespace                         │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Crawler Pods (vendor-a, vendor-b, vendor-c proxies)    ││
│  │ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       ││
│  │ │Crawler-1│ │Crawler-2│ │Crawler-3│ │Crawler-N│  ...  ││
│  │ └─────────┘ └─────────┘ └─────────┘ └─────────┘       ││
│  └─────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│                Network Observability Layer                  │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Cilium CNI + Hubble (Network Flow Monitoring)          ││
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       ││
│  │ │Hubble Relay │ │Hubble Metrics│ │Cilium Agent │       ││
│  │ └─────────────┘ └─────────────┘ └─────────────┘       ││
│  └─────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│                  Monitoring Stack                           │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       ││
│  │ │ Prometheus  │ │  Grafana    │ │AlertManager │       ││
│  │ │   Server    │ │ Dashboards  │ │             │       ││
│  │ └─────────────┘ └─────────────┘ └─────────────┘       ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                   External Proxy Servers
                 (vendor-a, vendor-b, vendor-c)
                    http://65.108.203.37:18080
```

## Data Model & Schema

### Metrics Labels
- `source_pod`: Name of the crawler pod
- `source_namespace`: Always "crawlers"
- `proxy_vendor`: Vendor identifier (vendor-a, vendor-b, vendor-c)
- `destination_domain`: Target domain being crawled
- `destination_ip`: Target IP address
- `protocol`: HTTP/HTTPS
- `http_version`: HTTP/1.1 or HTTP/2

### Key Metrics
1. **Proxy Request Count**: `hubble_flows_total`
2. **Outbound Bytes**: `hubble_flows_bytes_total{direction="EGRESS"}`
3. **Inbound Bytes**: `hubble_flows_bytes_total{direction="INGRESS"}`
4. **Connection Duration**: `hubble_flows_duration_seconds`

## Prerequisites

- Docker Desktop or similar container runtime
- Minikube
- Helm 3.x
- kubectl

## Installation Instructions

### 1. Setup Minikube Cluster

```bash
# Start 2-node minikube cluster
minikube start --network-plugin=cni --cni=false --memory=4096 --nodes=2

# Verify cluster is running
kubectl get nodes
```

### 2. Install Cilium with Hubble

```bash
# install cilium (on mac)
brew install cilium-cli

# Install Cilium with Hubble enabled
cilium install \
  --helm-set hubble.enabled=true \
  --helm-set hubble.ui.enabled=true \
  --helm-set hubble.metrics.enabled="{dns,drop,tcp,flow,port-distribution,icmp,http}" \
  --helm-set prometheus.enabled=true \
  --helm-set operator.prometheus.enabled=true \
  --helm-set hubble.relay.enabled=true

# Wait for Cilium to be ready
cilium status --wait

```

### 3. Install Prometheus Stack

```bash
# Add Prometheus community helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install kube-prometheus-stack
helm install prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
  --set prometheus.prometheusSpec.podMonitorSelectorNilUsesHelmValues=false \
  --set grafana.adminPassword=admin123
```

### 4. Create ServiceMonitors for Hubble Metrics

```bash
# Apply ServiceMonitors for Hubble and Cilium metrics
kubectl apply -f k8s-manifests/hubble-servicemonitors.yaml
```

### 5. Build and Deploy Crawler Application

```bash
# Build Docker image
docker build -t timilsinamadhav/crawler-proxy-telemetry:latest .

# Load image into minikube
minikube image load timilsinamadhav/crawler-proxy-telemetry:latest

# Create crawlers namespace
kubectl create namespace crawlers

# Deploy crawler application using Helm
helm install crawler-app ./helm-charts/crawler-app --namespace crawlers
```

### 6. Access Dashboards

```bash
# Port-forward Grafana (default: admin/admin123)
kubectl port-forward -n monitoring svc/prometheus-stack-grafana 3000:80 &

# Port-forward Hubble UI
kubectl port-forward -n kube-system svc/hubble-ui 12000:80 &

# Port-forward Prometheus
kubectl port-forward -n monitoring svc/prometheus-stack-kube-prom-prometheus 9090:9090 &
```

### 7. Import Grafana Dashboard

1. **Open Grafana** in your browser: http://localhost:3000
2. **Login** with credentials: `admin` / `admin123`
3. **Navigate to Dashboard Import**:
   - Click the "+" icon in the left sidebar
   - Select "Import"
4. **Import the dashboard**:
   - Click "Upload JSON file"
   - Select `dashboards/proxy-usage-dashboard.json` from this project
   - Click "Load"
5. **Configure the dashboard**:
   - Leave the default settings
   - Click "Import"
6. **View the dashboard**:
   - The "Proxy Usage Telemetry Dashboard" will open
   - You should see metrics for request rates, bandwidth, and proxy vendor distribution

**Dashboard Features:**
- **Request Rate by Proxy Vendor**: Real-time request rates per proxy
- **Total Requests by Proxy Vendor**: Summary stats
- **Outbound/Inbound Bandwidth**: Traffic volume by proxy
- **Traffic Distribution by Destination**: Pie chart of target domains
- **Request Duration**: Response time percentiles
- **Detailed Traffic Breakdown**: Table view of all metrics

## Usage

### Starting Load Generation

```bash
# Scale up crawler pods
kubectl scale deployment crawler-app -n crawlers --replicas=10

# Monitor traffic in real-time
cilium hubble observe --namespace crawlers --follow

# Check metrics
curl http://localhost:9090/api/v1/query?query=hubble_flows_total
```

### Viewing Dashboards

1. **Grafana**: http://localhost:3000 (admin/admin123)
   - **Proxy Usage Telemetry Dashboard**: View imported dashboard for complete proxy analytics
   - **Built-in dashboards**: Kubernetes cluster metrics, node metrics, etc.
   
2. **Hubble UI**: http://localhost:12000
   - **Network Topology**: Visual representation of service communication
   - **Flow Logs**: Real-time network flows with filtering options
   
3. **Prometheus**: http://localhost:9090
   - **Query Interface**: Run PromQL queries for custom analysis
   - **Targets**: Verify all metrics endpoints are being scraped
   - **Rules**: View alerting and recording rules

## Validation

### Test Proxy Attribution

```bash
# Check if traffic is properly attributed to proxy vendors
kubectl logs -n crawlers -l app.kubernetes.io/name=crawler-app --tail=100

# Verify crawler metrics are collected
curl -s "http://localhost:9090/api/v1/query?query=rate(crawler_requests_total[5m])" | jq .

# Check Hubble metrics are available
curl -s "http://localhost:9090/api/v1/query?query=hubble_flows_total" | jq .

# Check bandwidth metrics
curl -s "http://localhost:9090/api/v1/query?query=rate(crawler_bytes_sent_total[5m])" | jq .
```

### Performance Validation

```bash
# Scale up to test performance
kubectl scale deployment crawler-app -n crawlers --replicas=20

# Wait for pods to be ready
kubectl rollout status deployment/crawler-app -n crawlers

# Check increased metrics
curl -s "http://localhost:9090/api/v1/query?query=sum(rate(crawler_requests_total[1m]))by(proxy_vendor)" | jq .
```

## Trade-offs and Design Decisions

### 1. Cilium + Hubble Choice
- **Pros**: 
  - Deep packet inspection at kernel level
  - No application code changes required
  - Supports HTTP/1.1, HTTP/2, and HTTPS
  - Rich metadata extraction
- **Cons**: 
  - Additional complexity
  - Resource overhead

### 2. Proxy Vendor Attribution Strategy
- **Method**: Use destination IP mapping to vendor
- **Reasoning**: Most reliable way to attribute traffic without application changes
- **Alternative**: Could use HTTP headers, but requires application modification

### 3. Metrics Granularity
- **Choice**: Pod-level granularity with vendor attribution
- **Reasoning**: Balances observability needs with storage requirements
- **Trade-off**: Higher cardinality metrics vs. detailed insights

## Troubleshooting

### Common Issues

2. **Metrics not appearing in Prometheus**:
   ```bash
   kubectl get servicemonitor -n kube-system
   ```

3. **Grafana dashboard not loading**:
   ```bash
   kubectl logs -n monitoring deployment/prometheus-stack-grafana
   ```

4. **Dashboard shows "No data" after import**:
   - Wait 2-3 minutes for metrics to be collected
   - Check if crawler pods are running: `kubectl get pods -n crawlers`
   - Verify ServiceMonitors: `kubectl get servicemonitor -n monitoring`
   - Check Prometheus targets: http://localhost:9090/targets

5. **Dashboard import fails**:
   - Ensure you're using the correct JSON file: `dashboards/proxy-usage-dashboard.json`
   - Try copying the JSON content and pasting it directly in Grafana import
   - Check Grafana version compatibility (tested with Grafana 9.x+)

## Cleanup

```bash
# Remove all components
helm uninstall crawler-app -n crawlers
helm uninstall prometheus-stack -n monitoring
kubectl delete -f k8s-manifests/hubble-servicemonitors.yaml
cilium uninstall
kubectl delete namespace crawlers monitoring
minikube delete
```
