"""Flask-RESTX resources for the versioned Paragrapher API."""

from __future__ import annotations

import logging
import re
import smtplib
import uuid
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from functools import wraps
from pathlib import Path

from flask import current_app, jsonify, request, send_from_directory, session
from flask_restx import Namespace, Resource, fields
from PIL import Image, UnidentifiedImageError
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db
from models import (
    Book,
    Category,
    ChatGroup,
    Community,
    CommunityLike,
    CommunityMember,
    CreditTransaction,
    Discount,
    EmailOutbox,
    GroupMember,
    Loan,
    Message,
    Notification,
    Quote,
    QuoteLike,
    User,
    new_id,
    utcnow,
)

log = logging.getLogger("paragrapher.api")
ns = Namespace("paragrapher", path="/", description="Paragrapher v1")

error_model = ns.model("Error", {
    "error": fields.Nested(ns.model("ErrorDetail", {
        "code": fields.String(required=True),
        "message": fields.String(required=True),
    }))
})
response_model = ns.model("Response", {"data": fields.Raw})
auth_model = ns.model("Credentials", {
    "username": fields.String(required=True),
    "email": fields.String,
    "password": fields.String(required=True),
    "display_name": fields.String,
})
community_model = ns.model("CommunityInput", {
    "name": fields.String(required=True),
    "description": fields.String,
    "is_private": fields.Boolean,
})
quote_model = ns.model("QuoteInput", {
    "text": fields.String(required=True),
    "reference": fields.String,
    "character": fields.String,
    "tags": fields.List(fields.String),
})
book_model = ns.model("BookInput", {
    "title": fields.String(required=True),
    "author": fields.String(required=True),
    "genre": fields.String,
    "description": fields.String,
    "price": fields.Integer,
    "community_slug": fields.String(required=True),
})


def ok(data, status: int = 200):
    return {"data": data}, status


def fail(code: str, message: str, status: int):
    return {"error": {"code": code, "message": message}}, status


def json_body() -> dict:
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else {}


def active_user() -> User | None:
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None


def login_required(func):
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        user = active_user()
        if not user:
            return fail("authentication_required", "Sign in to continue.", 401)
        return func(self, *args, current_user=user, **kwargs)
    return wrapped


def community_by_slug(slug: str) -> Community | None:
    return db.session.scalar(select(Community).where(Community.slug == slug))


def membership(user: User, community: Community) -> CommunityMember | None:
    return db.session.scalar(select(CommunityMember).where(
        CommunityMember.user_id == user.id,
        CommunityMember.community_id == community.id,
    ))


def community_access(user: User | None, community: Community) -> bool:
    return not community.is_private or bool(user and membership(user, community))


def can_moderate(user: User, community: Community) -> bool:
    member = membership(user, community)
    return bool(user.is_admin or (member and member.role in {"owner", "moderator"}))


def page_data(query, page: int = 1, per_page: int = 20) -> dict:
    page = max(1, min(page, 100000))
    per_page = max(1, min(per_page, 50))
    total_query = select(func.count()).select_from(query.order_by(None).subquery())
    total = db.session.scalar(total_query) or 0
    items = db.session.scalars(
        query.limit(per_page).offset((page - 1) * per_page)
    ).all()
    return {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": (total + per_page - 1) // per_page,
    }


def parse_page() -> tuple[int, int]:
    try:
        page = int(request.args.get("page", "1"))
        per_page = int(request.args.get("per_page", "20"))
    except ValueError:
        return 1, 20
    return max(1, page), max(1, min(per_page, 50))


def add_notification(user_id: int, title: str, body: str) -> None:
    db.session.add(Notification(user_id=user_id, title=title[:160], body=body[:500]))


def queue_email(recipient: str, subject: str, body: str) -> None:
    item = EmailOutbox(recipient=recipient, subject=subject[:200], body=body[:4000])
    db.session.add(item)
    if current_app.config.get("MAIL_MODE") == "smtp":
        host = current_app.config.get("SMTP_HOST")
        if not host:
            log.warning("SMTP mode requested without SMTP_HOST; message retained in the outbox")
            return
        message = EmailMessage()
        message["From"] = current_app.config["SMTP_FROM"]
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        try:
            with smtplib.SMTP(host, current_app.config["SMTP_PORT"], timeout=10) as smtp:
                smtp.starttls()
                username = current_app.config.get("SMTP_USERNAME")
                if username:
                    smtp.login(username, current_app.config.get("SMTP_PASSWORD", ""))
                smtp.send_message(message)
            item.sent_at = utcnow()
        except (OSError, smtplib.SMTPException):
            log.exception("Could not send email; message retained in the outbox")
    else:
        log.info("Email queued for %s: %s", recipient, subject)


def quote_query(viewer: User | None = None):
    query = select(Quote).where(Quote.parent_id.is_(None))
    if not viewer:
        query = query.join(Community).where(Community.is_private.is_(False))
    else:
        public_community = Community.is_private.is_(False)
        member_community = select(CommunityMember.id).where(
            CommunityMember.community_id == Community.id,
            CommunityMember.user_id == viewer.id,
        ).exists()
        query = query.join(Community).where(or_(public_community, member_community))
    return query


def require_community(slug: str, user: User | None = None):
    community = community_by_slug(slug)
    if not community:
        return None, fail("community_not_found", "This community does not exist.", 404)
    if not community_access(user, community):
        return None, fail("permission_denied", "Join this private community to view it.", 403)
    return community, None


def validate_tags(value) -> list[str] | None:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > 12:
        return None
    tags = []
    for tag in value:
        if not isinstance(tag, str) or not tag.strip() or len(tag.strip()) > 32:
            return None
        tags.append(tag.strip())
    return list(dict.fromkeys(tags))


def safe_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return (slug or "community")[:72]


def upload_image(upload, prefix: str) -> tuple[str | None, tuple | None]:
    if not upload or not upload.filename:
        return None, fail("file_required", "Choose an image to upload.", 400)
    try:
        image = Image.open(upload.stream)
        image.verify()
        image_format = image.format
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        return None, fail("invalid_image", "Upload a valid PNG, JPEG, or WebP image.", 400)
    extensions = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
    if image_format not in extensions:
        return None, fail("invalid_image", "Upload a valid PNG, JPEG, or WebP image.", 400)
    filename = f"{prefix}-{uuid.uuid4().hex}{extensions[image_format]}"
    folder = Path(current_app.config["UPLOAD_FOLDER"])
    folder.mkdir(parents=True, exist_ok=True)
    upload.stream.seek(0)
    image = Image.open(upload.stream)
    image.thumbnail((1600, 1600))
    image.save(folder / filename, format=image_format, optimize=True)
    return f"/api/v1/uploads/{filename}", None


