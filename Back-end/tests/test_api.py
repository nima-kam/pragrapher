from __future__ import annotations

from io import BytesIO

from PIL import Image
from sqlalchemy import func, select

from extensions import db
from models import (
    Book,
    Community,
    CommunityMember,
    EmailOutbox,
    GroupMember,
    Message,
    Notification,
    Quote,
    User,
)
from seed import seed_demo_data
from tests.helpers import DEMO_PASSWORD, request, seed, sign_in


def payload(response):
    data = response.get_json()
    assert data is not None, response.data
    return data.get("data", data)


def test_health_docs_migration_and_repeatable_seed(client, app):
    assert client.get("/health").get_json()["status"] == "ok"
    assert client.get("/docs").status_code == 200
    with app.app_context():
        seed_demo_data()
        seed_demo_data()
        assert db.session.scalar(select(func.count(User.id))) == 4
        assert db.session.scalar(select(func.count(Community.id))) == 3
        assert db.session.scalar(select(func.count(Quote.id))) == 7
        assert db.session.scalar(select(func.count(Book.id))) == 3

    daily = payload(client.get("/api/v1/quotes/daily"))
    popular = payload(client.get("/api/v1/quotes/popular?per_page=8"))
    assert daily["quote"]["text"]
    assert len(popular["items"]) >= 4


def test_auth_csrf_registration_login_profile_password_and_logout(client):
    missing_csrf = client.post("/api/v1/auth/register", json={
        "username": "new_reader",
        "email": "new@example.test",
        "password": "A-long-test-password!",
    })
    assert missing_csrf.status_code == 403

    bad = request(client, "post", "/api/v1/auth/register", {
        "username": "x",
        "email": "not-an-email",
        "password": "short",
    })
    assert bad.status_code == 400

    created = request(client, "post", "/api/v1/auth/register", {
        "username": "new_reader",
        "email": "new@example.test",
        "display_name": "خواننده‌ی تازه",
        "password": "A-long-test-password!",
    })
    assert created.status_code == 201
    assert payload(client.get("/api/v1/auth/me"))["username"] == "new_reader"

    changed = request(client, "patch", "/api/v1/me", {
        "display_name": "خواننده‌ی کتاب‌دوست",
        "bio": "دوستدار قصه‌ها",
    })
    assert payload(changed)["display_name"] == "خواننده‌ی کتاب‌دوست"
    assert request(client, "post", "/api/v1/me/password", {
        "old_password": "A-long-test-password!",
        "new_password": "A-different-long-password!",
    }).status_code == 200
    assert request(client, "post", "/api/v1/auth/logout", {}).status_code == 200
    assert request(client, "get", "/api/v1/auth/me").status_code == 401
    assert request(client, "post", "/api/v1/auth/login", {
        "username": "new_reader",
        "password": "A-different-long-password!",
    }).status_code == 200

    assert request(client, "post", "/api/v1/auth/login", {
        "username": "new_reader",
        "password": "incorrect password",
    }).status_code == 401


def test_community_membership_privacy_likes_categories_and_invites(client):
    seed(client)
    sign_in(client)

    listed = payload(client.get("/api/v1/communities?per_page=50"))
    assert len(listed["items"]) == 3
    top = payload(client.get("/api/v1/communities/top"))
    assert top
    community = next(item for item in listed["items"] if item["slug"] == "poetry-corner")

    assert request(client, "delete", "/api/v1/communities/poetry-corner/join").status_code == 200
    assert request(client, "post", "/api/v1/communities/poetry-corner/join", {}).status_code == 200
    assert request(client, "put", "/api/v1/communities/poetry-corner/likes/me", {}).status_code == 200
    assert request(client, "delete", "/api/v1/communities/poetry-corner/likes/me").status_code == 200
    assert request(client, "post", "/api/v1/communities/poetry-corner/categories", {"name": "خوانش دوباره"}).status_code == 403
    categories = payload(client.get("/api/v1/communities/poetry-corner/categories"))
    assert categories
    assert request(client, "patch", "/api/v1/communities/poetry-corner/members/me", {"subscribed": False}).status_code == 200
    assert payload(client.get("/api/v1/communities/poetry-corner/members"))

    private = payload(request(client, "post", "/api/v1/communities", {
        "name": "باشگاه خصوصی کتاب",
        "description": "گفت‌وگوی اعضا",
        "is_private": True,
    }))
    assert request(client, "post", f"/api/v1/communities/{private['slug']}/categories", {"name": "خوانش دوباره"}).status_code == 201
    assert any(item["name"] == "خوانش دوباره" for item in payload(client.get(f"/api/v1/communities/{private['slug']}/categories")))
    guest = client.application.test_client()
    request(guest, "post", "/api/v1/auth/register", {
        "username": "guest_reader",
        "email": "guest@example.test",
        "password": "Guest-reader-password!",
    })
    assert guest.get(f"/api/v1/communities/{private['slug']}").status_code == 403
    assert request(client, "post", f"/api/v1/communities/{private['slug']}/members", {"username": "guest_reader"}).status_code == 201
    sign_in(guest, "guest_reader", "Guest-reader-password!")
    assert guest.get(f"/api/v1/communities/{private['slug']}").status_code == 200
    assert community["is_member"] is True

    invalid = request(client, "post", "/api/v1/communities", {"name": ""})
    assert invalid.status_code == 400


