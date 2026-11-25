"""Course, module, lesson, landing and gallery changes are written to the audit log."""

import json

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.audit_log import AuditLog
from app.models.rbac import Permission, Role, UserRoleAssignment
from app.models.user import User
from conftest import mfa_headers

LESSON_HTML = "<p>Секретный конспект урока</p>"
COURSE_HTML = "<p>Длинное описание курса</p>"


async def _editor(client: AsyncClient, db: AsyncSession) -> tuple[User, dict[str, str]]:
    user = User(email="editor@example.com", password_hash=get_password_hash("x" * 12), role="student")
    role = Role(name="owner", description="owner", is_system=True)
    role.permissions = [
        Permission(name="content.manage", description="content"),
        Permission(name="commerce.manage_pricing", description="pricing"),
    ]
    db.add_all([user, role])
    await db.flush()
    db.add(UserRoleAssignment(user_id=user.id, role_id=role.id))
    await db.commit()
    return user, await mfa_headers(client, db, user)


async def _entries(db: AsyncSession, action: str) -> list[AuditLog]:
    db.expunge_all()
    result = await db.execute(
        select(AuditLog).where(AuditLog.action == action).order_by(AuditLog.created_at)
    )
    return list(result.scalars().all())


def _no_bodies(entries: list[AuditLog]) -> None:
    dumped = json.dumps([[entry.old_value, entry.new_value] for entry in entries], ensure_ascii=False)
    assert "конспект" not in dumped
    assert "Длинное описание" not in dumped


@pytest.mark.asyncio
async def test_course_module_and_lesson_crud_is_audited(client: AsyncClient, db: AsyncSession):
    editor, headers = await _editor(client, db)

    course = await client.post("/api/admin/courses", json={"title": "Course A"}, headers=headers)
    assert course.status_code == 200, course.text
    course_id = course.json()["id"]
    db.expunge_all()
    updated = await client.put(
        f"/api/admin/courses/{course_id}",
        json={"description": COURSE_HTML, "is_published": True, "price_self": 6900},
        headers=headers,
    )
    assert updated.status_code == 200, updated.text

    module = await client.post(
        "/api/admin/modules", json={"course_id": course_id, "title": "Module 1"}, headers=headers
    )
    module_id = module.json()["id"]
    db.expunge_all()
    await client.put(f"/api/admin/modules/{module_id}", json={"is_published": True}, headers=headers)
    lesson = await client.post(
        "/api/admin/lessons",
        json={"module_id": module_id, "title": "Lesson 1", "content": LESSON_HTML},
        headers=headers,
    )
    lesson_id = lesson.json()["id"]
    db.expunge_all()
    lesson_update = await client.put(
        f"/api/admin/lessons/{lesson_id}",
        json={"content": LESSON_HTML + "<p>ещё</p>", "is_preview": True},
        headers=headers,
    )
    assert lesson_update.status_code == 200, lesson_update.text
    db.expunge_all()
    assert (await client.delete(f"/api/admin/lessons/{lesson_id}", headers=headers)).status_code == 200
    db.expunge_all()
    assert (await client.delete(f"/api/admin/modules/{module_id}", headers=headers)).status_code == 200
    db.expunge_all()
    assert (await client.delete(f"/api/admin/courses/{course_id}", headers=headers)).status_code == 200

    course_update = (await _entries(db, "course.update"))[0]
    assert course_update.actor_user_id == editor.id
    assert course_update.object_id == course_id
    assert course_update.old_value == {"is_published": False, "price_self": 5900}
    assert course_update.new_value == {
        "changed_fields": ["description", "is_published", "price_self"],
        "is_published": True,
        "price_self": 6900,
    }
    lesson_entry = (await _entries(db, "lesson.update"))[0]
    assert lesson_entry.old_value == {"is_preview": False}
    assert lesson_entry.new_value == {"changed_fields": ["content", "is_preview"], "is_preview": True}

    created = await _entries(db, "course.create")
    assert created[0].new_value["title"] == "Course A"
    for action in ("module.create", "module.update", "lesson.create", "lesson.delete", "module.delete", "course.delete"):
        entries = await _entries(db, action)
        assert len(entries) == 1, action
        assert entries[0].actor_user_id == editor.id
    every_entry = list((await db.execute(select(AuditLog))).scalars().all())
    _no_bodies(every_entry)


@pytest.mark.asyncio
async def test_landing_and_gallery_changes_are_audited(client: AsyncClient, db: AsyncSession):
    editor, headers = await _editor(client, db)
    course = await client.post("/api/admin/courses", json={"title": "Landing course"}, headers=headers)
    course_id = course.json()["id"]
    db.expunge_all()

    hero = await client.put(
        f"/api/admin/courses/{course_id}/landing-hero",
        json={"landing_title": "Новый заголовок", "landing_description": COURSE_HTML},
        headers=headers,
    )
    assert hero.status_code == 200, hero.text
    first = await client.post(
        "/api/admin/gallery",
        json={"image_url": "/uploads/a.jpg", "title": "Работа 1", "order_index": 0},
        headers=headers,
    )
    second = await client.post(
        "/api/admin/gallery",
        json={"image_url": "/uploads/b.jpg", "title": "Работа 2", "order_index": 1},
        headers=headers,
    )
    first_id, second_id = first.json()["id"], second.json()["id"]
    db.expunge_all()
    await client.put(f"/api/admin/gallery/{first_id}", json={"is_published": False}, headers=headers)
    db.expunge_all()
    await client.put(
        "/api/admin/gallery/reorder",
        json=[{"id": first_id, "order_index": 1}, {"id": second_id, "order_index": 1}],
        headers=headers,
    )
    db.expunge_all()
    deleted = await client.delete(f"/api/admin/gallery/{second_id}", headers=headers)
    assert deleted.status_code == 204

    hero_entry = (await _entries(db, "course_landing.update"))[0]
    assert hero_entry.actor_user_id == editor.id
    assert hero_entry.new_value == {
        "changed_fields": ["landing_description", "landing_title"],
        "landing_title": "Новый заголовок",
    }
    assert len(await _entries(db, "gallery_item.create")) == 2
    update = (await _entries(db, "gallery_item.update"))[0]
    assert update.old_value == {"is_published": True}
    reorder = (await _entries(db, "gallery.reorder"))[0]
    assert reorder.old_value == {"order_index": {first_id: 0}}
    assert reorder.new_value == {"order_index": {first_id: 1}}
    removed = (await _entries(db, "gallery_item.delete"))[0]
    assert removed.object_id == second_id
    _no_bodies(list((await db.execute(select(AuditLog))).scalars().all()))
