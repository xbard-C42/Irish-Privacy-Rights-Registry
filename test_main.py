"""
Privacy Rights Registry - API Tests
Test suite for the Irish Privacy Rights Registry API

This test suite validates:
- User registration and privacy rights management
- Anti-doxxing protection enforcement
- Company registration and API key management
- Transparency and compliance reporting
- GDPR/Irish Data Protection law compliance
"""

import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
from datetime import datetime, timedelta

# Import the main application
from main import app, get_db, Settings


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create an async test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    return Settings(
        SECRET_KEY="test-secret-key",
        DATABASE_URL="sqlite:///./test.db",
        REDIS_URL="redis://localhost:6379",
        ALLOWED_ORIGINS=["http://localhost:3000"],
        MIN_PASSWORD_LENGTH=8,
        TOKEN_EXPIRY_DAYS=365,
        RATE_LIMIT_REQUESTS="100/hour"
    )


class TestHealthCheck:
    """Test health check endpoint"""
    
    def test_health_check_success(self, client):
        """Test successful health check"""
        response = client.get("/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "timestamp" in data
        assert "version" in data


class TestUserRegistration:
    """Test user registration and privacy rights management"""
    
    def test_user_registration_success(self, client):
        """Test successful user registration with strong password"""
        user_data = {
            "email": "test@example.ie",
            "password": "StrongPass123!",
            "rights": {
                "erasure": True,
                "no_sale": True,
                "no_profiling": False,
                "no_marketing": True,
                "data_portability": True,
                "access_request": True,
                "anti_doxxing": True  # Anti-doxxing protection enabled
            }
        }
        
        response = client.post("/v1/register", json=user_data)
        assert response.status_code == 201
        data = response.json()
        
        # Verify response structure
        assert "token" in data
        assert "rights" in data
        assert "expires_at" in data
        assert data["rights"]["anti_doxxing"] is True
        assert data["message"] == "User registered successfully"
    
    def test_user_registration_weak_password(self, client):
        """Test that weak passwords are rejected"""
        user_data = {
            "email": "test@example.ie",
            "password": "weak",
            "rights": {"erasure": True}
        }
        
        response = client.post("/v1/register", json=user_data)
        assert response.status_code == 422  # Validation error
        
        # Test common password rejection
        user_data["password"] = "password"
        response = client.post("/v1/register", json=user_data)
        assert response.status_code == 422
    
    def test_user_registration_duplicate_email(self, client):
        """Test duplicate email registration prevention"""
        user_data = {
            "email": "duplicate@example.ie",
            "password": "StrongPass123!",
            "rights": {"erasure": True}
        }
        
        # First registration should succeed
        response = client.post("/v1/register", json=user_data)
        assert response.status_code == 201
        
        # Second registration should fail
        response = client.post("/v1/register", json=user_data)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]


class TestCompanyRegistration:
    """Test company registration and API key management"""
    
    def test_company_registration_success(self, client):
        """Test successful company registration"""
        company_data = {
            "name": "Test Company Ltd",
            "contact_email": "legal@testcompany.ie"
        }
        
        response = client.post("/v1/company/register", json=company_data)
        assert response.status_code == 201
        data = response.json()
        
        # Verify response structure
        assert "api_key" in data
        assert "company_id" in data
        assert data["name"] == "Test Company Ltd"
        assert data["api_key"].startswith("prr_")  # Prefixed API key
        assert "Store this API key securely" in data["note"]
    
    def test_company_registration_duplicate_email(self, client):
        """Test duplicate company email prevention"""
        company_data = {
            "name": "Duplicate Company",
            "contact_email": "duplicate@company.ie"
        }
        
        # First registration should succeed
        response = client.post("/v1/company/register", json=company_data)
        assert response.status_code == 201
        
        # Second registration should fail
        response = client.post("/v1/company/register", json=company_data)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]


class TestAntiDoxxingProtection:
    """Test anti-doxxing protection enforcement"""
    
    def test_anti_doxxing_blocks_lookup(self, client):
        """Test that anti-doxxing protection blocks data lookups"""
        # Register user with anti-doxxing protection
        user_data = {
            "email": "protected@example.ie",
            "password": "StrongPass123!",
            "rights": {"anti_doxxing": True}
        }
        
        user_response = client.post("/v1/register", json=user_data)
        assert user_response.status_code == 201
        token = user_response.json()["token"]
        
        # Register company
        company_data = {
            "name": "Test Company",
            "contact_email": "test@company.ie"
        }
        
        company_response = client.post("/v1/company/register", json=company_data)
        assert company_response.status_code == 201
        api_key = company_response.json()["api_key"]
        
        # Try to lookup protected user - should be blocked
        headers = {"Authorization": f"Bearer {api_key}"}
        lookup_response = client.get(f"/v1/registry/{token}", headers=headers)
        
        assert lookup_response.status_code == 403
        assert "anti-doxxing protection" in lookup_response.json()["detail"]
        assert "stalking/harassment" in lookup_response.json()["detail"]
    
    def test_normal_lookup_without_protection(self, client):
        """Test normal lookup for users without anti-doxxing protection"""
        # Register user WITHOUT anti-doxxing protection
        user_data = {
            "email": "unprotected@example.ie",
            "password": "StrongPass123!",
            "rights": {"anti_doxxing": False, "erasure": True}
        }
        
        user_response = client.post("/v1/register", json=user_data)
        assert user_response.status_code == 201
        token = user_response.json()["token"]
        
        # Register company
        company_data = {
            "name": "Test Company",
            "contact_email": "test@company.ie"
        }
        
        company_response = client.post("/v1/company/register", json=company_data)
        assert company_response.status_code == 201
        api_key = company_response.json()["api_key"]
        
        # Lookup should succeed
        headers = {"Authorization": f"Bearer {api_key}"}
        lookup_response = client.get(f"/v1/registry/{token}", headers=headers)
        
        assert lookup_response.status_code == 200
        data = lookup_response.json()
        assert data["token_valid"] is True
        assert "rights" in data
        assert data["rights"]["erasure"] is True