@ns.route("/auth/register")
class Register(Resource):
    @ns.expect(auth_model, validate=False)
    @ns.response(201, "Account created", response_model)
    @ns.response(400, "Invalid details", error_model)
    def post(self):
        data = json_body()
        username = str(data.get("username", "")).strip()
        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("password", ""))
        display_name = str(data.get("display_name", username)).strip() or username
        if not re.fullmatch(r"[A-Za-z0-9_-]{3,40}", username):
            return fail("invalid_username", "Username must be 3–40 letters, numbers, underscores, or hyphens.", 400)
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            return fail("invalid_email", "Enter a valid email address.", 400)
        if len(password) < 10 or len(password) > 128:
            return fail("invalid_password", "Password must be 10–128 characters long.", 400)
        if len(display_name) > 100:
            return fail("invalid_display_name", "Display name must be 100 characters or shorter.", 400)
        user = User(username=username, email=email, password_hash=generate_password_hash(password), display_name=display_name)
        db.session.add(user)
        try:
            db.session.flush()
            add_notification(user.id, "خوش آمدید", "به پاراگراف‌ر خوش آمدید. جامعه‌ای برای دوستداران کتاب و نقل‌قول‌ها.")
            queue_email(email, "Welcome to Paragrapher", "Your local Paragrapher account is ready.")
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return fail("account_exists", "That username or email is already registered.", 409)
        session.clear()
        session.permanent = True
        session["user_id"] = user.id
        session["csrf_token"] = uuid.uuid4().hex + uuid.uuid4().hex
        return {"data": {"user": user.public_dict(), "csrf_token": session["csrf_token"]}}, 201


@ns.route("/auth/login")
class Login(Resource):
    @ns.expect(auth_model, validate=False)
    @ns.response(200, "Signed in", response_model)
    @ns.response(401, "Invalid credentials", error_model)
    def post(self):
        data = json_body()
        identity = str(data.get("username", data.get("email", ""))).strip()
        password = str(data.get("password", ""))
        user = db.session.scalar(select(User).where(or_(User.username == identity, User.email == identity.lower())))
        if not user or not check_password_hash(user.password_hash, password):
            return fail("invalid_credentials", "Username/email or password is incorrect.", 401)
        session.clear()
        session.permanent = True
        session["user_id"] = user.id
        session["csrf_token"] = uuid.uuid4().hex + uuid.uuid4().hex
        return ok({"user": user.public_dict(), "csrf_token": session["csrf_token"]})


@ns.route("/auth/logout")
class Logout(Resource):
    @login_required
    def post(self, current_user):
        session.clear()
        return ok({"message": "Signed out."})


@ns.route("/auth/me")
class CurrentUser(Resource):
    @login_required
    def get(self, current_user):
        return ok(current_user.public_dict())


@ns.route("/me")
class Profile(Resource):
    @login_required
    @ns.expect(ns.model("ProfileInput", {
        "display_name": fields.String,
        "bio": fields.String,
        "date_of_birth": fields.String,
    }), validate=False)
    def patch(self, current_user):
        data = json_body()
        if "display_name" in data:
            value = str(data["display_name"]).strip()
            if not value or len(value) > 100:
                return fail("invalid_display_name", "Display name must contain 1–100 characters.", 400)
            current_user.display_name = value
        if "bio" in data:
            value = str(data["bio"]).strip()
            if len(value) > 500:
                return fail("bio_too_long", "Bio must be 500 characters or shorter.", 400)
            current_user.bio = value
        if "date_of_birth" in data:
            try:
                current_user.date_of_birth = date.fromisoformat(data["date_of_birth"]) if data["date_of_birth"] else None
            except (TypeError, ValueError):
                return fail("invalid_date", "Use the YYYY-MM-DD date format.", 400)
        db.session.commit()
        return ok(current_user.public_dict())


@ns.route("/me/password")
class ChangePassword(Resource):
    @login_required
    def post(self, current_user):
        data = json_body()
        old_password = str(data.get("old_password", ""))
        new_password = str(data.get("new_password", ""))
        if not check_password_hash(current_user.password_hash, old_password):
            return fail("wrong_password", "Current password is incorrect.", 400)
        if len(new_password) < 10 or len(new_password) > 128:
            return fail("invalid_password", "New password must be 10–128 characters long.", 400)
        current_user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        return ok({"message": "Password changed."})


@ns.route("/me/avatar")
class ProfileAvatar(Resource):
    @login_required
    def post(self, current_user):
        url, error = upload_image(request.files.get("file"), "user")
        if error:
            return error
        current_user.avatar_url = url
        db.session.commit()
        return ok({"avatar_url": url})


@ns.route("/uploads/<string:filename>")
class UploadedFile(Resource):
    def get(self, filename):
        if "/" in filename or ".." in filename:
            return fail("not_found", "Image not found.", 404)
        return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


@ns.route("/me/quotes")
class MyQuotes(Resource):
    @login_required
    def get(self, current_user):
        page, per_page = parse_page()
        pagination = page_data(select(Quote).where(Quote.user_id == current_user.id, Quote.parent_id.is_(None)).order_by(Quote.created_at.desc()), page, per_page)
        pagination["items"] = [item.to_dict(current_user) for item in pagination["items"]]
        return ok(pagination)


@ns.route("/me/books")
class MyBooks(Resource):
    @login_required
    def get(self, current_user):
        books = db.session.scalars(select(Book).where(or_(Book.seller_id == current_user.id, Book.buyer_id == current_user.id)).order_by(Book.created_at.desc())).all()
        return ok([book.to_dict() for book in books])


@ns.route("/me/credit-transactions")
class CreditHistory(Resource):
    @login_required
    def get(self, current_user):
        rows = db.session.scalars(select(CreditTransaction).where(CreditTransaction.user_id == current_user.id).order_by(CreditTransaction.created_at.desc()).limit(100)).all()
        return ok([{"id": row.id, "amount": row.amount, "kind": row.kind, "note": row.note, "created_at": row.created_at.isoformat()} for row in rows])


@ns.route("/notifications")
class Notifications(Resource):
    @login_required
    def get(self, current_user):
        rows = db.session.scalars(select(Notification).where(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).limit(100)).all()
        return ok([row.to_dict() for row in rows])

    @login_required
    def delete(self, current_user):
        db.session.execute(db.delete(Notification).where(Notification.user_id == current_user.id, Notification.read_at.is_not(None)))
        db.session.commit()
        return ok({"message": "Read notifications cleared."})


@ns.route("/notifications/<int:notification_id>/read")
class ReadNotification(Resource):
    @login_required
    def put(self, current_user, notification_id):
        row = db.session.scalar(select(Notification).where(Notification.id == notification_id, Notification.user_id == current_user.id))
        if not row:
            return fail("notification_not_found", "Notification not found.", 404)
        row.read_at = utcnow()
        db.session.commit()
        return ok(row.to_dict())