def test_quotes_replies_likes_search_and_authorization(client):
    seed(client)
    sign_in(client)

    quote_response = request(client, "post", "/api/v1/communities/fantasy-shelf/quotes", {
        "text": "هر پایان، پنجره‌ای برای آغاز دیگری است.",
        "reference": "کتابِ آزمون",
        "character": "رها",
        "tags": ["امید", "پایان"],
    })
    assert quote_response.status_code == 201
    quote = payload(quote_response)
    assert request(client, "put", f"/api/v1/quotes/{quote['id']}/likes/me", {}).status_code == 200
    assert request(client, "put", f"/api/v1/quotes/{quote['id']}/likes/me", {}).status_code == 200
    reply = request(client, "post", f"/api/v1/quotes/{quote['id']}/replies", {"text": "چه جمله‌ی امیدوارکننده‌ای."})
    assert reply.status_code == 201
    replies = payload(client.get(f"/api/v1/quotes/{quote['id']}/replies"))
    assert len(replies) == 1
    assert payload(client.get(f"/api/v1/quotes?community=fantasy-shelf"))["items"]
    assert payload(client.get("/api/v1/search?q=فانوس"))["quotes"]
    assert payload(client.get("/api/v1/search/suggestions?q=چراغ"))

    stranger = client.application.test_client()
    sign_in(stranger, "sara_books")
    forbidden = request(stranger, "patch", f"/api/v1/quotes/{quote['id']}", {"text": "تغییر غیرمجاز"})
    assert forbidden.status_code == 403
    updated = request(client, "patch", f"/api/v1/quotes/{quote['id']}", {"text": "متن ویرایش‌شده‌ی مالک"})
    assert payload(updated)["text"] == "متن ویرایش‌شده‌ی مالک"
    assert request(client, "delete", f"/api/v1/quotes/{quote['id']}").status_code == 200