class TestTransparencyReporting:
    """Test transparency and compliance reporting"""
    
    def test_global_transparency_endpoint(self, client):
        """Test global transparency statistics"""
        response = client.get("/v1/transparency/global")
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        required_fields = [
            "total_users", "total_companies", "total_lookups",
            "blocked_lookups", "protection_rate", "users_with_anti_doxxing",
            "anti_doxxing_adoption", "violations_reported"
        ]
        
        for field in required_fields:
            assert field in data
            assert isinstance(data[field], (int, float))
        
        assert "last_updated" in data
        assert "registry_effectiveness" in data
    
    def test_company_transparency_endpoint(self, client):
        """Test company-specific transparency reporting"""
        # First register a company
        company_data = {
            "name": "Transparency Test Company",
            "contact_email": "transparency@company.ie"
        }
        
        company_response = client.post("/v1/company/register", json=company_data)
        assert company_response.status_code == 201
        company_id = company_response.json()["company_id"]
        
        # Check transparency report
        response = client.get(f"/v1/transparency/company/{company_id}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert data["company_id"] == company_id
        assert "total_lookups" in data
        assert "blocked_lookups" in data
        assert "violations_reported" in data
        assert "compliance_score" in data
        assert "registered_since" in data


class TestViolationReporting:
    """Test privacy violation reporting"""
    
    def test_violation_report_submission(self, client):
        """Test users can report privacy violations"""
        # Register user first
        user_data = {
            "email": "victim@example.ie",
            "password": "StrongPass123!",
            "rights": {"anti_doxxing": True}
        }
        
        user_response = client.post("/v1/register", json=user_data)
        assert user_response.status_code == 201
        token = user_response.json()["token"]
        
        # Report violation
        violation_data = {
            "user_token": token,
            "company_name": "BadCompany Ltd",
            "violation_type": "ignored_registry",
            "description": "Company sold my data despite registry indicating anti-doxxing protection",
            "evidence_url": "https://example.com/evidence.pdf"
        }
        
        response = client.post("/v1/violations/report", json=violation_data)
        assert response.status_code == 200
        data = response.json()
        
        assert "report_id" in data
        assert "next_steps" in data
        assert "logged" in data["message"]


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    def test_rate_limiting_on_registration(self, client):
        """Test rate limiting prevents abuse on registration endpoint"""
        # This test would require mocking the rate limiter
        # In a real implementation, you'd make multiple rapid requests
        # and verify that rate limiting kicks in
        pass
    
    def test_rate_limiting_on_lookup(self, client):
        """Test rate limiting on lookup endpoints"""
        # Similar to above, would test company lookup rate limiting
        pass


class TestGDPRCompliance:
    """Test GDPR and Irish Data Protection compliance"""
    
    def test_user_token_expiry(self, client):
        """Test that user tokens have proper expiry"""
        user_data = {
            "email": "expiry@example.ie",
            "password": "StrongPass123!",
            "rights": {"erasure": True}
        }
        
        response = client.post("/v1/register", json=user_data)
        assert response.status_code == 201
        data = response.json()
        
        # Verify token has expiry
        assert "expires_at" in data
        
        # Verify expiry is approximately 1 year from now
        expires_at = datetime.fromisoformat(data["expires_at"].replace('Z', '+00:00'))
        expected_expiry = datetime.now() + timedelta(days=365)
        
        # Allow for some variation in timing
        assert abs((expires_at - expected_expiry).total_seconds()) < 60
    
    def test_audit_logging(self, client):
        """Test that all actions are properly logged for GDPR compliance"""
        # This would test that audit logs are created for all actions
        # In a real implementation, you'd verify database audit entries
        pass


class TestIrishGovernmentIntegration:
    """Test integration with Irish government systems"""
    
    def test_dpc_compliance_reporting(self, client):
        """Test Data Protection Commission compliance reporting"""
        # This would test integration with DPC systems
        # Mock the DPC API endpoints
        pass
    
    def test_oireachtas_integration(self, client):
        """Test integration with Oireachtas systems"""
        # This would test integration with parliamentary systems
        pass


@pytest.mark.asyncio
async def test_async_operations():
    """Test async operations and concurrent access"""
    # Test concurrent user registrations
    # Test concurrent lookups
    # Test system performance under load
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