@ns.route("/communities")
class Communities(Resource):
    @ns.doc(params={"q": "Filter by community name", "page": "Page number", "per_page": "Items per page"})
    def get(self):
        viewer = active_user()
        page, per_page = parse_page()
        query = select(Community).where(Community.is_private.is_(False))
        if viewer:
            member_ids = select(CommunityMember.community_id).where(CommunityMember.user_id == viewer.id)
            query = select(Community).where(or_(Community.is_private.is_(False), Community.id.in_(member_ids)))
        text = request.args.get("q", "").strip()
        if text:
            query = query.where(Community.name.ilike(f"%{text}%"))
        pagination = page_data(query.order_by(Community.name.asc()), page, per_page)
        pagination["items"] = [item.to_dict(viewer) for item in pagination["items"]]
        return ok(pagination)

    @login_required
    @ns.expect(community_model, validate=False)
    def post(self, current_user):
        data = json_body()
        name = str(data.get("name", "")).strip()
        description = str(data.get("description", "")).strip()
        if not name or len(name) > 120 or len(description) > 600:
            return fail("invalid_community", "Community name is required; name and description must fit their limits.", 400)
        slug = safe_slug(name)
        base_slug = slug
        counter = 2
        while db.session.scalar(select(Community.id).where(Community.slug == slug)):
            slug = f"{base_slug[:68]}-{counter}"
            counter += 1
        community = Community(slug=slug, name=name, description=description, is_private=bool(data.get("is_private", False)), owner_id=current_user.id)
        db.session.add(community)
        db.session.flush()
        db.session.add(CommunityMember(community_id=community.id, user_id=current_user.id, role="owner"))
        db.session.commit()
        return ok(community.to_dict(current_user), 201)


@ns.route("/communities/top")
class TopCommunities(Resource):
    def get(self):
        viewer = active_user()
        rows = db.session.execute(
            select(Community, func.count(CommunityMember.id).label("members_count"))
            .outerjoin(CommunityMember, CommunityMember.community_id == Community.id)
            .where(Community.is_private.is_(False))
            .group_by(Community.id)
            .order_by(func.count(CommunityMember.id).desc(), Community.name.asc())
            .limit(12)
        ).all()
        return ok([community.to_dict(viewer) for community, _count in rows])


@ns.route("/communities/<string:slug>")
class CommunityDetail(Resource):
    def get(self, slug):
        community, error = require_community(slug, active_user())
        if error:
            return error
        data = community.to_dict(active_user())
        data["categories"] = [item.to_dict() for item in db.session.scalars(select(Category).where(Category.community_id == community.id).order_by(Category.name)).all()]
        return ok(data)

    @login_required
    @ns.expect(community_model, validate=False)
    def patch(self, slug, current_user):
        community, error = require_community(slug, current_user)
        if error:
            return error
        if not can_moderate(current_user, community):
            return fail("permission_denied", "Only community moderators can edit this community.", 403)
        data = json_body()
        if "name" in data:
            value = str(data["name"]).strip()
            if not value or len(value) > 120:
                return fail("invalid_community", "Name must contain 1–120 characters.", 400)
            community.name = value
        if "description" in data:
            value = str(data["description"]).strip()
            if len(value) > 600:
                return fail("invalid_community", "Description must be 600 characters or shorter.", 400)
            community.description = value
        if "is_private" in data:
            community.is_private = bool(data["is_private"])
        db.session.commit()
        return ok(community.to_dict(current_user))


@ns.route("/communities/<string:slug>/join")
class JoinCommunity(Resource):
    @login_required
    def post(self, slug, current_user):
        community = community_by_slug(slug)
        if not community:
            return fail("community_not_found", "This community does not exist.", 404)
        if community.is_private:
            return fail("private_community", "Ask a community moderator for an invitation.", 403)
        if not membership(current_user, community):
            db.session.add(CommunityMember(community_id=community.id, user_id=current_user.id))
            add_notification(community.owner_id, "عضو جدید", f"{current_user.display_name} به جامعهٔ «{community.name}» پیوست.")
            db.session.commit()
        return ok(community.to_dict(current_user))

    @login_required
    def delete(self, slug, current_user):
        community = community_by_slug(slug)
        if not community:
            return fail("community_not_found", "This community does not exist.", 404)
        member = membership(current_user, community)
        if member and member.role == "owner":
            return fail("owner_cannot_leave", "Transfer ownership before leaving this community.", 409)
        if member:
            db.session.delete(member)
            db.session.commit()
        return ok({"message": "You left the community."})


@ns.route("/communities/<string:slug>/members")
class CommunityMembers(Resource):
    def get(self, slug):
        community, error = require_community(slug, active_user())
        if error:
            return error
        rows = db.session.scalars(select(CommunityMember).where(CommunityMember.community_id == community.id).order_by(CommunityMember.joined_at)).all()
        return ok([{"id": row.user.id, "username": row.user.username, "display_name": row.user.display_name, "role": row.role, "joined_at": row.joined_at.isoformat()} for row in rows])

    @login_required
    def post(self, slug, current_user):
        community = community_by_slug(slug)
        if not community:
            return fail("community_not_found", "This community does not exist.", 404)
        if not can_moderate(current_user, community):
            return fail("permission_denied", "Only community moderators can invite readers.", 403)
        username = str(json_body().get("username", "")).strip()
        invitee = db.session.scalar(select(User).where(User.username == username))
        if not invitee:
            return fail("user_not_found", "Reader not found.", 404)
        if not membership(invitee, community):
            db.session.add(CommunityMember(community_id=community.id, user_id=invitee.id))
            add_notification(invitee.id, "دعوت به جامعه", f"شما به جامعه‌ی «{community.name}» دعوت شدید.")
            db.session.commit()
        return ok(community.to_dict(invitee), 201)


@ns.route("/communities/<string:slug>/members/me")
class CommunitySubscription(Resource):
    @login_required
    def patch(self, slug, current_user):
        community = community_by_slug(slug)
        if not community:
            return fail("community_not_found", "This community does not exist.", 404)
        member = membership(current_user, community)
        if not member:
            return fail("membership_required", "Join the community first.", 403)
        member.subscribed = bool(json_body().get("subscribed", True))
        db.session.commit()
        return ok({"subscribed": member.subscribed})


@ns.route("/communities/<string:slug>/likes/me")
class CommunityLikeResource(Resource):
    @login_required
    def put(self, slug, current_user):
        community, error = require_community(slug, current_user)
        if error:
            return error
        if not db.session.get(CommunityLike, (current_user.id, community.id)):
            db.session.add(CommunityLike(user_id=current_user.id, community_id=community.id))
            db.session.commit()
        return ok(community.to_dict(current_user))

    @login_required
    def delete(self, slug, current_user):
        community = community_by_slug(slug)
        if not community:
            return fail("community_not_found", "This community does not exist.", 404)
        item = db.session.get(CommunityLike, (current_user.id, community.id))
        if item:
            db.session.delete(item)
            db.session.commit()
        return ok(community.to_dict(current_user))


