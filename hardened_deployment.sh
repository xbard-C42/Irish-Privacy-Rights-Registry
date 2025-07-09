#!/bin/bash

# Privacy Rights Registry - Production-Ready Deployment Script
# Now with security hardening, secrets management, and operational improvements

echo "🔒 Privacy Rights Registry - Production Deployment"
echo "================================================"

# Check prerequisites
check_prerequisites() {
    echo "📋 Checking prerequisites..."
    
    command -v python3 >/dev/null || { 
        echo "❌ Python 3 is required but not installed. Please install Python 3.9+"; 
        exit 1; 
    }
    
    command -v docker >/dev/null || { 
        echo "⚠️  Docker not found. Some deployment options will be unavailable."; 
    }
    
    command -v redis-server >/dev/null || { 
        echo "⚠️  Redis not found. Rate limiting will use in-memory storage."; 
    }
    
    echo "✅ Prerequisites check complete"
}

# Create project structure
setup_project() {
    echo "📁 Setting up project structure..."
    
    # Create directories
    mkdir -p privacy-registry/{migrations,tests,config,logs,scripts}
    cd privacy-registry
    
    echo "✅ Project structure created"
}

# Create enhanced requirements.txt
create_requirements() {
    [[ -f requirements.txt ]] || cat > requirements.txt << 'EOF'
# Core FastAPI and server
fastapi==0.104.1
uvicorn[standard]==0.24.0

# Database and ORM
sqlalchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.9

# Authentication and security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# Validation and configuration
pydantic[email]==2.5.0
python-dotenv==1.0.0

# Rate limiting and caching
slowapi==0.1.9
redis==5.0.1

# Logging and monitoring
loguru==0.7.2

# Development and testing
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2
EOF
}

# Create secure configuration
create_config() {
    [[ -f .env.example ]] || cat > .env.example << 'EOF'
# Security
SECRET_KEY=your-secret-key-change-this-in-production
MIN_PASSWORD_LENGTH=12
TOKEN_EXPIRY_DAYS=365

# Database
DATABASE_URL=postgresql://user:password@localhost/privacy_registry
# For development: sqlite:///./privacy_registry.db

# Redis (for rate limiting)
REDIS_URL=redis://localhost:6379

# CORS and security
ALLOWED_ORIGINS=https://your-frontend-domain.com,https://your-api-domain.com
RATE_LIMIT_REQUESTS=100/hour

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO
EOF

    [[ -f .env ]] || cat > .env << 'EOF'
# Development configuration
SECRET_KEY=dev-secret-key-change-in-production
MIN_PASSWORD_LENGTH=8
TOKEN_EXPIRY_DAYS=365
DATABASE_URL=sqlite:///./privacy_registry.db
REDIS_URL=redis://localhost:6379
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
RATE_LIMIT_REQUESTS=100/hour
ENVIRONMENT=development
LOG_LEVEL=DEBUG
EOF

    echo "✅ Configuration files created"
}

# Create Alembic migration setup
create_migrations() {
    [[ -f alembic.ini ]] || cat > alembic.ini << 'EOF'
[alembic]
script_location = migrations
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = 

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
EOF

    [[ -f migrations/env.py ]] || mkdir -p migrations && cat > migrations/env.py << 'EOF'
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Import your models
from main import Base
from dotenv import load_dotenv

load_dotenv()

config = context.config
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
EOF

    [[ -f migrations/script.py.mako ]] || cat > migrations/script.py.mako << 'EOF'
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}

def upgrade() -> None:
    ${upgrades if upgrades else "pass"}

def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
EOF

    echo "✅ Alembic migration setup created"
}

