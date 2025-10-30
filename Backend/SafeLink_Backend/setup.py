"""
Initial setup script for SafeLink.
Creates default admin user and configures the system.
"""
from core.auth import AuthService, UserCreate
from core.mitigation import MitigationService
from config.logger_config import setup_logger
import sys

logger = setup_logger("Setup")


def create_admin_user():
    """Create the default admin user."""
    auth_service = AuthService()
    
    print("\n=== SafeLink Admin User Setup ===\n")
    
    username = input("Admin username (default: admin): ").strip() or "admin"
    email = input("Admin email: ").strip()
    
    if not email:
        email = f"{username}@safelink.local"
    
    password = input("Admin password: ").strip()
    
    if not password:
        print("Error: Password cannot be empty")
        sys.exit(1)
    
    confirm_password = input("Confirm password: ").strip()
    
    if password != confirm_password:
        print("Error: Passwords do not match")
        sys.exit(1)
    
    try:
        user = auth_service.create_user(
            UserCreate(
                username=username,
                email=email,
                password=password,
                full_name="System Administrator"
            ),
            role_names=["admin"]
        )
        
        print(f"\n✓ Admin user created successfully!")
        print(f"  Username: {user.username}")
        print(f"  Email: {user.email}")
        print(f"  Roles: {[role.name for role in user.roles]}")
        
    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)


def create_default_users():
    """Create example users for different roles."""
    auth_service = AuthService()
    
    print("\n=== Creating Default Users ===\n")
    
    create_defaults = input("Create default operator and viewer users? (y/N): ").strip().lower()
    
    if create_defaults != 'y':
        return
    
    users_to_create = [
        {
            "data": UserCreate(
                username="operator",
                email="operator@safelink.local",
                password="operator123",
                full_name="Operator User"
            ),
            "roles": ["operator"]
        },
        {
            "data": UserCreate(
                username="viewer",
                email="viewer@safelink.local",
                password="viewer123",
                full_name="Viewer User"
            ),
            "roles": ["viewer"]
        }
    ]
    
    for user_config in users_to_create:
        try:
            user = auth_service.create_user(user_config["data"], role_names=user_config["roles"])
            print(f"✓ Created {user.username} ({', '.join(user_config['roles'])})")
        except ValueError as e:
            print(f"⚠ Skipped {user_config['data'].username}: {e}")


def setup_whitelist():
    """Setup default whitelist entries."""
    print("\n=== Mitigation Whitelist Setup ===\n")
    
    mitigation_service = MitigationService()
    
    setup_whitelist_option = input("Add entries to mitigation whitelist? (y/N): ").strip().lower()
    
    if setup_whitelist_option != 'y':
        return
    
    print("\nAdd IPs/MACs that should NEVER be mitigated (e.g., gateway, DNS servers)")
    print("Enter blank IP to finish\n")
    
    while True:
        ip = input("IP address: ").strip()
        if not ip:
            break
        
        mac = input("MAC address (optional): ").strip() or None
        description = input("Description: ").strip() or "Whitelisted during setup"
        
        try:
            mitigation_service.add_to_whitelist(
                ip=ip,
                mac=mac,
                description=description,
                created_by="setup_script"
            )
            print(f"✓ Added {ip} to whitelist\n")
        except Exception as e:
            print(f"⚠ Error: {e}\n")


def display_summary():
    """Display setup summary and next steps."""
    print("\n" + "="*60)
    print("SafeLink Setup Complete!")
    print("="*60)
    print("\nNext Steps:")
    print("1. Start the backend server:")
    print("   uvicorn api:app --host 0.0.0.0 --port 8000")
    print("\n2. Start Celery worker (in another terminal):")
    print("   celery -A core.tasks worker --loglevel=info")
    print("\n3. Start Celery beat for scheduled tasks:")
    print("   celery -A core.tasks beat --loglevel=info")
    print("\n4. Access the API documentation:")
    print("   http://localhost:8000/docs")
    print("\n5. Configure threat intelligence (optional):")
    print("   - Get AbuseIPDB API key from https://www.abuseipdb.com/")
    print("   - Set ABUSEIPDB_API_KEY in .env file")
    print("\n6. Configure SIEM export (optional):")
    print("   - Set SIEM_* variables in .env file")
    print("   - Or use API: POST /siem/configure")
    print("\n7. Login to the frontend:")
    print("   - Use the admin credentials you just created")
    print("   - Default operator/viewer passwords (if created): operator123/viewer123")
    print("\n" + "="*60)


def main():
    """Main setup function."""
    print("\n" + "="*60)
    print("SafeLink Network Defense System - Initial Setup")
    print("="*60)
    
    try:
        # Create admin user
        create_admin_user()
        
        # Create default users
        create_default_users()
        
        # Setup whitelist
        setup_whitelist()
        
        # Display summary
        display_summary()
        
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Setup error: {e}")
        print(f"\nSetup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
