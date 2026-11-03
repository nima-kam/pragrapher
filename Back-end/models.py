"""Database models for the Paragrapher v1 API."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship

from extensions import db


def new_id() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False, index=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.String(500), nullable=False, default="")
    date_of_birth = db.Column(db.Date, nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    credit_balance = db.Column(db.Integer, nullable=False, default=100)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    memberships = relationship("CommunityMember", back_populates="user", cascade="all, delete-orphan")

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "bio": self.bio,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "avatar_url": self.avatar_url,
            "credit_balance": self.credit_balance,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat(),
        }


class Community(db.Model):
    __tablename__ = "communities"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.String(600), nullable=False, default="")
    is_private = db.Column(db.Boolean, nullable=False, default=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    avatar_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    owner = relationship("User", foreign_keys=[owner_id])
    members = relationship("CommunityMember", back_populates="community", cascade="all, delete-orphan")
    quotes = relationship("Quote", back_populates="community", cascade="all, delete-orphan")

    def to_dict(self, viewer: User | None = None) -> dict:
        return {
            "id": self.id,
            "slug": self.slug,
            "name": self.name,
            "description": self.description,
            "is_private": self.is_private,
            "avatar_url": self.avatar_url,
            "owner": {"id": self.owner.id, "username": self.owner.username, "display_name": self.owner.display_name},
            "member_count": len(self.members),
            "like_count": db.session.query(CommunityLike).filter_by(community_id=self.id).count(),
            "is_member": bool(viewer and any(item.user_id == viewer.id for item in self.members)),
            "is_liked": bool(viewer and db.session.get(CommunityLike, (viewer.id, self.id))),
            "created_at": self.created_at.isoformat(),
        }


class CommunityMember(db.Model):
    __tablename__ = "community_members"
    __table_args__ = (UniqueConstraint("community_id", "user_id", name="uq_community_member"),)

    id = db.Column(db.Integer, primary_key=True)
    community_id = db.Column(db.String(36), db.ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False, default="member")
    subscribed = db.Column(db.Boolean, nullable=False, default=True)
    joined_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    community = relationship("Community", back_populates="members")
    user = relationship("User", back_populates="memberships")


class CommunityLike(db.Model):
    __tablename__ = "community_likes"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    community_id = db.Column(db.String(36), db.ForeignKey("communities.id", ondelete="CASCADE"), primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class Category(db.Model):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("community_id", "name", name="uq_category_community_name"),)

    id = db.Column(db.Integer, primary_key=True)
    community_id = db.Column(db.String(36), db.ForeignKey("communities.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(300), nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "description": self.description, "created_at": self.created_at.isoformat()}


class Quote(db.Model):
    __tablename__ = "quotes"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    community_id = db.Column(db.String(36), db.ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    text = db.Column(db.String(2000), nullable=False)
    reference = db.Column(db.String(250), nullable=False, default="")
    character = db.Column(db.String(150), nullable=False, default="")
    tags = db.Column(db.JSON, nullable=False, default=list)
    parent_id = db.Column(db.String(36), db.ForeignKey("quotes.id", ondelete="CASCADE"), nullable=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    community = relationship("Community", back_populates="quotes")
    user = relationship("User", foreign_keys=[user_id])
    parent = relationship("Quote", remote_side=[id], back_populates="replies")
    replies = relationship("Quote", back_populates="parent", cascade="all, delete-orphan")
    likes = relationship("QuoteLike", back_populates="quote", cascade="all, delete-orphan")

    @property
    def like_count(self) -> int:
        return len(self.likes)

    def to_dict(self, viewer: User | None = None, include_replies: bool = False) -> dict:
        result = {
            "id": self.id,
            "community": {"slug": self.community.slug, "name": self.community.name},
            "user": {"id": self.user.id, "username": self.user.username, "display_name": self.user.display_name, "avatar_url": self.user.avatar_url},
            "text": self.text,
            "reference": self.reference,
            "character": self.character,
            "tags": self.tags or [],
            "parent_id": self.parent_id,
            "like_count": self.like_count,
            "reply_count": len(self.replies),
            "is_liked": bool(viewer and db.session.get(QuoteLike, (viewer.id, self.id))),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if include_replies:
            result["replies"] = [reply.to_dict(viewer) for reply in sorted(self.replies, key=lambda item: item.created_at)]
        return result


class QuoteLike(db.Model):
    __tablename__ = "quote_likes"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    quote_id = db.Column(db.String(36), db.ForeignKey("quotes.id", ondelete="CASCADE"), primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    quote = relationship("Quote", back_populates="likes")


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    body = db.Column(db.String(500), nullable=False)
    read_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    def to_dict(self) -> dict:
        return {"id": self.id, "title": self.title, "body": self.body, "read": self.read_at is not None, "created_at": self.created_at.isoformat()}


class Book(db.Model):
    __tablename__ = "books"
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_book_price_nonnegative"),
        CheckConstraint("status in ('available', 'reserved', 'sold')", name="ck_book_status"),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    community_id = db.Column(db.String(36), db.ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reserved_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title = db.Column(db.String(180), nullable=False)
    author = db.Column(db.String(160), nullable=False)
    genre = db.Column(db.String(80), nullable=False, default="")
    description = db.Column(db.String(1200), nullable=False, default="")
    price = db.Column(db.Integer, nullable=False, default=0)
    image_url = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="available")
    reservation_expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    community = relationship("Community")
    seller = relationship("User", foreign_keys=[seller_id])
    buyer = relationship("User", foreign_keys=[buyer_id])
    reserved_by = relationship("User", foreign_keys=[reserved_by_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "community": {"slug": self.community.slug, "name": self.community.name},
            "seller": {"id": self.seller.id, "username": self.seller.username, "display_name": self.seller.display_name},
            "buyer_id": self.buyer_id,
            "title": self.title,
            "author": self.author,
            "genre": self.genre,
            "description": self.description,
            "price": self.price,
            "image_url": self.image_url,
            "status": self.status,
            "reserved_until": self.reservation_expires_at.isoformat() if self.reservation_expires_at else None,
            "created_at": self.created_at.isoformat(),
        }


class CreditTransaction(db.Model):
    __tablename__ = "credit_transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    counterparty_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    book_id = db.Column(db.String(36), db.ForeignKey("books.id", ondelete="SET NULL"), nullable=True)
    amount = db.Column(db.Integer, nullable=False)
    kind = db.Column(db.String(32), nullable=False)
    note = db.Column(db.String(240), nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    user = relationship("User", foreign_keys=[user_id])


class Loan(db.Model):
    __tablename__ = "loans"
    __table_args__ = (CheckConstraint("status in ('requested', 'approved', 'rejected', 'returned')", name="ck_loan_status"),)

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    book_id = db.Column(db.String(36), db.ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    borrower_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lender_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="requested")
    due_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    book = relationship("Book")
    borrower = relationship("User", foreign_keys=[borrower_id])
    lender = relationship("User", foreign_keys=[lender_id])

    def to_dict(self) -> dict:
        def reader(user: User) -> dict:
            return {"id": user.id, "username": user.username, "display_name": user.display_name, "avatar_url": user.avatar_url}
        return {"id": self.id, "book": self.book.to_dict(), "borrower": reader(self.borrower), "lender": reader(self.lender), "status": self.status, "due_at": self.due_at.isoformat() if self.due_at else None, "created_at": self.created_at.isoformat()}


class Discount(db.Model):
    __tablename__ = "discounts"

    code = db.Column(db.String(32), primary_key=True)
    percent = db.Column(db.Integer, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class ChatGroup(db.Model):
    __tablename__ = "chat_groups"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    name = db.Column(db.String(100), nullable=False)
    community_id = db.Column(db.String(36), db.ForeignKey("communities.id", ondelete="CASCADE"), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    community = relationship("Community")
    owner = relationship("User")
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "community": self.community.slug if self.community else None, "owner": self.owner.username, "member_count": len(self.members), "created_at": self.created_at.isoformat()}


class GroupMember(db.Model):
    __tablename__ = "group_members"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_group_member"),)

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.String(36), db.ForeignKey("chat_groups.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    joined_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    group = relationship("ChatGroup", back_populates="members")
    user = relationship("User")


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    group_id = db.Column(db.String(36), db.ForeignKey("chat_groups.id", ondelete="CASCADE"), nullable=True, index=True)
    body = db.Column(db.String(2000), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    sender = relationship("User", foreign_keys=[sender_id])
    recipient = relationship("User", foreign_keys=[recipient_id])
    group = relationship("ChatGroup")

    def to_dict(self) -> dict:
        return {"id": self.id, "sender": self.sender.username, "recipient": self.recipient.username if self.recipient else None, "group_id": self.group_id, "body": self.body, "created_at": self.created_at.isoformat()}


class EmailOutbox(db.Model):
    __tablename__ = "email_outbox"

    id = db.Column(db.Integer, primary_key=True)
    recipient = db.Column(db.String(254), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    body = db.Column(db.String(4000), nullable=False)
    sent_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
