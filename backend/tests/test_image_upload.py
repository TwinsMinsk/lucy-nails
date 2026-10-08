import io

import pytest
from PIL import Image

from app.api import upload
from app.models.user import User
from app.main import app
from app.core.dependencies import get_current_user
from app.core import upload_limits


@pytest.fixture
def image_storage(monkeypatch, tmp_path):
    monkeypatch.setattr(upload, "_upload_dir", lambda: tmp_path)
    app.dependency_overrides[get_current_user] = lambda: User(role="admin")
    yield tmp_path
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_fake_image_is_rejected_without_saved_file(client, image_storage):
    response = await client.post(
        "/api/admin/upload", files={"file": ("fake.png", b"not an image", "image/png")}
    )
    assert response.status_code == 400
    assert not list(image_storage.iterdir())


@pytest.mark.asyncio
async def test_oversized_image_is_rejected_without_saved_file(
    client, image_storage, monkeypatch
):
    monkeypatch.setattr(upload, "MAX_UPLOAD_BYTES", 100, raising=False)
    response = await client.post(
        "/api/admin/upload", files={"file": ("large.png", b"x" * 101, "image/png")}
    )
    assert response.status_code == 413
    assert not list(image_storage.iterdir())


@pytest.mark.asyncio
async def test_valid_image_is_reencoded_and_mismatched_extension_denied(
    client, image_storage
):
    source = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(source, format="PNG")
    data = source.getvalue()
    mismatch = await client.post(
        "/api/admin/upload", files={"file": ("wrong.jpg", data, "image/jpeg")}
    )
    assert mismatch.status_code == 400
    response = await client.post(
        "/api/admin/upload",
        files={"file": ("real.png", data + b"hidden trailing bytes", "image/png")},
    )
    assert response.status_code == 200, response.text
    saved = image_storage / response.json()["filename"]
    assert b"hidden trailing bytes" not in saved.read_bytes()
    with Image.open(saved) as image:
        assert image.size == (4, 4)


@pytest.mark.asyncio
async def test_pixel_limit_is_enforced(client, image_storage, monkeypatch):
    monkeypatch.setattr(upload, "MAX_IMAGE_PIXELS", 10, raising=False)
    source = io.BytesIO()
    Image.new("RGB", (4, 4)).save(source, format="PNG")
    response = await client.post(
        "/api/admin/upload",
        files={"file": ("pixels.png", source.getvalue(), "image/png")},
    )
    assert response.status_code == 400
    assert not list(image_storage.iterdir())


@pytest.mark.asyncio
async def test_chunked_body_limit_runs_before_multipart_parsing(
    client, image_storage, monkeypatch
):
    monkeypatch.setattr(upload_limits, "MAX_MULTIPART_BYTES", 100)

    async def chunks():
        yield b"x" * 60
        yield b"x" * 60

    response = await client.post(
        "/api/admin/upload",
        content=chunks(),
        headers={"Content-Type": "multipart/form-data; boundary=x"},
    )
    assert response.status_code == 413
    assert not list(image_storage.iterdir())


@pytest.mark.asyncio
async def test_truncated_image_is_bad_request_not_server_error(client, image_storage):
    source = io.BytesIO()
    Image.new("RGB", (8, 8)).save(source, format="PNG")
    response = await client.post(
        "/api/admin/upload",
        files={"file": ("broken.png", source.getvalue()[:40], "image/png")},
    )
    assert response.status_code == 400
    assert not list(image_storage.iterdir())
