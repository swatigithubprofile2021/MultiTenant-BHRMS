import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models.user import User
from app.db.models.roles import Role
from app.core.security import hash_password
import os



SUPER_ADMIN_EMAIL = os.getenv("SUPER_ADMIN_EMAIL")
SUPER_ADMIN_PASSWORD = os.getenv("SUPER_ADMIN_PASSWORD")




async def create_super_admin():
    async with AsyncSessionLocal() as db:

        # Get super_admin role
        result = await db.execute(select(Role).where(Role.name == "super_admin"))
        role = result.scalar_one_or_none()

        if not role:
            print("❌ super_admin role not found. Run seed_roles first.")
            return

        # Check if already exists
        result = await db.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        existing = result.scalar_one_or_none()

        if existing:
            print("⚠ Super admin already exists.")
            return

        super_admin = User(
            name="Super Admin",
            email=SUPER_ADMIN_EMAIL,
            hashed_password=hash_password(SUPER_ADMIN_PASSWORD),
            role_id=role.id,
            tenant_id=None,
        )

        db.add(super_admin)
        await db.commit()

    print("✅ Super Admin created successfully.")


if __name__ == "__main__":
    asyncio.run(create_super_admin())
