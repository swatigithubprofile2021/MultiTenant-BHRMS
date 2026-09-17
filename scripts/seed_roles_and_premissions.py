import asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import AsyncSessionLocal, async_engine as engine_async
from app.db.base import Base
from app.db.models.roles import Role
from app.db.models.permissions import Permission
from app.db.models.association import role_permissions
from sqlalchemy import insert

# Default roles
DEFAULT_ROLES = ["super_admin", "admin", "tenant_admin", "user"]

# Default permissions
DEFAULT_PERMISSIONS = [
    {"code": "U100", "name": "Create Platform Admin"},
    {"code": "U101", "name": "Edit Platform Admin"},
    {"code": "U102", "name": "Delete Platform Admin"},
    {"code": "U103", "name": "Create Tenant Admin"},
    {"code": "U104", "name": "Edit Tenant Admin"},
    {"code": "U105", "name": "Delete Tenant Admin"},
    {"code": "U106", "name": "Create User"},
    {"code": "U107", "name": "Edit User"},
    {"code": "U108", "name": "Delete User"},
    {"code": "T200", "name": "Create Tenant"},
    {"code": "T201", "name": "Edit Tenant"},
    {"code": "T202", "name": "Delete Tenant"},
    {"code": "D300", "name": "Document Upload"},
    {"code": "D301", "name": "Document Edit"},
    {"code": "D302", "name": "Document Delete"},
    {"code": "A400", "name": "Create Agent"},
    {"code": "A401", "name": "Edit Agent"},
    {"code": "A402", "name": "Delete Agent"},
    {"code": "D500", "name": "View Dashboard"},
]

# Role → permission mapping
ROLE_PERMISSIONS = {
    "super_admin": ["U100", "U101", "U102", "D500"],
    "admin": ["U103", "U104", "U105", "T200", "T201", "T202", "D500"],
    "tenant_admin": ["D300", "D301", "D302", "A400", "A401", "A402", "D500"],
    "user": [
        "D500",
    ],
}


async def init_db():
    """
    Ensure all tables exist.
    """
    async with engine_async.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Tables created successfully.")


async def seed_roles_and_permissions():
    """
    Seed roles and permissions and assign them properly.
    """
    async with AsyncSessionLocal() as db:
        # Seed permissions
        permission_objs = {}
        for perm in DEFAULT_PERMISSIONS:
            result = await db.execute(
                select(Permission).where(Permission.code == perm["code"])
            )
            existing_perm = result.scalar_one_or_none()

            if not existing_perm:
                perm_obj = Permission(code=perm["code"], name=perm["name"])
                db.add(perm_obj)
                await db.flush()
                permission_objs[perm["code"]] = perm_obj
            else:
                permission_objs[perm["code"]] = existing_perm

        await db.commit()  # commit to generate IDs for new permissions

        # Seed roles and assign permissions
        for role_name in DEFAULT_ROLES:
            result = await db.execute(
                select(Role)
                .options(selectinload(Role.permissions))
                .where(Role.name == role_name)
            )
            existing_role = result.scalar_one_or_none()
            if not existing_role:
                role_obj = Role(name=role_name)
                db.add(role_obj)
                await db.flush()  # assign ID
            else:
                role_obj = existing_role

            # Assign permissions without triggering lazy-load
            # for code in ROLE_PERMISSIONS.get(role_name, []):
            #     perm_obj = permission_objs.get(code)
            #     if perm_obj and perm_obj not in role_obj.permissions:
            #         role_obj.permissions.append(perm_obj)

            # Clear existing permissions (important when re-running seed)
            for code in ROLE_PERMISSIONS.get(role_name, []):
                perm_obj = permission_objs.get(code)
                if perm_obj:
                    await db.execute(
                        insert(role_permissions).values(
                            role_id=role_obj.id, permission_id=perm_obj.id
                        )
                    )

        await db.commit()

    print("✅ Roles and permissions seeded successfully.")


async def main():
    await init_db()  # ensure tables exist
    await seed_roles_and_permissions()


if __name__ == "__main__":
    asyncio.run(main())
