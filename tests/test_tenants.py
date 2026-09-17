import pytest
import tests.config as config


@pytest.mark.order(2)
async def test_create_tenant(async_client, super_admin_token):
    headers = {"Authorization": super_admin_token, "Content-Type": "application/json"}
    resp = await async_client.post(
        "/api/v1/tenants",
        headers=headers,
        json={"name": "Acme Corp"},
    )
    assert resp.status_code == 200
    assert resp.json()["tenant_id"] is not None
    # store tenant id for later tests
    config.TENANT_ID = resp.json()["tenant_id"]
