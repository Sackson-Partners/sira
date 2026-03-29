"""
Seed data for development/staging environments.
Never runs in production.
"""

import os
import logging

logger = logging.getLogger(__name__)


def seed_test_users():
    """Create test users for all roles. Only runs in non-production environments."""
    from app.core.config import settings
    env = getattr(settings, 'ENVIRONMENT', None)
    if env == "production":
        logger.warning("Skipping seed in production")
        return

    from app.core.database import SessionLocal
    from app.core.security import hash_password
    from app.models.user import User
    from app.models.organization import Organization

    db = SessionLocal()
    try:
        # Create demo organization if not exists
        org = db.query(Organization).filter(Organization.slug == "sira-demo").first()
        if not org:
            org = Organization(
                name="SIRA Demo Organization",
                slug="sira-demo",
                type="logistics",
                country_code="ZA",
                timezone="Africa/Johannesburg",
                plan="professional",
                is_active=True,
            )
            db.add(org)
            db.flush()
            logger.info("Created demo organization")

        test_password = os.getenv("TEST_USER_PASSWORD", "TestPass@Sira2024!")

        test_users = [
            {
                "email": "superadmin@sira.system",
                "username": "superadmin",
                "full_name": "Super Administrator",
                "role": "super_admin",
                "password": os.getenv("SUPER_ADMIN_PASSWORD", test_password),
                "organization_id": None,
            },
            {
                "email": "orgadmin@demo.sira",
                "username": "orgadmin",
                "full_name": "Org Administrator",
                "role": "org_admin",
                "password": test_password,
                "organization_id": org.id,
            },
            {
                "email": "manager@demo.sira",
                "username": "demoManager",
                "full_name": "Operations Manager",
                "role": "manager",
                "password": test_password,
                "organization_id": org.id,
            },
            {
                "email": "operator@demo.sira",
                "username": "demoOperator",
                "full_name": "Field Operator",
                "role": "operator",
                "password": test_password,
                "organization_id": org.id,
            },
            {
                "email": "analyst@demo.sira",
                "username": "demoAnalyst",
                "full_name": "Data Analyst",
                "role": "analyst",
                "password": test_password,
                "organization_id": org.id,
            },
            {
                "email": "viewer@demo.sira",
                "username": "demoViewer",
                "full_name": "Report Viewer",
                "role": "viewer",
                "password": test_password,
                "organization_id": org.id,
            },
        ]

        for user_data in test_users:
            existing = db.query(User).filter(User.email == user_data["email"]).first()
            if not existing:
                user = User(
                    email=user_data["email"],
                    username=user_data["username"],
                    full_name=user_data["full_name"],
                    role=user_data["role"],
                    hashed_password=hash_password(user_data["password"]),
                    is_active=True,
                    is_verified=True,
                    organization_id=user_data.get("organization_id"),
                )
                db.add(user)
                logger.info(f"Created seed user: {user_data['email']} ({user_data['role']})")

        db.commit()
        logger.info("Seed data created successfully")
    except Exception as e:
        logger.error(f"Seed failed: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_test_users()
