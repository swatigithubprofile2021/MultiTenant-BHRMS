import pytest
from io import BytesIO
import tests.config as config


@pytest.mark.order(4)
async def test_add_document(async_client, super_admin_token):
    headers = {"Authorization": super_admin_token, "Content-Type": "application/json"}

    file_content = b"dummy file content"

    resp = await async_client.post(
        "/api/v1/documents",
        data={
            "title": "Test Document",
            "category": "finance",
        },
        headers=headers,
        files={"file": ("test.pdf", BytesIO(file_content), "application/pdf")},
    )
    assert resp.status_code == 201

    data = resp.json()
    assert data["filename"] == "test.pdf"
    assert data["tenant_id"] == "test-tenant"