@ns.route("/communities/<string:slug>/categories")
class CommunityCategories(Resource):
    def get(self, slug):
        community, error = require_community(slug, active_user())
        if error:
            return error
        rows = db.session.scalars(select(Category).where(Category.community_id == community.id).order_by(Category.name)).all()
        return ok([row.to_dict() for row in rows])

    @login_required
    def post(self, slug, current_user):
        community, error = require_community(slug, current_user)
        if error:
            return error
        if not can_moderate(current_user, community):
            return fail("permission_denied", "Only community moderators can add categories.", 403)
        data = json_body()
        name = str(data.get("name", "")).strip()
        description = str(data.get("description", "")).strip()
        if not name or len(name) > 80 or len(description) > 300:
            return fail("invalid_category", "Category name is required and must be 80 characters or shorter.", 400)
        category = Category(community_id=community.id, name=name, description=description)
        db.session.add(category)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return fail("category_exists", "That category already exists in this community.", 409)
        return ok(category.to_dict(), 201)


@ns.route("/communities/<string:slug>/avatar")
class CommunityAvatar(Resource):
    @login_required
    def post(self, slug, current_user):
        community, error = require_community(slug, current_user)
        if error:
            return error
        if not can_moderate(current_user, community):
            return fail("permission_denied", "Only community moderators can change its image.", 403)
        url, error = upload_image(request.files.get("file"), "community")
        if error:
            return error
        community.avatar_url = url
        db.session.commit()
        return ok({"avatar_url": url})


@ns.route("/quotes")
class Quotes(Resource):
    @ns.doc(params={"community": "Community slug", "sort": "recent or popular", "page": "Page number"})
    def get(self):
        viewer = active_user()
        page, per_page = parse_page()
        query = quote_query(viewer)
        slug = request.args.get("community", "").strip()
        if slug:
            community = community_by_slug(slug)
            if not community:
                return fail("community_not_found", "This community does not exist.", 404)
            if not community_access(viewer, community):
                return fail("permission_denied", "Join this private community to view its quotes.", 403)
            query = query.where(Quote.community_id == community.id)
        text = request.args.get("q", "").strip()
        if text:
            query = query.where(or_(Quote.text.ilike(f"%{text}%"), Quote.reference.ilike(f"%{text}%"), Quote.character.ilike(f"%{text}%")))
        if request.args.get("sort") == "popular":
            query = query.outerjoin(QuoteLike).group_by(Quote.id).order_by(func.count(QuoteLike.user_id).desc(), Quote.created_at.desc())
        else:
            query = query.order_by(Quote.created_at.desc())
        pagination = page_data(query, page, per_page)
        pagination["items"] = [item.to_dict(viewer) for item in pagination["items"]]
        return ok(pagination)


@ns.route("/quotes/daily")
class QuoteOfTheDay(Resource):
    def get(self):
        viewer = active_user()
        candidates = db.session.scalars(quote_query(viewer).order_by(Quote.id.asc())).all()
        if not candidates:
            return ok({"date": datetime.now(timezone.utc).date().isoformat(), "quote": None})
        day = datetime.now(timezone.utc).date()
        offset = int(day.strftime("%Y%m%d")) % len(candidates)
        quote = candidates[offset]
        return ok({"date": day.isoformat(), "quote": quote.to_dict(viewer)})


@ns.route("/quotes/popular")
class PopularQuotes(Resource):
    def get(self):
        viewer = active_user()
        page, per_page = parse_page()
        query = quote_query(viewer).outerjoin(QuoteLike).group_by(Quote.id).order_by(func.count(QuoteLike.user_id).desc(), Quote.created_at.desc())
        pagination = page_data(query, page, per_page)
        pagination["items"] = [item.to_dict(viewer) for item in pagination["items"]]
        return ok(pagination)


@ns.route("/communities/<string:slug>/quotes")
class CommunityQuotes(Resource):
    def get(self, slug):
        viewer = active_user()
        community, error = require_community(slug, viewer)
        if error:
            return error
        page, per_page = parse_page()
        pagination = page_data(select(Quote).where(Quote.community_id == community.id, Quote.parent_id.is_(None)).order_by(Quote.created_at.desc()), page, per_page)
        pagination["items"] = [item.to_dict(viewer) for item in pagination["items"]]
        return ok(pagination)

    @login_required
    @ns.expect(quote_model, validate=False)
    def post(self, slug, current_user):
        community, error = require_community(slug, current_user)
        if error:
            return error
        if not membership(current_user, community):
            return fail("membership_required", "Join the community before posting a quote.", 403)
        data = json_body()
        text = str(data.get("text", "")).strip()
        reference = str(data.get("reference", "")).strip()
        character = str(data.get("character", "")).strip()
        tags = validate_tags(data.get("tags"))
        if not text or len(text) > 2000 or len(reference) > 250 or len(character) > 150 or tags is None:
            return fail("invalid_quote", "Quote text is required; text, reference, character, or tags exceed their limits.", 400)
        quote = Quote(community_id=community.id, user_id=current_user.id, text=text, reference=reference, character=character, tags=tags)
        db.session.add(quote)
        for member in community.members:
            if member.user_id != current_user.id and member.subscribed:
                add_notification(member.user_id, "نقل‌قول تازه", f"در جامعهٔ «{community.name}» نقل‌قول تازه‌ای ثبت شد.")
        db.session.commit()
        return ok(quote.to_dict(current_user), 201)


@ns.route("/quotes/<string:quote_id>")
class QuoteDetail(Resource):
    def get(self, quote_id):
        quote = db.session.get(Quote, quote_id)
        if not quote:
            return fail("quote_not_found", "Quote not found.", 404)
        if not community_access(active_user(), quote.community):
            return fail("permission_denied", "Join this private community to view the quote.", 403)
        return ok(quote.to_dict(active_user(), include_replies=True))

    @login_required
    @ns.expect(quote_model, validate=False)
    def patch(self, quote_id, current_user):
        quote = db.session.get(Quote, quote_id)
        if not quote:
            return fail("quote_not_found", "Quote not found.", 404)
        if quote.parent_id or (quote.user_id != current_user.id and not can_moderate(current_user, quote.community)):
            return fail("permission_denied", "You can edit only your own quotes or quotes in a community you moderate.", 403)
        data = json_body()
        if "text" in data:
            value = str(data["text"]).strip()
            if not value or len(value) > 2000:
                return fail("invalid_quote", "Quote text must contain 1–2000 characters.", 400)
            quote.text = value
        if "reference" in data:
            value = str(data["reference"]).strip()
            if len(value) > 250:
                return fail("invalid_quote", "Reference must be 250 characters or shorter.", 400)
            quote.reference = value
        if "character" in data:
            value = str(data["character"]).strip()
            if len(value) > 150:
                return fail("invalid_quote", "Character must be 150 characters or shorter.", 400)
            quote.character = value
        if "tags" in data:
            tags = validate_tags(data["tags"])
            if tags is None:
                return fail("invalid_tags", "Use up to 12 tags, each no longer than 32 characters.", 400)
            quote.tags = tags
        db.session.commit()
        return ok(quote.to_dict(current_user))

    @login_required
    def delete(self, quote_id, current_user):
        quote = db.session.get(Quote, quote_id)
        if not quote:
            return fail("quote_not_found", "Quote not found.", 404)
        if quote.user_id != current_user.id and not can_moderate(current_user, quote.community):
            return fail("permission_denied", "You cannot delete this quote.", 403)
        db.session.delete(quote)
        db.session.commit()
        return ok({"message": "Quote deleted."})