def test_books_upload_credits_purchase_discounts_and_loans(client):
    seed(client)
    sign_in(client)

    books = payload(client.get("/api/v1/books?per_page=20"))["items"]
    own_book = next(book for book in books if book["title"] == "نقشه‌ی فانوس‌ها")
    stranger_book = next(book for book in books if book["title"] == "باغِ واژه‌ها")
    assert request(client, "post", f"/api/v1/books/{own_book['id']}/reserve", {}).status_code == 400

    image = BytesIO()
    Image.new("RGB", (8, 8), color="green").save(image, format="PNG")
    image.seek(0)
    uploaded = request(client, "post", f"/api/v1/books/{own_book['id']}/image", data={
        "file": (image, "cover.png"),
    })
    assert uploaded.status_code == 200
    assert payload(uploaded)["image_url"].startswith("/api/v1/uploads/")
    bad_upload = request(client, "post", f"/api/v1/books/{own_book['id']}/image", data={
        "file": (BytesIO(b"not an image"), "bad.png"),
    })
    assert bad_upload.status_code == 400

    assert payload(request(client, "post", "/api/v1/credits/demo", {"amount": 50}))["credit_balance"] == 550
    reserved = request(client, "post", f"/api/v1/books/{stranger_book['id']}/reserve", {})
    assert payload(reserved)["status"] == "reserved"
    visible_reservation = payload(client.get("/api/v1/books?per_page=20"))["items"]
    assert any(item["id"] == stranger_book["id"] and item["status"] == "reserved" for item in visible_reservation)
    purchase = request(client, "post", f"/api/v1/books/{stranger_book['id']}/purchase", {"discount_code": "KETAB10"})
    assert purchase.status_code == 200
    assert payload(purchase)["book"]["status"] == "sold"
    assert request(client, "get", f"/api/v1/discounts/KETAB10?price=100").status_code == 200

    new_book = request(client, "post", "/api/v1/books", {
        "title": "کتاب قرضی",
        "author": "نویسنده",
        "community_slug": "fantasy-shelf",
        "price": 0,
    })
    assert new_book.status_code == 201
    loan = request(client, "post", "/api/v1/loans", {"book_id": payload(new_book)["id"]})
    assert loan.status_code == 400

    seller = client.application.test_client()
    sign_in(seller, "sara_books")
    loan_book = request(seller, "post", "/api/v1/books", {
        "title": "کتاب برای امانت",
        "author": "نویسنده‌ی مهمان",
        "community_slug": "poetry-corner",
        "price": 0,
    })
    assert loan_book.status_code == 201
    loan = request(client, "post", "/api/v1/loans", {"book_id": payload(loan_book)["id"]})
    assert loan.status_code == 201
    approved = request(seller, "patch", f"/api/v1/loans/{payload(loan)['id']}", {"status": "approved"})
    assert approved.status_code == 200
    assert payload(client.get("/api/v1/borrowed-books"))
    assert request(client, "patch", f"/api/v1/loans/{payload(loan)['id']}", {"status": "returned"}).status_code == 200

    admin = client.application.test_client()
    sign_in(admin, "admin")
    discount = request(admin, "post", "/api/v1/discounts", {"code": "SPRING25", "percent": 25})
    assert discount.status_code == 201
    assert request(client, "post", "/api/v1/discounts", {"code": "READER10", "percent": 10}).status_code == 403
    announcement = request(admin, "post", "/api/v1/discounts/email-top-users", {"code": "SPRING25"})
    assert payload(announcement)["queued"] == 3
    with client.application.app_context():
        assert db.session.scalar(select(func.count(EmailOutbox.id))) == 3


def test_groups_direct_chat_notifications_public_profile_and_loans(client):
    seed(client)
    user = sign_in(client)

    groups = payload(client.get("/api/v1/groups"))
    assert groups
    group = groups[0]
    assert request(client, "post", f"/api/v1/groups/{group['id']}/join", {}).status_code == 200
    assert payload(request(client, "get", f"/api/v1/groups/{group['id']}"))["members"]
    sent = request(client, "post", f"/api/v1/groups/{group['id']}/messages", {"body": "سلام گروه"})
    assert sent.status_code == 201
    assert any(item["body"] == "سلام گروه" for item in payload(client.get(f"/api/v1/groups/{group['id']}/messages")))
    assert request(client, "post", "/api/v1/groups", {"name": "خوانش هفتگی", "community_slug": "fantasy-shelf"}).status_code == 201

    direct = request(client, "post", "/api/v1/chat/messages", {"to": "sara_books", "body": "سلام سارا"})
    assert direct.status_code == 201
    assert payload(client.get("/api/v1/chat/messages?with=sara_books"))
    assert payload(client.get("/api/v1/users/sara_books"))["username"] == "sara_books"

    notifications = payload(client.get("/api/v1/notifications"))
    assert notifications
    notification_id = notifications[0]["id"]
    assert request(client, "put", f"/api/v1/notifications/{notification_id}/read", {}).status_code == 200
    assert request(client, "delete", "/api/v1/notifications").status_code == 200
    assert payload(client.get("/api/v1/me/quotes")) is not None
    assert payload(client.get("/api/v1/me/books")) is not None
    assert payload(client.get("/api/v1/me/credit-transactions")) is not None
    assert user["username"] == "nima_reader"
