# Production Deployment Guide

## Overview
This guide covers deploying the Insurance Eligibility Agent to production environments.

## Prerequisites
- Python 3.9+
- OpenAI API Key
- Production server (AWS EC2, Azure VM, GCP Compute, etc.)
- Domain name (optional but recommended)
- SSL certificate (Let's Encrypt recommended)

## Deployment Options

### Option 1: Docker Deployment (Recommended)

#### 1. Create Dockerfiles

**Backend Dockerfile** (`backend/Dockerfile`):
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application code
COPY . .

# Expose port
EXPOSE 5000

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"]
```

**Frontend Dockerfile** (`frontend/Dockerfile`):
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8501

# Run streamlit
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

**Docker Compose** (`docker-compose.yml`):
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "5000:5000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - FLASK_ENV=production
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build: ./frontend
    ports:
      - "8501:8501"
    environment:
      - API_BASE_URL=http://backend:5000/api
    depends_on:
      - backend
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - frontend
      - backend
    restart: unless-stopped
```

#### 2. Deploy with Docker

```bash
# Set environment variables
export OPENAI_API_KEY=your-key-here

# Build and start services
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Option 2: Traditional Deployment

#### Backend (Flask with Gunicorn)

**Install on server:**
```bash
# Install Python and dependencies
sudo apt-get update
sudo apt-get install python3.9 python3-pip nginx

# Create application user
sudo useradd -m -s /bin/bash eligibility-agent

# Copy files
sudo cp -r backend /home/eligibility-agent/
sudo chown -R eligibility-agent:eligibility-agent /home/eligibility-agent/

# Switch to app user
sudo su - eligibility-agent

# Create virtual environment
cd /home/eligibility-agent/backend
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt gunicorn

# Create .env file
cat > .env << EOF
OPENAI_API_KEY=your-key-here
FLASK_ENV=production
EOF
```

**Create systemd service** (`/etc/systemd/system/eligibility-backend.service`):
```ini
[Unit]
Description=Insurance Eligibility Backend
After=network.target

[Service]
User=eligibility-agent
Group=eligibility-agent
WorkingDirectory=/home/eligibility-agent/backend
Environment="PATH=/home/eligibility-agent/backend/venv/bin"
ExecStart=/home/eligibility-agent/backend/venv/bin/gunicorn \
    --bind 127.0.0.1:5000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile /var/log/eligibility-backend/access.log \
    --error-logfile /var/log/eligibility-backend/error.log \
    app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

**Start service:**
```bash
sudo systemctl daemon-reload
sudo systemctl start eligibility-backend
sudo systemctl enable eligibility-backend
sudo systemctl status eligibility-backend
```

#### Frontend (Streamlit)

**Create systemd service** (`/etc/systemd/system/eligibility-frontend.service`):
```ini
[Unit]
Description=Insurance Eligibility Frontend
After=network.target

[Service]
User=eligibility-agent
Group=eligibility-agent
WorkingDirectory=/home/eligibility-agent/frontend
Environment="PATH=/home/eligibility-agent/frontend/venv/bin"
ExecStart=/home/eligibility-agent/frontend/venv/bin/streamlit run streamlit_app.py \
    --server.port=8501 \
    --server.address=127.0.0.1
Restart=always

[Install]
WantedBy=multi-user.target
```

### Nginx Configuration

**Create nginx config** (`/etc/nginx/sites-available/eligibility-agent`):
```nginx
upstream backend {
    server 127.0.0.1:5000;
}

upstream frontend {
    server 127.0.0.1:8501;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS Server
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    # Backend API
    location /api {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check
    location /health {
        proxy_pass http://backend;
    }
}
```

**Enable site:**
```bash
sudo ln -s /etc/nginx/sites-available/eligibility-agent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Database Integration (Optional)

For production, consider adding PostgreSQL for conversation persistence:

**Install PostgreSQL:**
```bash
sudo apt-get install postgresql postgresql-contrib
```

**Create database:**
```sql
CREATE DATABASE eligibility_agent;
CREATE USER eligibility_user WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE eligibility_agent TO eligibility_user;
```

**Update backend to use PostgreSQL** (add to `requirements.txt`):
```
psycopg2-binary==2.9.9
sqlalchemy==2.0.25
```

## Environment Variables for Production

**Backend (.env):**
```bash
# API Keys
OPENAI_API_KEY=your-production-key

# Flask
FLASK_ENV=production
SECRET_KEY=generate-a-random-secret-key

# Database (if using)
DATABASE_URL=postgresql://eligibility_user:password@localhost/eligibility_agent

# Redis (for session management)
REDIS_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/eligibility-backend/app.log

# Security
ALLOWED_ORIGINS=https://your-domain.com
MAX_CONTENT_LENGTH=16777216  # 16MB

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
```

## Monitoring & Logging

### Setup Logging

**Add to `backend/app.py`:**
```python
import logging
from logging.handlers import RotatingFileHandler

if not app.debug:
    file_handler = RotatingFileHandler(
        'logs/eligibility-agent.log',
        maxBytes=10240000,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Eligibility Agent startup')
```

### Monitoring Tools

1. **Application Monitoring:**
   - Sentry for error tracking
   - New Relic or DataDog for APM
   - Prometheus + Grafana for metrics

2. **Infrastructure Monitoring:**
   - CloudWatch (AWS)
   - Azure Monitor
   - Google Cloud Monitoring

## Security Hardening

### 1. API Security

**Add authentication** (JWT example):
```python
from flask_jwt_extended import JWTManager, jwt_required

app.config['JWT_SECRET_KEY'] = os.getenv('SECRET_KEY')
jwt = JWTManager(app)

@app.route("/api/conversation/start", methods=["POST"])
@jwt_required()
def start_conversation():
    # Your code here
    pass
```

### 2. Rate Limiting

**Add Flask-Limiter:**
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route("/api/conversation/start", methods=["POST"])
@limiter.limit("10 per minute")
def start_conversation():
    # Your code here
    pass
```

### 3. Input Validation

**Add request validation:**
```python
from pydantic import BaseModel, validator

class ConversationStartRequest(BaseModel):
    initial_message: str
    
    @validator('initial_message')
    def message_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Message cannot be empty')
        if len(v) > 1000:
            raise ValueError('Message too long')
        return v
```

## Backup & Recovery

**Automated backups:**
```bash
#!/bin/bash
# /home/eligibility-agent/backup.sh

BACKUP_DIR=/backups/eligibility-agent
DATE=$(date +%Y%m%d_%H%M%S)

# Backup database
pg_dump eligibility_agent > $BACKUP_DIR/db_$DATE.sql

# Backup application files
tar -czf $BACKUP_DIR/app_$DATE.tar.gz /home/eligibility-agent/

# Keep only last 7 days
find $BACKUP_DIR -type f -mtime +7 -delete
```

**Add to crontab:**
```bash
0 2 * * * /home/eligibility-agent/backup.sh
```

## Scaling Considerations

### Horizontal Scaling

**Load Balancer Configuration:**
```nginx
upstream backend_servers {
    least_conn;
    server backend1.internal:5000;
    server backend2.internal:5000;
    server backend3.internal:5000;
}
```

### Auto-scaling (AWS Example)

**Use AWS ECS with auto-scaling:**
- Min instances: 2
- Max instances: 10
- Target CPU: 70%
- Scale up: +2 instances when > 70% for 2 minutes
- Scale down: -1 instance when < 30% for 5 minutes

## Health Checks

**Enhanced health check endpoint:**
```python
@app.route("/health", methods=["GET"])
def health_check():
    checks = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "database": check_database(),
            "redis": check_redis(),
            "openai": check_openai_api(),
            "disk_space": check_disk_space()
        }
    }
    
    overall_status = all(checks["checks"].values())
    status_code = 200 if overall_status else 503
    
    return jsonify(checks), status_code
```

## Disaster Recovery Plan

1. **Backup frequency:** Daily automated backups
2. **Backup retention:** 30 days
3. **Recovery Time Objective (RTO):** 4 hours
4. **Recovery Point Objective (RPO):** 24 hours
5. **Failover procedure:** Document step-by-step recovery

## Cost Optimization

1. **Use reserved instances** for predictable workloads
2. **Implement caching** to reduce API calls
3. **Optimize database queries**
4. **Use CDN** for static assets
5. **Monitor and optimize** OpenAI API usage

## Compliance & Auditing

### HIPAA Compliance Checklist

- [ ] Enable encryption at rest
- [ ] Enable encryption in transit (HTTPS)
- [ ] Implement audit logging
- [ ] Add user authentication
- [ ] Implement access controls
- [ ] Regular security assessments
- [ ] Business Associate Agreement with cloud provider
- [ ] Data retention policies
- [ ] Incident response plan

### Audit Logging

**Add comprehensive logging:**
```python
@app.route("/api/conversation/start", methods=["POST"])
def start_conversation():
    audit_log = {
        "timestamp": datetime.now().isoformat(),
        "user_id": get_user_id(),
        "action": "conversation_start",
        "ip_address": request.remote_addr,
        "user_agent": request.user_agent.string
    }
    logger.info(json.dumps(audit_log))
    # Your code here
```

## Support & Maintenance

1. **Monitor error rates** and set up alerts
2. **Review logs** daily
3. **Update dependencies** monthly
4. **Security patches** within 48 hours
5. **Performance testing** quarterly
6. **Disaster recovery drills** bi-annually

---

**Remember:** This is a healthcare application dealing with sensitive patient data. Always prioritize security and compliance.