@ns.route("/quotes/<string:quote_id>/likes/me")
class QuoteLikeResource(Resource):
    @login_required
    def put(self, quote_id, current_user):
        quote = db.session.get(Quote, quote_id)
        if not quote:
            return fail("quote_not_found", "Quote not found.", 404)
        if not community_access(current_user, quote.community):
            return fail("permission_denied", "Join this private community first.", 403)
        if not db.session.get(QuoteLike, (current_user.id, quote.id)):
            db.session.add(QuoteLike(user_id=current_user.id, quote_id=quote.id))
            if quote.user_id != current_user.id:
                add_notification(quote.user_id, "پسند تازه", f"{current_user.display_name} نقل‌قول شما را پسندید.")
            db.session.commit()
        return ok(quote.to_dict(current_user))

    @login_required
    def delete(self, quote_id, current_user):
        quote = db.session.get(Quote, quote_id)
        if not quote:
            return fail("quote_not_found", "Quote not found.", 404)
        item = db.session.get(QuoteLike, (current_user.id, quote.id))
        if item:
            db.session.delete(item)
            db.session.commit()
        return ok(quote.to_dict(current_user))


@ns.route("/quotes/<string:quote_id>/replies")
class QuoteReplies(Resource):
    def get(self, quote_id):
        parent = db.session.get(Quote, quote_id)
        if not parent or parent.parent_id:
            return fail("quote_not_found", "Quote not found.", 404)
        if not community_access(active_user(), parent.community):
            return fail("permission_denied", "Join this private community first.", 403)
        rows = db.session.scalars(select(Quote).where(Quote.parent_id == parent.id).order_by(Quote.created_at)).all()
        return ok([item.to_dict(active_user()) for item in rows])

    @login_required
    def post(self, quote_id, current_user):
        parent = db.session.get(Quote, quote_id)
        if not parent or parent.parent_id:
            return fail("quote_not_found", "Quote not found.", 404)
        if not membership(current_user, parent.community):
            return fail("membership_required", "Join this community before replying.", 403)
        text = str(json_body().get("text", "")).strip()
        if not text or len(text) > 1000:
            return fail("invalid_reply", "Reply must contain 1–1000 characters.", 400)
        reply = Quote(community_id=parent.community_id, user_id=current_user.id, text=text, reference=parent.reference, character="", parent_id=parent.id, tags=[])
        db.session.add(reply)
        if parent.user_id != current_user.id:
            add_notification(parent.user_id, "پاسخ تازه", f"{current_user.display_name} به نقل‌قول شما پاسخ داد.")
        db.session.commit()
        return ok(reply.to_dict(current_user), 201)


@ns.route("/search")
class Search(Resource):
    @ns.doc(params={"q": "Search text", "type": "all, communities, quotes, or books", "page": "Page number"})
    def get(self):
        text = request.args.get("q", "").strip()
        kind = request.args.get("type", "all")
        if len(text) < 2 or len(text) > 100:
            return fail("invalid_query", "Search must contain 2–100 characters.", 400)
        if kind not in {"all", "communities", "quotes", "books"}:
            return fail("invalid_search_type", "Choose all, communities, quotes, or books.", 400)
        viewer = active_user()
        pattern = f"%{text}%"
        result = {}
        if kind in {"all", "communities"}:
            rows = db.session.scalars(select(Community).where(Community.is_private.is_(False), or_(Community.name.ilike(pattern), Community.description.ilike(pattern))).limit(10)).all()
            result["communities"] = [row.to_dict(viewer) for row in rows]
        if kind in {"all", "quotes"}:
            rows = db.session.scalars(quote_query(viewer).where(or_(Quote.text.ilike(pattern), Quote.reference.ilike(pattern), Quote.character.ilike(pattern))).order_by(Quote.created_at.desc()).limit(15)).all()
            result["quotes"] = [row.to_dict(viewer) for row in rows]
        if kind in {"all", "books"}:
            rows = db.session.scalars(select(Book).join(Community).where(Book.status == "available", Community.is_private.is_(False), or_(Book.title.ilike(pattern), Book.author.ilike(pattern), Book.genre.ilike(pattern))).order_by(Book.created_at.desc()).limit(10)).all()
            result["books"] = [row.to_dict() for row in rows]
        return ok(result)


@ns.route("/search/suggestions")
class Suggestions(Resource):
    def get(self):
        prefix = request.args.get("q", "").strip()
        if len(prefix) < 1 or len(prefix) > 80:
            return ok([])
        pattern = f"%{prefix}%"
        communities = db.session.scalars(select(Community.name).where(Community.is_private.is_(False), Community.name.ilike(pattern)).limit(5)).all()
        quotes = db.session.scalars(select(Quote.text).join(Community).where(Community.is_private.is_(False), Quote.parent_id.is_(None), Quote.text.ilike(pattern)).limit(5)).all()
        return ok([{"type": "community", "text": value} for value in communities] + [{"type": "quote", "text": value[:100]} for value in quotes])


@ns.route("/communities/<string:slug>/search")
class CommunitySearch(Resource):
    def get(self, slug):
        community, error = require_community(slug, active_user())
        if error:
            return error
        text = request.args.get("q", "").strip()
        if len(text) < 2 or len(text) > 100:
            return fail("invalid_query", "Search must contain 2–100 characters.", 400)
        rows = db.session.scalars(select(Quote).where(Quote.community_id == community.id, Quote.parent_id.is_(None), or_(Quote.text.ilike(f"%{text}%"), Quote.reference.ilike(f"%{text}%"), Quote.character.ilike(f"%{text}%"))).order_by(Quote.created_at.desc()).limit(30)).all()
        return ok([row.to_dict(active_user()) for row in rows])


@ns.route("/users/<string:username>")
class PublicProfile(Resource):
    def get(self, username):
        user = db.session.scalar(select(User).where(User.username == username))
        if not user:
            return fail("user_not_found", "Reader not found.", 404)
        communities = db.session.scalars(select(Community).join(CommunityMember).where(CommunityMember.user_id == user.id, Community.is_private.is_(False))).all()
        return ok({"id": user.id, "username": user.username, "display_name": user.display_name, "bio": user.bio, "avatar_url": user.avatar_url, "communities": [item.to_dict(active_user()) for item in communities]})


