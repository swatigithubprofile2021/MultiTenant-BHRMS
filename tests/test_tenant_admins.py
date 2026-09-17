import pytest
import tests.config as config


@pytest.mark.order(3)
async def test_create_tenant_admin(async_client, super_admin_token):
    headers = {"Authorization": super_admin_token, "Content-Type": "application/json"}
    resp = await async_client.post(
        "/api/v1/admins/tenant",
        headers=headers,
        json={
            "name": "Tenant Admin Test",
            "email": "tenantadmin@test.com",
            "password": "TenantPass123",
            "tenant_id": config.TENANT_ID,
        },
    )
    print(resp.text)
    assert resp.status_code == 200
    assert (
        f"Tenant admin 'Tenant Admin Test' created successfully" in resp.json()["msg"]
    )
