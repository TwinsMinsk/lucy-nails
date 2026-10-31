import time
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.rbac import Permission, Role, UserRoleAssignment
from app.models.user import User
from app.services import ads_service

TOKEN = "a" * 40
SYNC = "/api/internal/ads/campaigns/za-dizain"
HEADERS = {"X-Ads-Token": TOKEN}

CAMPAIGN = {
    "title": "За дизайн доплачивают",
    "summary": "10 роликов",
    "starts_on": "2026-11-09",
    "groups": [{"key": "reach", "title": "Охват", "note": "Вау-визуал"}],
    "about": [{"title": "Идея", "body": "Однотонку умеют все."}],
    "materials": [
        {
            "code": "r01",
            "title": "11 дизайнов",
            "group_key": "reach",
            "hook": "11 дизайнов, за которые доплачивают",
            "voiceover": "Строка 1\nСтрока 2",
            "caption": "Подпись",
            "utm_content": "r01-11-dizainov",
            "duration_seconds": 28,
            "order_index": 1,
        },
        {"code": "r03", "title": "Фольга", "group_key": "reach", "order_index": 3},
    ],
    "tasks": [{"key": "voice", "title": "Записать голос", "order_index": 1}],
    "calendar": [
        {"key": "w1-mon", "day": "2026-11-09", "time": "19:30", "week": 1, "title": "R1", "material_code": "r01"},
        {"key": "w1-fri", "day": "2026-11-13", "week": 1, "title": "Итоги недели"},
    ],
}


@pytest.fixture
def ads_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ADS_STORAGE_DIR", str(tmp_path / "ads"))
    monkeypatch.setattr(settings, "ADS_SYNC_TOKEN", TOKEN)
    return tmp_path / "ads"


async def _permission(db: AsyncSession, name: str) -> Permission:
    return await db.scalar(select(Permission).where(Permission.name == name)) or Permission(name=name, description=name)


async def _staff(db: AsyncSession, email: str, permissions: list[str], name: str | None = None) -> User:
    user = User(email=email, password_hash=get_password_hash("staffpass1"), role="student", full_name=name)
    role = Role(name=f"role-{email}", description="test", is_system=True)
    role.permissions = [await _permission(db, p) for p in permissions]
    db.add_all([user, role])
    await db.flush()
    db.add(UserRoleAssignment(user_id=user.id, role_id=role.id))
    await db.commit()
    await db.refresh(user)
    return user


async def _bearer(client: AsyncClient, user: User) -> dict[str, str]:
    login = await client.post("/api/auth/login", json={"email": user.email, "password": "staffpass1"})
    assert login.status_code == 200, login.text
    client.cookies.clear()
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _lucy(client: AsyncClient, db: AsyncSession) -> dict[str, str]:
    # The marketer role: both ads permissions and nothing else.
    user = await _staff(db, "lucy@example.com", ["ads.read", "ads.manage"], name="Люся")
    return await _bearer(client, user)


async def _upload(client: AsyncClient, code: str, key: str, body: bytes, **params) -> dict:
    response = await client.put(f"{SYNC}/materials/{code}/files/{key}", params=params, content=body, headers=HEADERS)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_sync_requires_configured_token(client, ads_storage, monkeypatch):
    assert (await client.put(SYNC, json=CAMPAIGN)).status_code == 401
    assert (await client.put(SYNC, json=CAMPAIGN, headers={"X-Ads-Token": "b" * 40})).status_code == 401
    monkeypatch.setattr(settings, "ADS_SYNC_TOKEN", "short")
    assert (await client.put(SYNC, json=CAMPAIGN, headers={"X-Ads-Token": "short"})).status_code == 503