@ns.route("/books")
class Books(Resource):
    def get(self):
        page, per_page = parse_page()
        viewer = active_user()
        visible_listing = Book.status == "available"
        if viewer:
            visible_listing = or_(
                visible_listing,
                and_(Book.status == "reserved", Book.reserved_by_id == viewer.id),
            )
        query = select(Book).join(Community).where(visible_listing, Community.is_private.is_(False)).order_by(Book.created_at.desc())
        slug = request.args.get("community")
        if slug:
            community = community_by_slug(slug)
            if not community:
                return fail("community_not_found", "This community does not exist.", 404)
            if not community_access(viewer, community):
                return fail("permission_denied", "Join this private community first.", 403)
            query = select(Book).where(visible_listing, Book.community_id == community.id).order_by(Book.created_at.desc())
        pagination = page_data(query, page, per_page)
        pagination["items"] = [item.to_dict() for item in pagination["items"]]
        return ok(pagination)

    @login_required
    @ns.expect(book_model, validate=False)
    def post(self, current_user):
        data = json_body()
        community, error = require_community(str(data.get("community_slug", "")), current_user)
        if error:
            return error
        if not membership(current_user, community):
            return fail("membership_required", "Join the community before listing a book.", 403)
        title = str(data.get("title", "")).strip()
        author = str(data.get("author", "")).strip()
        genre = str(data.get("genre", "")).strip()
        description = str(data.get("description", "")).strip()
        try:
            price = int(data.get("price", 0))
        except (TypeError, ValueError):
            return fail("invalid_price", "Price must be a whole number of demo credits.", 400)
        if not title or not author or len(title) > 180 or len(author) > 160 or len(genre) > 80 or len(description) > 1200 or not 0 <= price <= 100000:
            return fail("invalid_book", "Check the required title/author and the field limits.", 400)
        book = Book(community_id=community.id, seller_id=current_user.id, title=title, author=author, genre=genre, description=description, price=price)
        db.session.add(book)
        db.session.commit()
        return ok(book.to_dict(), 201)


@ns.route("/books/<string:book_id>")
class BookDetail(Resource):
    def get(self, book_id):
        book = db.session.get(Book, book_id)
        if not book:
            return fail("book_not_found", "Book not found.", 404)
        if not community_access(active_user(), book.community):
            return fail("permission_denied", "Join this private community to view the listing.", 403)
        return ok(book.to_dict())

    @login_required
    def patch(self, book_id, current_user):
        book = db.session.get(Book, book_id)
        if not book:
            return fail("book_not_found", "Book not found.", 404)
        if book.seller_id != current_user.id or book.status == "sold":
            return fail("permission_denied", "Only the seller can edit an available listing.", 403)
        data = json_body()
        for key, limit in (("title", 180), ("author", 160), ("genre", 80), ("description", 1200)):
            if key in data:
                value = str(data[key]).strip()
                if key in {"title", "author"} and not value:
                    return fail("invalid_book", f"{key.title()} is required.", 400)
                if len(value) > limit:
                    return fail("invalid_book", f"{key.title()} exceeds its limit.", 400)
                setattr(book, key, value)
        if "price" in data:
            try:
                price = int(data["price"])
            except (TypeError, ValueError):
                return fail("invalid_price", "Price must be a whole number of demo credits.", 400)
            if not 0 <= price <= 100000:
                return fail("invalid_price", "Price must be between 0 and 100000 demo credits.", 400)
            book.price = price
        db.session.commit()
        return ok(book.to_dict())

    @login_required
    def delete(self, book_id, current_user):
        book = db.session.get(Book, book_id)
        if not book:
            return fail("book_not_found", "Book not found.", 404)
        if book.seller_id != current_user.id or book.status == "sold":
            return fail("permission_denied", "Only the seller can remove an unsold listing.", 403)
        db.session.delete(book)
        db.session.commit()
        return ok({"message": "Listing removed."})


@ns.route("/books/<string:book_id>/image")
class BookImage(Resource):
    @login_required
    def post(self, book_id, current_user):
        book = db.session.get(Book, book_id)
        if not book:
            return fail("book_not_found", "Book not found.", 404)
        if book.seller_id != current_user.id:
            return fail("permission_denied", "Only the seller can change the listing image.", 403)
        url, error = upload_image(request.files.get("file"), "book")
        if error:
            return error
        book.image_url = url
        db.session.commit()
        return ok({"image_url": url})


@ns.route("/books/<string:book_id>/reserve")
class ReserveBook(Resource):
    @login_required
    def post(self, book_id, current_user):
        book = db.session.scalar(select(Book).where(Book.id == book_id).with_for_update())
        if not book:
            return fail("book_not_found", "Book not found.", 404)
        if book.seller_id == current_user.id:
            return fail("own_listing", "You cannot reserve your own listing.", 400)
        if not community_access(current_user, book.community):
            return fail("permission_denied", "Join this private community first.", 403)
        if book.status == "reserved" and book.reservation_expires_at and book.reservation_expires_at <= utcnow():
            book.status = "available"
            book.reserved_by_id = None
            book.reservation_expires_at = None
        if book.status != "available":
            return fail("book_unavailable", "This book is already reserved or sold.", 409)
        book.status = "reserved"
        book.reserved_by_id = current_user.id
        book.reservation_expires_at = utcnow() + timedelta(minutes=30)
        db.session.commit()
        return ok(book.to_dict())

    @login_required
    def delete(self, book_id, current_user):
        book = db.session.scalar(select(Book).where(Book.id == book_id).with_for_update())
        if not book:
            return fail("book_not_found", "Book not found.", 404)
        if book.reserved_by_id != current_user.id:
            return fail("permission_denied", "Only the reader who reserved this book can release it.", 403)
        book.status = "available"
        book.reserved_by_id = None
        book.reservation_expires_at = None
        db.session.commit()
        return ok(book.to_dict())


