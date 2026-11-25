"""Telegram help desk: processed updates, customer threads and the message map.

Message text and files are deliberately not stored: the operators' Telegram
group is the record of the conversation, the database only routes it.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TelegramUpdate(Base):
    """An update id Telegram delivered; each one is handled at most once."""

    __tablename__ = "telegram_updates"

    update_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )


class HelpdeskThread(Base):
    """One customer (Telegram user) and their forum topic in the help desk group."""

    __tablename__ = "helpdesk_threads"
    __table_args__ = (
        UniqueConstraint("chat_id", "topic_id", name="uq_helpdesk_threads_chat_topic"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    # As last seen in the customer's messages.
    telegram_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Typed by the customer; never verified and never answered back.
    stated_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    # Order the customer came from through a signed site link.
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    # Help desk chat the topic lives in: a new group invalidates old topics.
    chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    topic_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    last_customer_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_operator_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_ack_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    flood_notice_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Incoming private messages and commands in the current one-minute window,
    # counted before anything else happens (flood limit).
    incoming_window_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    incoming_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class HelpdeskMessage(Base):
    """A relayed message: its id in the customer's chat and in the group topic.

    The row is written before the copy is sent (``sending``) and settled after
    it (``sent``), keyed by the update it came from, so a redelivered update
    is never copied a second time. ``uncertain`` means Telegram may or may not
    have delivered the copy; operators are told instead of copying again.
    """

    __tablename__ = "helpdesk_messages"
    __table_args__ = (
        UniqueConstraint("update_id", "direction", name="uq_helpdesk_messages_update"),
        UniqueConstraint(
            "thread_id", "direction", "customer_message_id",
            name="uq_helpdesk_messages_customer_side",
        ),
        UniqueConstraint(
            "thread_id", "direction", "group_message_id",
            name="uq_helpdesk_messages_group_side",
        ),
        Index("ix_helpdesk_messages_thread_created", "thread_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("helpdesk_threads.id", ondelete="CASCADE"), nullable=False
    )
    # "to_operators" (customer -> topic) or "to_customer" (topic -> customer).
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    update_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # "sending", "sent" or "uncertain".
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="sent")
    customer_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    group_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