# Create production-ready Docker setup
create_docker() {
    [[ -f Dockerfile ]] || cat > Dockerfile << 'EOF'
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    redis-tools \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash privacy

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .
RUN chown -R privacy:privacy /app

# Switch to non-root user
USER privacy

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/v1/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

    [[ -f docker-compose.yml ]] || cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://privacy:privacy@db:5432/privacy_registry
      - REDIS_URL=redis://redis:6379
      - SECRET_KEY=${SECRET_KEY:-change-this-in-production}
      - ENVIRONMENT=production
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=privacy_registry
      - POSTGRES_USER=privacy
      - POSTGRES_PASSWORD=privacy
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
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
      - api
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
EOF

    [[ -f nginx.conf ]] || cat > nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream api {
        server api:8000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=registration:10m rate=1r/m;

    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

        location /v1/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /v1/register {
            limit_req zone=registration burst=5 nodelay;
            proxy_pass http://api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF

    echo "✅ Docker configuration created"
}

# Create comprehensive test suite
create_tests() {
    [[ -f tests/test_main.py ]] || cat > tests/test_main.py << 'EOF'
import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from main import app
import json

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
async def async_client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] in ["healthy", "degraded"]

def test_user_registration(client):
    """Test user registration with strong password"""
    user_data = {
        "email": "test@example.com",
        "password": "StrongPass123!",
        "rights": {
            "erasure": True,
            "no_sale": True,
            "no_profiling": False,
            "no_marketing": True,
            "data_portability": True,
            "access_request": True,
            "anti_doxxing": True
        }
    }
    
    response = client.post("/v1/register", json=user_data)
    assert response.status_code == 201
    data = response.json()
    assert "token" in data
    assert data["rights"]["anti_doxxing"] is True

def test_weak_password_rejection(client):
    """Test that weak passwords are rejected"""
    user_data = {
        "email": "test@example.com",
        "password": "weak",
        "rights": {"erasure": True}
    }
    
    response = client.post("/v1/register", json=user_data)
    assert response.status_code == 422  # Validation error

def test_company_registration(client):
    """Test company registration"""
    company_data = {
        "name": "Test Company Ltd",
        "contact_email": "legal@testcompany.com"
    }
    
    response = client.post("/v1/company/register", json=company_data)
    assert response.status_code == 201
    data = response.json()
    assert "api_key" in data
    assert data["api_key"].startswith("prr_")

def test_anti_doxxing_protection(client):
    """Test that anti-doxxing protection blocks lookups"""
    # Register user with anti-doxxing protection
    user_data = {
        "email": "protected@example.com",
        "password": "StrongPass123!",
        "rights": {"anti_doxxing": True}
    }
    
    user_response = client.post("/v1/register", json=user_data)
    assert user_response.status_code == 201
    token = user_response.json()["token"]
    
    # Register company
    company_data = {
        "name": "Test Company",
        "contact_email": "test@company.com"
    }
    
    company_response = client.post("/v1/company/register", json=company_data)
    assert company_response.status_code == 201
    api_key = company_response.json()["api_key"]
    
    # Try to lookup protected user - should be blocked
    headers = {"Authorization": f"Bearer {api_key}"}
    lookup_response = client.get(f"/v1/registry/{token}", headers=headers)
    assert lookup_response.status_code == 403
    assert "anti-doxxing protection" in lookup_response.json()["detail"]

def test_transparency_endpoints(client):
    """Test transparency endpoints"""
    # Global transparency
    response = client.get("/v1/transparency/global")
    assert response.status_code == 200
    data = response.json()
    assert "total_users" in data
    assert "blocked_lookups" in data
    assert "protection_rate" in data

@pytest.mark.asyncio
async def test_rate_limiting():
    """Test rate limiting on sensitive endpoints"""
    # This would require more sophisticated testing with multiple requests
    # Implementation depends on your rate limiting strategy
    pass

if __name__ == "__main__":
    pytest.main([__file__])
EOF

    echo "✅ Test suite created"
}

# Create deployment scripts
create_scripts() {
    [[ -f scripts/setup.sh ]] || cat > scripts/setup.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 Setting up Privacy Rights Registry..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp .env.example .env
    echo "📝 Please edit .env with your production values"
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Initialize database migrations
echo "🗄️  Setting up database migrations..."
alembic revision --autogenerate -m "Initial migration"

# Run migrations
echo "🔄 Running database migrations..."
alembic upgrade head

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your production values"
echo "2. Run: ./scripts/run.sh"
echo "3. Test: python -m pytest tests/"
echo "4. Visit: http://localhost:8000/v1/docs"
EOF

    [[ -f scripts/run.sh ]] || cat > scripts/run.sh << 'EOF'
#!/bin/bash
set -e

# Load environment variables
if [ -f .env ]; then
    source .env
fi

# Activate virtual environment
source venv/bin/activate

# Run migrations
echo "🔄 Running database migrations..."
alembic upgrade head

# Start the server
echo "🚀 Starting Privacy Rights Registry..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level info
EOF

    [[ -f scripts/deploy.sh ]] || cat > scripts/deploy.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 Deploying Privacy Rights Registry to production..."

# Build and deploy with Docker
echo "🐳 Building Docker containers..."
docker-compose build

echo "🔄 Starting services..."
docker-compose up -d

echo "⏳ Waiting for services to be ready..."
sleep 10

echo "🔄 Running database migrations..."
docker-compose exec api alembic upgrade head

echo "🧪 Running health check..."
curl -f http://localhost:8000/v1/health

echo "✅ Deployment complete!"
echo ""
echo "Services available at:"
echo "- API: http://localhost:8000"
echo "- API Docs: http://localhost:8000/v1/docs"
echo "- Database: localhost:5432"
echo "- Redis: localhost:6379"
EOF

    chmod +x scripts/*.sh
    echo "✅ Deployment scripts created"
}

# Create comprehensive README
create_readme() {
    [[ -f README.md ]] || cat > README.md << 'EOF'
# Privacy Rights Registry

A production-ready registry for individuals to declare their privacy rights, creating legal due diligence obligations for companies and preventing stalking/doxxing attacks.

## 🔒 Security Features

- **Rate limiting** on all endpoints
- **Strong password requirements** with validation
- **Anti-doxxing protection** that blocks data lookups
- **Comprehensive audit logging** with IP tracking
- **API key authentication** for companies
- **CORS protection** and security headers
- **Database migrations** for safe schema changes

## 🚀 Quick Start

1. **Setup**: `./scripts/setup.sh`
2. **Configure**: Edit `.env` with your values
3. **Run**: `./scripts/run.sh`
4. **Test**: `python -m pytest tests/`
5. **Deploy**: `./scripts/deploy.sh`

## 📡 API Endpoints

### User Endpoints
- `POST /v1/register` - Register privacy rights
- `POST /v1/violations/report` - Report privacy violations

### Company Endpoints
- `POST /v1/company/register` - Register for API access
- `GET /v1/registry/{token}` - Look up user rights (requires API key)
- `POST /v1/audit/log` - Log compliance actions

### Transparency Endpoints
- `GET /v1/transparency/global` - Global registry statistics
- `GET /v1/transparency/company/{id}` - Company compliance stats

## 🛡️ Anti-Doxxing Protection

When users enable anti-doxxing protection:
- **Data lookups are blocked** with 403 responses
- **Attempts are logged** for transparency
- **Companies become liable** for ignoring registry checks
- **Stalking/harassment is prevented** at the infrastructure level

## 🏗️ Legal Framework

This registry creates **legal liability** for companies that:
1. Process personal data without checking the registry
2. Ignore registered privacy rights
3. Enable stalking/harassment through data sales

**The registry makes "we didn't know" legally indefensible.**

## 🔧 Configuration

Key environment variables:
- `SECRET_KEY` - JWT signing key (change in production!)
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection for rate limiting
- `ALLOWED_ORIGINS` - CORS allowed origins
- `MIN_PASSWORD_LENGTH` - Minimum password length (default: 12)

## 🐳 Docker Deployment

```bash
# Development
docker-compose up -d

# Production (with nginx, SSL)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 📊 Monitoring

- **Health check**: `/v1/health`
- **Logs**: Check `logs/` directory
- **Metrics**: Prometheus-compatible metrics (optional)
- **Audit trail**: Complete audit logs in database

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/

# Test specific functionality
python -m pytest tests/test_main.py::test_anti_doxxing_protection

# Load testing
# Install: pip install locust
# Run: locust -f tests/load_test.py --host=http://localhost:8000
```

## 📈 Scaling

- **Database**: Use PostgreSQL with read replicas
- **Caching**: Redis for rate limiting and session storage
- **Load balancing**: nginx with multiple API instances
- **Monitoring**: Add Prometheus + Grafana

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🚨 Important Notes

- **Change the SECRET_KEY** in production
- **Use HTTPS** for all production deployments
- **Backup your database** regularly
- **Monitor logs** for security events
- **Update dependencies** regularly

## 🔗 Related Projects

- [C42 OS](https://c42os.com) - Privacy-first operating system
- [Consciousness Council](https://github.com/xbard-C42/consciousness-council) - Multi-agent AI democracy

---

**The faster this exists, the faster "we didn't know" becomes "we couldn't be bothered to check" in court.**
EOF

    echo "✅ README created"
}

# Main execution
main() {
    check_prerequisites
    setup_project
    create_requirements
    create_config
    create_migrations
    create_docker
    create_tests
    create_scripts
    create_readme
    
    echo ""
    echo "🎉 Privacy Rights Registry - Production Setup Complete!"
    echo "=================================================="
    echo ""
    echo "📋 Next steps:"
    echo "1. cd privacy-registry"
    echo "2. Copy the hardened API code into main.py"
    echo "3. Edit .env with your production values"
    echo "4. Run: ./scripts/setup.sh"
    echo "5. Run: ./scripts/run.sh"
    echo "6. Visit: http://localhost:8000/v1/docs"
    echo ""
    echo "🚀 Ready to deploy privacy rights infrastructure!"
    echo "💡 Remember: Change SECRET_KEY in production!"
}

main "$@"