@ns.route("/books/<string:book_id>/purchase")
class PurchaseBook(Resource):
    @login_required
    def post(self, book_id, current_user):
        book = db.session.scalar(select(Book).where(Book.id == book_id).with_for_update())
        if not book:
            return fail("book_not_found", "Book not found.", 404)
        if book.seller_id == current_user.id:
            return fail("own_listing", "You cannot purchase your own listing.", 400)
        if not community_access(current_user, book.community):
            return fail("permission_denied", "Join this private community first.", 403)
        if book.status == "reserved" and book.reservation_expires_at and book.reservation_expires_at <= utcnow():
            book.status = "available"
            book.reserved_by_id = None
            book.reservation_expires_at = None
        if book.status == "reserved" and book.reserved_by_id != current_user.id:
            return fail("book_reserved", "This book is reserved by another reader.", 409)
        if book.status == "sold":
            return fail("book_sold", "This book has already been sold.", 409)
        data = json_body()
        price = book.price
        code = str(data.get("discount_code", "")).strip().upper()
        if code:
            discount = db.session.get(Discount, code)
            if not discount:
                return fail("discount_not_found", "Discount code not found.", 404)
            price = max(0, (price * (100 - discount.percent) + 99) // 100)
        buyer = db.session.scalar(select(User).where(User.id == current_user.id).with_for_update())
        seller = db.session.scalar(select(User).where(User.id == book.seller_id).with_for_update())
        if buyer.credit_balance < price:
            return fail("insufficient_demo_credits", "Add local demo credits before purchasing this book.", 400)
        buyer.credit_balance -= price
        seller.credit_balance += price
        book.buyer_id = buyer.id
        book.status = "sold"
        book.reserved_by_id = None
        book.reservation_expires_at = None
        db.session.add(CreditTransaction(user_id=buyer.id, counterparty_id=seller.id, book_id=book.id, amount=-price, kind="book_purchase", note=book.title))
        db.session.add(CreditTransaction(user_id=seller.id, counterparty_id=buyer.id, book_id=book.id, amount=price, kind="book_sale", note=book.title))
        add_notification(buyer.id, "خرید کتاب", f"کتاب «{book.title}» با {price} اعتبار نمایشی خریداری شد.")
        add_notification(seller.id, "فروش کتاب", f"کتاب «{book.title}» فروخته شد.")
        db.session.commit()
        return ok({"book": book.to_dict(), "credit_balance": buyer.credit_balance, "charged_demo_credits": price})


@ns.route("/credits/demo")
class DemoCredits(Resource):
    @login_required
    def post(self, current_user):
        if not current_app.config["DEMO_CREDITS_ENABLED"]:
            return fail("demo_credits_disabled", "Demo credits are disabled outside local development.", 403)
        try:
            amount = int(json_body().get("amount", 0))
        except (TypeError, ValueError):
            return fail("invalid_amount", "Amount must be a whole number.", 400)
        if not 1 <= amount <= 500:
            return fail("invalid_amount", "Add between 1 and 500 demo credits at a time.", 400)
        current_user.credit_balance += amount
        db.session.add(CreditTransaction(user_id=current_user.id, amount=amount, kind="demo_top_up", note="Local demo balance"))
        db.session.commit()
        return ok({"credit_balance": current_user.credit_balance})


@ns.route("/discounts/<string:code>")
class DiscountDetail(Resource):
    def get(self, code):
        discount = db.session.get(Discount, code.strip().upper())
        if not discount:
            return fail("discount_not_found", "Discount code not found.", 404)
        result = {"code": discount.code, "percent": discount.percent}
        if request.args.get("price") is not None:
            try:
                price = int(request.args["price"])
            except ValueError:
                return fail("invalid_price", "Price must be a whole number.", 400)
            result["discounted_price"] = max(0, (price * (100 - discount.percent) + 99) // 100)
        return ok(result)


@ns.route("/discounts")
class Discounts(Resource):
    @login_required
    def post(self, current_user):
        if not current_user.is_admin:
            return fail("permission_denied", "Only a local administrator can create discount codes.", 403)
        data = json_body()
        code = str(data.get("code", "")).strip().upper()
        try:
            percent = int(data.get("percent", 0))
        except (TypeError, ValueError):
            return fail("invalid_discount", "Discount percentage must be a whole number.", 400)
        if not re.fullmatch(r"[A-Z0-9_-]{3,32}", code) or not 1 <= percent <= 90:
            return fail("invalid_discount", "Use a 3–32 character code and a discount between 1% and 90%.", 400)
        discount = Discount(code=code, percent=percent, created_by_id=current_user.id)
        db.session.add(discount)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return fail("discount_exists", "That code already exists.", 409)
        return ok({"code": discount.code, "percent": discount.percent}, 201)


@ns.route("/discounts/email-top-users")
class EmailDiscount(Resource):
    @login_required
    def post(self, current_user):
        return send_discount_to_top_users(current_user, json_body().get("code", ""))


def send_discount_to_top_users(current_user: User, raw_code: str):
    if not current_user.is_admin:
        return fail("permission_denied", "Only a local administrator can send a discount announcement.", 403)
    code = str(raw_code).strip().upper()
    discount = db.session.get(Discount, code)
    if not discount:
        return fail("discount_not_found", "Create a discount code before announcing it.", 404)
    users = db.session.scalars(select(User).where(User.id != current_user.id).order_by(User.credit_balance.desc()).limit(20)).all()
    for user in users:
        queue_email(user.email, "Paragrapher community discount", f"Use {discount.code} for {discount.percent}% off a demo-credit book purchase.")
        add_notification(user.id, "کد تخفیف تازه", f"کد {discount.code} برای خرید نمایشی شما آماده است.")
    db.session.commit()
    return ok({"queued": len(users), "mode": current_app.config["MAIL_MODE"]})


@ns.route("/loans")
class Loans(Resource):
    @login_required
    def get(self, current_user):
        rows = db.session.scalars(select(Loan).where(or_(Loan.borrower_id == current_user.id, Loan.lender_id == current_user.id)).order_by(Loan.created_at.desc())).all()
        return ok([row.to_dict() for row in rows])

    @login_required
    def post(self, current_user):
        book_id = str(json_body().get("book_id", ""))
        book = db.session.get(Book, book_id)
        if not book:
            return fail("book_not_found", "Book not found.", 404)
        if book.seller_id == current_user.id:
            return fail("own_listing", "You cannot request your own book.", 400)
        if book.status == "sold":
            return fail("book_unavailable", "A sold book cannot be borrowed.", 409)
        if not community_access(current_user, book.community):
            return fail("permission_denied", "Join this private community first.", 403)
        active = db.session.scalar(select(Loan.id).where(Loan.book_id == book.id, Loan.status.in_(["requested", "approved"])))
        if active:
            return fail("loan_exists", "This book already has an active loan request.", 409)
        loan = Loan(book_id=book.id, borrower_id=current_user.id, lender_id=book.seller_id)
        db.session.add(loan)
        add_notification(book.seller_id, "درخواست امانت", f"{current_user.display_name} برای امانت کتاب «{book.title}» درخواست داد.")
        db.session.commit()
        return ok(loan.to_dict(), 201)


@ns.route("/loans/<string:loan_id>")
class LoanDetail(Resource):
    @login_required
    def patch(self, loan_id, current_user):
        loan = db.session.get(Loan, loan_id)
        if not loan:
            return fail("loan_not_found", "Loan request not found.", 404)
        status = str(json_body().get("status", ""))
        if status not in {"approved", "rejected", "returned"}:
            return fail("invalid_loan_status", "Choose approved, rejected, or returned.", 400)
        allowed = (status in {"approved", "rejected"} and current_user.id == loan.lender_id and loan.status == "requested") or (status == "returned" and current_user.id == loan.borrower_id and loan.status == "approved")
        if not allowed:
            return fail("permission_denied", "You cannot make that change to this loan.", 403)
        loan.status = status
        if status == "approved":
            loan.due_at = utcnow() + timedelta(days=21)
        recipient = loan.borrower_id if current_user.id == loan.lender_id else loan.lender_id
        add_notification(recipient, "وضعیت امانت", f"درخواست امانت «{loan.book.title}»: {status}")
        db.session.commit()
        return ok(loan.to_dict())


@ns.route("/borrowed-books")
class BorrowedBooks(Resource):
    @login_required
    def get(self, current_user):
        rows = db.session.scalars(select(Loan).where(Loan.borrower_id == current_user.id, Loan.status == "approved").order_by(Loan.due_at)).all()
        return ok([row.to_dict() for row in rows])


@ns.route("/groups")
class Groups(Resource):
    def get(self):
        viewer = active_user()
        query = select(ChatGroup).outerjoin(Community, ChatGroup.community_id == Community.id)
        if viewer:
            member_community = select(CommunityMember.id).where(
                CommunityMember.community_id == Community.id,
                CommunityMember.user_id == viewer.id,
            ).exists()
            group_member = select(GroupMember.id).where(
                GroupMember.group_id == ChatGroup.id,
                GroupMember.user_id == viewer.id,
            ).exists()
            query = query.where(or_(ChatGroup.community_id.is_(None), Community.is_private.is_(False), member_community, group_member))
        else:
            query = query.where(or_(ChatGroup.community_id.is_(None), Community.is_private.is_(False)))
        rows = db.session.scalars(query.order_by(ChatGroup.name)).all()
        return ok([row.to_dict() for row in rows])

    @login_required
    def post(self, current_user):
        data = json_body()
        name = str(data.get("name", "")).strip()
        if not name or len(name) > 100:
            return fail("invalid_group", "Group name must contain 1–100 characters.", 400)
        community = None
        slug = str(data.get("community_slug", "")).strip()
        if slug:
            community, error = require_community(slug, current_user)
            if error:
                return error
            if not membership(current_user, community):
                return fail("membership_required", "Join the community before creating a group.", 403)
        group = ChatGroup(name=name, community_id=community.id if community else None, owner_id=current_user.id)
        db.session.add(group)
        db.session.flush()
        db.session.add(GroupMember(group_id=group.id, user_id=current_user.id))
        db.session.commit()
        return ok(group.to_dict(), 201)


@ns.route("/groups/<string:group_id>")
class GroupDetail(Resource):
    @login_required
    def get(self, group_id, current_user):
        group = db.session.get(ChatGroup, group_id)
        if not group:
            return fail("group_not_found", "Group not found.", 404)
        if not db.session.scalar(select(GroupMember.id).where(GroupMember.group_id == group.id, GroupMember.user_id == current_user.id)):
            return fail("permission_denied", "Join the group to view its members and messages.", 403)
        data = group.to_dict()
        data["members"] = [{"username": item.user.username, "display_name": item.user.display_name} for item in group.members]
        return ok(data)


@ns.route("/groups/<string:group_id>/join")
class JoinGroup(Resource):
    @login_required
    def post(self, group_id, current_user):
        group = db.session.get(ChatGroup, group_id)
        if not group:
            return fail("group_not_found", "Group not found.", 404)
        if group.community and not membership(current_user, group.community):
            return fail("membership_required", "Join the community first.", 403)
        if not db.session.scalar(select(GroupMember.id).where(GroupMember.group_id == group.id, GroupMember.user_id == current_user.id)):
            db.session.add(GroupMember(group_id=group.id, user_id=current_user.id))
            db.session.commit()
        return ok(group.to_dict())


@ns.route("/groups/<string:group_id>/messages")
class GroupMessages(Resource):
    @login_required
    def get(self, group_id, current_user):
        group = db.session.get(ChatGroup, group_id)
        if not group:
            return fail("group_not_found", "Group not found.", 404)
        if not db.session.scalar(select(GroupMember.id).where(GroupMember.group_id == group.id, GroupMember.user_id == current_user.id)):
            return fail("permission_denied", "Join the group before reading messages.", 403)
        rows = db.session.scalars(select(Message).where(Message.group_id == group.id).order_by(Message.created_at).limit(100)).all()
        return ok([row.to_dict() for row in rows])

    @login_required
    def post(self, group_id, current_user):
        group = db.session.get(ChatGroup, group_id)
        if not group:
            return fail("group_not_found", "Group not found.", 404)
        if not db.session.scalar(select(GroupMember.id).where(GroupMember.group_id == group.id, GroupMember.user_id == current_user.id)):
            return fail("permission_denied", "Join the group before sending messages.", 403)
        text = str(json_body().get("body", "")).strip()
        if not text or len(text) > 2000:
            return fail("invalid_message", "Message must contain 1–2000 characters.", 400)
        message = Message(group_id=group.id, sender_id=current_user.id, body=text)
        db.session.add(message)
        db.session.commit()
        return ok(message.to_dict(), 201)


@ns.route("/chat/messages")
class DirectMessages(Resource):
    @login_required
    def get(self, current_user):
        recipient = request.args.get("with", "").strip()
        other = db.session.scalar(select(User).where(User.username == recipient)) if recipient else None
        if not other:
            return fail("recipient_not_found", "Choose a valid reader username.", 404)
        rows = db.session.scalars(select(Message).where(Message.group_id.is_(None), or_(and_(Message.sender_id == current_user.id, Message.recipient_id == other.id), and_(Message.sender_id == other.id, Message.recipient_id == current_user.id))).order_by(Message.created_at).limit(100)).all()
        return ok([row.to_dict() for row in rows])

    @login_required
    def post(self, current_user):
        data = json_body()
        username = str(data.get("to", "")).strip()
        recipient = db.session.scalar(select(User).where(User.username == username))
        text = str(data.get("body", data.get("content", ""))).strip()
        if not recipient:
            return fail("recipient_not_found", "Choose a valid reader username.", 404)
        if recipient.id == current_user.id or not text or len(text) > 2000:
            return fail("invalid_message", "Choose another reader and enter a message of up to 2000 characters.", 400)
        message = Message(sender_id=current_user.id, recipient_id=recipient.id, body=text)
        db.session.add(message)
        add_notification(recipient.id, "پیام تازه", f"{current_user.display_name} برای شما پیام فرستاد.")
        db.session.commit()
        return ok(message.to_dict(), 201)


@ns.route("/communities/top/discount-email")
class CommunityDiscountEmail(Resource):
    @login_required
    def post(self, current_user):
        return send_discount_to_top_users(current_user, json_body().get("code", ""))


def register_resources(api) -> None:
    api.add_namespace(ns)
