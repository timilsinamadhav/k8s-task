# Microservices Application

A DevOps solution for a microservices application featuring API service (Node.js), Worker service (Python), Frontend (React), and PostgreSQL database with complete CI/CD pipeline and Kubernetes deployment using Helm.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Service   │    │  Worker Service │
│   (React +      │───▶│   (Node.js +    │───▶│   (Python +     │
│   Nginx)        │    │   Express)      │    │   PostgreSQL)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        │
                       ┌─────────────────┐               │
                       │   PostgreSQL    │◀──────────────┘
                       │   Database      │
                       └─────────────────┘
```

## 🚀 Services Overview

- **API Service**: Node.js/Express with PostgreSQL, health checks, CORS, rate limiting
- **Worker Service**: Python background worker with database logging and structured logging
- **Frontend Service**: React with modern UI, served via Nginx in production
- **Database**: PostgreSQL 15 with persistent storage and initialization scripts

## 🛠️ Local Development Setup

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)

### Quick Start with Docker Compose

1. **Clone and setup**
   ```bash
   git clone <repository-url>
   cd microservices-app
   cp env.example .env
   ```

2. **Start all services**
   ```bash
   docker-compose up -d
   ```

3. **Access the application**
   - Frontend: http://localhost:8080
   - API: http://localhost:3000
   - Database: localhost:5432

### Environment Variables

Create a `.env` file:

```env
# Database Configuration
DB_NAME=microservices_db
DB_USER=postgres
DB_PASSWORD=password
DB_PORT=5432

# Service Ports
API_PORT=3000
FRONTEND_PORT=8080

# Worker Configuration
WORKER_INTERVAL=30

# Environment
NODE_ENV=development
```

### Development Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f [service-name]

# Stop all services
docker-compose down

# Rebuild services
docker-compose build
```

## ☸️ Kubernetes Deployment with Helm

### Prerequisites
- Kubernetes cluster (local or cloud)
- Helm 3.x installed
- kubectl configured

### Deployment Steps

1. **Deploy with Helm**
   ```bash
   # Create namespace
   kubectl create namespace microservices

   # Install with default values
   helm install microservices-app ./helm-chart -n microservices

   # Or install with custom values
   helm install microservices-app ./helm-chart -n microservices \
     --set environment=production \
     --set apiService.replicaCount=3 \
     --set database.persistence.size=20Gi
   ```

2. **Verify deployment**
   ```bash
   kubectl get pods -n microservices
   kubectl get services -n microservices
   ```

### Environment-specific Deployments

**Development**
```bash
helm install microservices-app ./helm-chart \
  --set environment=development \
  --set apiService.replicaCount=1 \
  --set database.persistence.size=2Gi
```

**Production**
```bash
helm install microservices-app ./helm-chart \
  --set environment=production \
  --set apiService.replicaCount=3 \
  --set apiService.autoscaling.enabled=true \
  --set database.persistence.size=50Gi
```

### Helm Management Commands

```bash
# List releases
helm list -n microservices

# Upgrade release
helm upgrade microservices-app ./helm-chart -n microservices

# Get release history
helm history microservices-app -n microservices

# Uninstall release
helm uninstall microservices-app -n microservices
```

### 🔄 Rollback Instructions

#### Quick Rollback (to previous version)
```bash
# Rollback to the previous release
helm rollback microservices-app -n microservices

# Rollback with wait and timeout
helm rollback microservices-app -n microservices --wait --timeout=10m
```

#### Rollback to Specific Version
```bash
# Check release history
helm history microservices-app -n microservices

# Rollback to specific revision (e.g., revision 2)
helm rollback microservices-app 2 -n microservices --wait --timeout=10m
```

#### Verify Rollback
```bash
# Check status after rollback
helm status microservices-app -n microservices

# Verify pods are running
kubectl get pods -n microservices -l app.kubernetes.io/instance=microservices-app

# View recent events
kubectl get events -n microservices --sort-by='.lastTimestamp' | tail -10
```

> **Note**: Helm rollbacks revert your application to the previous configuration. Database data is preserved as it uses persistent volumes.

## 🔄 CI/CD Pipeline

### Simplified GitHub Actions Workflow

#### **For Pull Requests:**
- Runs tests for all services (API, Worker, Frontend)
- Validates code quality

#### **For Main Branch Pushes:**
1. **Build Phase** - Builds Docker images with timestamp and git SHA tags
2. **Push Phase** - Pushes images to DockerHub registry  
3. **Deploy Phase** - Deploys to Kubernetes using Helm with atomic upgrades

### Required GitHub Secrets

```bash
DOCKERHUB_TOKEN    # DockerHub access token for pushing images
KUBECONFIG        # Base64 encoded kubeconfig file for Kubernetes access
```

### Using the CI/CD Pipeline

1. **Setup Secrets** in GitHub repository:
   ```bash
   # Generate DockerHub token at https://hub.docker.com/settings/security
   DOCKERHUB_TOKEN: your_dockerhub_token
   
   # Get kubeconfig and base64 encode it
   KUBECONFIG: $(cat ~/.kube/config | base64 -w 0)
   ```

2. **Trigger Deployment**:
   ```bash
   # Push to main branch triggers automatic deployment
   git add .
   git commit -m "Deploy new features"
   git push origin main
   ```

3. **Monitor Deployment**:
   - Check GitHub Actions tab for pipeline status
   - Monitor Kubernetes: `kubectl get pods -n default`

## 🗄️ Database Persistence

### Local Development
- Uses Docker volume `microservices_postgres_data`
- Data persists between container restarts

### Kubernetes
- Uses PersistentVolumeClaim for data persistence
- Configurable storage class and size
- Automatic initialization with sample data

## 🔧 Troubleshooting

### Common Issues

**Services not starting**
```bash
# Check logs
docker-compose logs [service-name]
kubectl logs -f deployment/microservices-app-api -n microservices
```

**Database connection issues**
```bash
# Test database connectivity
docker-compose exec database psql -U postgres -d microservices_db -c "SELECT 1;"
```

**Kubernetes deployment issues**
```bash
# Check pod status and events
kubectl get pods -n microservices
kubectl get events -n microservices --sort-by='.lastTimestamp'
```

### Health Checks

All services include health check endpoints:
- **API Service**: `GET /health`
- **Frontend**: `GET /health`
- **Database**: PostgreSQL `pg_isready`

## 🔒 Security Features

- Non-root user execution in containers
- Security contexts in Kubernetes
- Rate limiting and CORS configuration
- Environment variable injection for secrets
- Minimal base images (Alpine)

---

**Built with Docker, Kubernetes, and Helm**