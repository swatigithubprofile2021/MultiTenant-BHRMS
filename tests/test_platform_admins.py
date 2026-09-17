import pytest


@pytest.mark.order(1)
async def test_create_platform_admin(async_client, super_admin_token):
    # Create Platform Admin
    headers = {"Authorization": super_admin_token, "Content-Type": "application/json"}
    resp = await async_client.post(
        "/api/v1/admins/platform",
        json={
            "name": "Test Admin",
            "email": "admin@test.com",
            "password": "AdminPass123",
        },
        headers=headers,
    )
    print(resp.text)
    assert resp.status_code == 200
    assert "Platform admin 'Test Admin' created successfully" in resp.json()["msg"]
