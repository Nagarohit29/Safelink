"""
Authentication and authorization module for SafeLink.
Implements JWT-based authentication with role-based access control (RBAC).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, List
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, func, Table, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from config.settings import DATABASE_URL
from sqlalchemy import create_engine

# JWT Configuration
SECRET_KEY = "your-secret-key-change-this-in-production"  # TODO: Move to environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

Base = declarative_base()

# Association table for many-to-many relationship
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True)
)


class Role(Base):
    """User role model for RBAC."""
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255))
    permissions = Column(String(500))  # JSON string of permissions
    created_at = Column(TIMESTAMP, default=func.now())
    
    users = relationship("User", secondary=user_roles, back_populates="roles")


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=func.now())
    last_login = Column(TIMESTAMP)
    
    roles = relationship("Role", secondary=user_roles, back_populates="users")


# Pydantic models
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    roles: List[str] = []


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    roles: List[str]
    
    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthService:
    """Service for handling authentication operations."""
    
    def __init__(self, database_url: str = DATABASE_URL):
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self._initialize_default_roles()
    
    def _initialize_default_roles(self):
        """Create default roles if they don't exist."""
        session = self.SessionLocal()
        try:
            roles_to_create = [
                {"name": "admin", "description": "Full system access", 
                 "permissions": '["read", "write", "delete", "configure", "mitigate"]'},
                {"name": "operator", "description": "Can view and mitigate threats", 
                 "permissions": '["read", "mitigate"]'},
                {"name": "viewer", "description": "Read-only access", 
                 "permissions": '["read"]'},
            ]
            
            for role_data in roles_to_create:
                existing = session.query(Role).filter_by(name=role_data["name"]).first()
                if not existing:
                    role = Role(**role_data)
                    session.add(role)
            
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error initializing roles: {e}")
        finally:
            session.close()
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        # Truncate to 72 bytes for bcrypt compatibility
        plain_password = plain_password[:72]
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password for storage."""
        # Truncate to 72 bytes for bcrypt compatibility
        password = password[:72]
        return pwd_context.hash(password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    def create_refresh_token(self, data: dict) -> str:
        """Create a JWT refresh token."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user by username and password."""
        session = self.SessionLocal()
        try:
            user = session.query(User).filter(User.username == username).first()
            if not user:
                return None
            if not self.verify_password(password, user.hashed_password):
                return None
            
            # Update last login
            user.last_login = datetime.now(timezone.utc)
            session.commit()
            session.refresh(user)
            
            # Load all attributes before closing session to avoid DetachedInstanceError
            _ = user.is_active
            _ = user.roles
            
            return user
        finally:
            session.close()
    
    def create_user(self, user_data: UserCreate, role_names: List[str] = None) -> User:
        """Create a new user."""
        session = self.SessionLocal()
        try:
            # Check if user already exists
            existing = session.query(User).filter(
                (User.username == user_data.username) | (User.email == user_data.email)
            ).first()
            if existing:
                raise ValueError("User with this username or email already exists")
            
            hashed_password = self.get_password_hash(user_data.password)
            user = User(
                username=user_data.username,
                email=user_data.email,
                hashed_password=hashed_password,
                full_name=user_data.full_name
            )
            
            # Assign roles
            if role_names:
                roles = session.query(Role).filter(Role.name.in_(role_names)).all()
                user.roles = roles
            else:
                # Default to viewer role
                viewer_role = session.query(Role).filter_by(name="viewer").first()
                if viewer_role:
                    user.roles = [viewer_role]
            
            session.add(user)
            session.commit()
            session.refresh(user)
            
            # Load roles before closing session to avoid DetachedInstanceError
            _ = user.roles  # Trigger lazy load
            
            return user
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get a user by username."""
        session = self.SessionLocal()
        try:
            user = session.query(User).filter(User.username == username).first()
            if user:
                # Load all attributes before closing session to avoid DetachedInstanceError
                _ = user.is_active
                _ = user.roles
            return user
        finally:
            session.close()
    
    def has_permission(self, user: User, permission: str) -> bool:
        """Check if a user has a specific permission."""
        if user.is_superuser:
            return True
        
        import json
        for role in user.roles:
            try:
                perms = json.loads(role.permissions)
                if permission in perms:
                    return True
            except:
                continue
        return False


# Dependency for getting current user
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(lambda: AuthService())
) -> User:
    """Dependency to get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = auth_service.get_user_by_username(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure the user is active."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def require_permission(permission: str):
    """Dependency factory to check if user has a specific permission."""
    async def permission_checker(
        current_user: User = Depends(get_current_active_user),
        auth_service: AuthService = Depends(lambda: AuthService())
    ):
        if not auth_service.has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires '{permission}'"
            )
        return current_user
    return permission_checker