@pytest.mark.asyncio
async def test_sync_keeps_team_state_and_replaces_calendar(client, db, ads_storage):
    created = await client.put(SYNC, json=CAMPAIGN, headers=HEADERS)
    assert created.status_code == 200, created.text
    campaign = created.json()
    assert [m["code"] for m in campaign["materials"]] == ["r01", "r03"]
    r01 = campaign["materials"][0]
    assert campaign["calendar"][0]["material_id"] == r01["id"]
    assert campaign["calendar"][1]["material_id"] is None

    headers = await _lucy(client, db)
    published = await client.patch(
        f"/api/admin/ads/materials/{r01['id']}",
        json={"status": "published", "published_url": "https://instagram.com/reel/abc"},
        headers=headers,
    )
    assert published.status_code == 200, published.text
    assert published.json()["published_at"] is not None
    task_id = campaign["tasks"][0]["id"]
    done = await client.patch(f"/api/admin/ads/tasks/{task_id}", json={"done": True}, headers=headers)
    assert done.json()["done_by"]["name"] == "Люся"

    second = dict(CAMPAIGN, calendar=[CAMPAIGN["calendar"][0]])
    second["materials"] = [dict(CAMPAIGN["materials"][0], caption="Новая подпись"), CAMPAIGN["materials"][1]]
    synced = (await client.put(SYNC, json=second, headers=HEADERS)).json()
    r01 = synced["materials"][0]
    assert r01["caption"] == "Новая подпись"
    assert r01["status"] == "published"
    assert r01["published_url"] == "https://instagram.com/reel/abc"
    assert synced["tasks"][0]["done_at"] is not None
    assert [e["title"] for e in synced["calendar"]] == ["R1"]


@pytest.mark.asyncio
async def test_prune_drops_missing_materials_and_their_files(client, db, ads_storage):
    await client.put(SYNC, json=CAMPAIGN, headers=HEADERS)
    await _upload(client, "r03", "video", b"reel", role="video", filename="r03.mp4")
    assert len(list(ads_storage.rglob("*.mp4"))) == 1

    pruned = dict(CAMPAIGN, materials=CAMPAIGN["materials"][:1], prune=True)
    response = await client.put(SYNC, json=pruned, headers=HEADERS)
    assert [m["code"] for m in response.json()["materials"]] == ["r01"]
    assert list(ads_storage.rglob("*.mp4")) == []


@pytest.mark.asyncio
async def test_synced_file_is_replaced_and_served_by_signed_link(client, db, ads_storage):
    await client.put(SYNC, json=CAMPAIGN, headers=HEADERS)
    first = await _upload(client, "r01", "video", b"0123456789", role="video", filename="r01-11-dizainov.mp4")
    second = await _upload(client, "r01", "video", b"abcdefghij-v2", role="video", filename="r01-11-dizainov.mp4")
    assert first["id"] == second["id"]
    assert second["size_bytes"] == 13
    assert second["content_type"] == "video/mp4"
    assert len(list(ads_storage.rglob("*.mp4"))) == 1

    played = await client.get(f"/api{second['url']}", headers={"Range": "bytes=0-4"})
    assert played.status_code == 206
    assert played.content == b"abcde"
    assert played.headers["content-disposition"].startswith("inline")

    downloaded = await client.get(f"/api{second['download_url']}")
    assert downloaded.content == b"abcdefghij-v2"
    assert downloaded.headers["content-disposition"].startswith("attachment")
    assert "r01-11-dizainov.mp4" in downloaded.headers["content-disposition"]


@pytest.mark.asyncio
async def test_signed_link_rejects_forged_and_expired(client, db, ads_storage):
    await client.put(SYNC, json=CAMPAIGN, headers=HEADERS)
    file = await _upload(client, "r01", "cover", b"jpeg", role="cover", filename="r01.jpg")
    query = parse_qs(urlparse(file["url"]).query)
    base = f"/api/ads/files/{file['id']}"

    forged = await client.get(base, params={"exp": query["exp"][0], "sig": "0" * 32})
    assert forged.status_code == 403
    longer = await client.get(base, params={"exp": int(query["exp"][0]) + 3600, "sig": query["sig"][0]})
    assert longer.status_code == 403

    past = int(time.time()) - 60
    expired_sig = ads_service._signature(ads_service.uuid.UUID(file["id"]), past)
    expired = await client.get(base, params={"exp": past, "sig": expired_sig})
    assert expired.status_code == 403


@pytest.mark.asyncio
async def test_sync_rejects_unsafe_file_types(client, db, ads_storage):
    await client.put(SYNC, json=CAMPAIGN, headers=HEADERS)
    response = await client.put(
        f"{SYNC}/materials/r01/files/page",
        params={"role": "other", "filename": "page.html"},
        content=b"<script>alert(1)</script>",
        headers=HEADERS,
    )
    assert response.status_code == 400
    assert list(ads_storage.rglob("*")) == []


