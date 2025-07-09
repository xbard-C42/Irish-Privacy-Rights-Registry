# Privacy Rights Registry - Environment Variables
# Copy this file to .env and update with your production values

# Security Configuration
SECRET_KEY=your-secret-key-change-this-in-production
MIN_PASSWORD_LENGTH=12
TOKEN_EXPIRY_DAYS=365

# Database Configuration
DATABASE_URL=postgresql://privacy_user:privacy_password@localhost:5432/privacy_registry
# For development: sqlite:///./privacy_registry.db

# Redis Configuration (for rate limiting)
REDIS_URL=redis://localhost:6379

# CORS and Security
ALLOWED_ORIGINS=https://privacy-registry.ireland.ie,https://api.privacy-registry.ireland.ie
RATE_LIMIT_REQUESTS=100/hour

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=False

# Irish Government Integration
OIREACHTAS_API_URL=https://api.oireachtas.ie
GDPR_COMPLIANCE_ENDPOINT=https://dataprotection.ie/api

# Email Configuration (for notifications)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@privacy-registry.ireland.ie

# Monitoring and Analytics
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
PROMETHEUS_PORT=9090

# Irish Data Protection Commission Integration
DPC_NOTIFICATION_ENDPOINT=https://forms.dataprotection.ie/
DPC_COMPLIANCE_WEBHOOK=https://your-domain.ie/webhooks/dpc

# Green Party Integration
GREEN_PARTY_API_KEY=your-green-party-api-key
GREEN_PARTY_WEBHOOK=https://greenparty.ie/webhooks/privacy-reports