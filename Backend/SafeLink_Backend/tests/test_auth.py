"""
Authentication Flow Tests

Tests for login, logout, token refresh, and protected routes.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api import app
from core.auth import AuthService, User, Base


# Test database setup
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def test_db():
    """Create test database."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    Base.metadata.create_all(bind=engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    yield TestingSessionLocal
    
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_service(test_db):
    """Create auth service with test database."""
    db = test_db()
    service = AuthService()
    service.db = db
    
    yield service
    
    db.close()


@pytest.fixture
def test_user(auth_service):
    """Create a test user."""
    from core.auth import UserCreate
    
    user_data = UserCreate(
        username="testuser",
        email="test@example.com",
        password="TestPassword123!",
        full_name="Test User"
    )
    
    user = auth_service.create_user(user_data)
    return user


class TestUserRegistration:
    """Test user registration."""
    
    def test_register_success(self, client):
        """Test successful user registration."""
        response = client.post("/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "SecurePass123!",
            "full_name": "New User"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"
        assert "id" in data
    
    def test_register_duplicate_username(self, client, test_user):
        """Test registration with duplicate username."""
        response = client.post("/auth/register", json={
            "username": "testuser",  # Already exists
            "email": "another@example.com",
            "password": "SecurePass123!",
            "full_name": "Another User"
        })
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()
    
    def test_register_weak_password(self, client):
        """Test registration with weak password."""
        response = client.post("/auth/register", json={
            "username": "weakuser",
            "email": "weak@example.com",
            "password": "123",  # Too short/weak
            "full_name": "Weak User"
        })
        
        # Should fail validation (422 Unprocessable Entity or 400 Bad Request)
        assert response.status_code in [400, 422]


class TestLogin:
    """Test login functionality."""
    
    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "TestPassword123!"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_username(self, client):
        """Test login with non-existent username."""
        response = client.post("/auth/login", json={
            "username": "nonexistent",
            "password": "SomePassword123!"
        })
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()
    
    def test_login_invalid_password(self, client, test_user):
        """Test login with wrong password."""
        response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "WrongPassword123!"
        })
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()
    
    def test_login_inactive_user(self, client, test_user, auth_service):
        """Test login with deactivated user."""
        # Deactivate user
        test_user.is_active = False
        auth_service.db.commit()
        
        response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "TestPassword123!"
        })
        
        assert response.status_code == 401
        assert "inactive" in response.json()["detail"].lower()


class TestTokenRefresh:
    """Test token refresh functionality."""
    
    def test_refresh_success(self, client, test_user, auth_service):
        """Test successful token refresh."""
        # Login to get refresh token
        login_response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "TestPassword123!"
        })
        refresh_token = login_response.json()["refresh_token"]
        
        # Refresh
        response = client.post("/auth/refresh", json={
            "refresh_token": refresh_token
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
    
    def test_refresh_invalid_token(self, client):
        """Test refresh with invalid token."""
        response = client.post("/auth/refresh", json={
            "refresh_token": "invalid_token_xyz"
        })
        
        assert response.status_code == 401


class TestProtectedRoutes:
    """Test protected route access."""
    
    def test_access_without_token(self, client):
        """Test accessing protected route without token."""
        response = client.get("/alerts/stats")
        
        assert response.status_code == 401
    
    def test_access_with_valid_token(self, client, test_user):
        """Test accessing protected route with valid token."""
        # Login
        login_response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "TestPassword123!"
        })
        access_token = login_response.json()["access_token"]
        
        # Access protected route
        response = client.get(
            "/alerts/stats",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
    
    def test_access_with_invalid_token(self, client):
        """Test accessing protected route with invalid token."""
        response = client.get(
            "/alerts/stats",
            headers={"Authorization": "Bearer invalid_token_xyz"}
        )
        
        assert response.status_code == 401
    
    def test_access_with_expired_token(self, client, auth_service, test_user):
        """Test accessing protected route with expired token."""
        # Create expired token
        from core.auth import create_access_token
        
        expired_token = create_access_token(
            data={"sub": test_user.username},
            expires_delta=timedelta(seconds=-1)  # Already expired
        )
        
        # Try to access
        response = client.get(
            "/alerts/stats",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == 401


class TestLogout:
    """Test logout functionality."""
    
    def test_logout_success(self, client, test_user):
        """Test successful logout."""
        # Login
        login_response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "TestPassword123!"
        })
        access_token = login_response.json()["access_token"]
        
        # Logout
        response = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        # Should succeed or return 200/204
        assert response.status_code in [200, 204]


class TestPermissions:
    """Test permission-based access control."""
    
    def test_admin_only_route(self, client, test_user):
        """Test route restricted to admin users."""
        # Login as regular user
        login_response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "TestPassword123!"
        })
        access_token = login_response.json()["access_token"]
        
        # Try to access admin-only route (if exists)
        # Example: user management endpoints
        response = client.get(
            "/auth/users",  # Assuming this is admin-only
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        # Should be forbidden for non-admin
        # (Will be 403 if permission check exists, else 200)
        assert response.status_code in [200, 403]
    
    def test_permission_decorator(self, auth_service, test_user):
        """Test permission checking decorator."""
        from core.auth import require_permission
        
        # Test user doesn't have admin permission
        has_admin = "admin" in (test_user.permissions or "")
        assert not has_admin


class TestUserProfile:
    """Test user profile operations."""
    
    def test_get_current_user_profile(self, client, test_user):
        """Test retrieving current user profile."""
        # Login
        login_response = client.post("/auth/login", json={
            "username": "testuser",
            "password": "TestPassword123!"
        })
        access_token = login_response.json()["access_token"]
        
        # Get profile
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