@pytest.mark.asyncio
async def test_permissions_split_read_and_manage(client, db, ads_storage):
    campaign = (await client.put(SYNC, json=CAMPAIGN, headers=HEADERS)).json()
    material_id = campaign["materials"][0]["id"]

    outsider = await _staff(db, "analyst@example.com", ["analytics.read"])
    outsider_headers = await _bearer(client, outsider)
    assert (await client.get("/api/admin/ads/campaigns", headers=outsider_headers)).status_code == 403

    viewer = await _staff(db, "viewer@example.com", ["ads.read"])
    viewer_headers = await _bearer(client, viewer)
    listed = await client.get("/api/admin/ads/campaigns", headers=viewer_headers)
    assert listed.status_code == 200
    summary = listed.json()[0]
    assert (summary["materials_total"], summary["tasks_total"], summary["tasks_done"]) == (2, 1, 0)
    detail = await client.get(f"/api/admin/ads/campaigns/{campaign['id']}", headers=viewer_headers)
    assert detail.json()["about"][0]["title"] == "Идея"
    denied = await client.patch(
        f"/api/admin/ads/materials/{material_id}", json={"status": "ready"}, headers=viewer_headers
    )
    assert denied.status_code == 403


@pytest.mark.asyncio
async def test_team_uploads_voice_and_removes_only_own_files(client, db, ads_storage):
    campaign = (await client.put(SYNC, json=CAMPAIGN, headers=HEADERS)).json()
    material_id = campaign["materials"][0]["id"]
    pipeline_file = await _upload(client, "r01", "video", b"reel", role="video", filename="r01.mp4")
    headers = await _lucy(client, db)

    voice = await client.post(
        f"/api/admin/ads/materials/{material_id}/files",
        params={"filename": "Запись R1.m4a"},
        content=b"voice-bytes",
        headers=headers,
    )
    assert voice.status_code == 201, voice.text
    body = voice.json()
    assert (body["role"], body["content_type"], body["filename"]) == ("voice", "audio/mp4", "Запись R1.m4a")
    assert body["uploaded_by"]["name"] == "Люся"

    rejected = await client.post(
        f"/api/admin/ads/materials/{material_id}/files",
        params={"filename": "image.svg"},
        content=b"<svg/>",
        headers=headers,
    )
    assert rejected.status_code == 400

    locked = await client.delete(f"/api/admin/ads/files/{pipeline_file['id']}", headers=headers)
    assert locked.status_code == 409
    removed = await client.delete(f"/api/admin/ads/files/{body['id']}", headers=headers)
    assert removed.status_code == 204
    assert list(ads_storage.rglob("*.m4a")) == []


@pytest.mark.asyncio
async def test_comments_belong_to_their_author(client, db, ads_storage):
    campaign = (await client.put(SYNC, json=CAMPAIGN, headers=HEADERS)).json()
    material_id = campaign["materials"][1]["id"]
    headers = await _lucy(client, db)

    created = await client.post(
        f"/api/admin/ads/campaigns/{campaign['id']}/comments",
        json={"body": "  В R3 поменять слово  ", "material_id": material_id},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["body"] == "В R3 поменять слово"
    assert created.json()["is_mine"] is True

    synced = (await client.get(SYNC, headers=HEADERS)).json()
    assert synced["comments"][0]["material_id"] == material_id

    other = await _staff(db, "oleg@example.com", ["ads.read", "ads.manage"])
    other_headers = await _bearer(client, other)
    foreign = await client.delete(f"/api/admin/ads/comments/{created.json()['id']}", headers=other_headers)
    assert foreign.status_code == 403
    own = await client.delete(f"/api/admin/ads/comments/{created.json()['id']}", headers=headers)
    assert own.status_code == 204


@pytest.mark.asyncio
async def test_published_url_must_be_https(client, db, ads_storage):
    campaign = (await client.put(SYNC, json=CAMPAIGN, headers=HEADERS)).json()
    headers = await _lucy(client, db)
    response = await client.patch(
        f"/api/admin/ads/materials/{campaign['materials'][0]['id']}",
        json={"published_url": "javascript:alert(1)"},
        headers=headers,
    )
    assert response.status_code == 422
