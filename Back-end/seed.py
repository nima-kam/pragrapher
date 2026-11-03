"""Repeatable, local-only demo content for screenshots and development."""

from __future__ import annotations

import click
from flask import current_app
from sqlalchemy import select
from werkzeug.security import generate_password_hash

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
    GroupMember,
    Loan,
    Message,
    Notification,
    Quote,
    QuoteLike,
    User,
    utcnow,
)

DEMO_PASSWORD = "ParagrapherDemo123!"


def seed_demo_data() -> None:
    if current_app.config["ENVIRONMENT"] == "production":
        raise RuntimeError("Demo seed data must never be added to production.")

    users = {}
    for username, email, display_name, is_admin in (
        ("admin", "admin@example.test", "مدیر کتابخانه", True),
        ("nima_reader", "nima@example.test", "نیما", False),
        ("sara_books", "sara@example.test", "سارا", False),
        ("arman_quotes", "arman@example.test", "آرمان", False),
    ):
        user = db.session.scalar(select(User).where(User.username == username))
        if user is None:
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(DEMO_PASSWORD),
                display_name=display_name,
                bio="دوستدار کتاب و گفت‌وگو درباره‌ی داستان‌ها.",
                credit_balance=500,
                is_admin=is_admin,
            )
            db.session.add(user)
            db.session.flush()
        users[username] = user

    community_data = (
        ("fantasy-shelf", "قفسه‌ی خیال", "برای گفت‌وگو درباره‌ی جهان‌های خیالی و قهرمانانشان.", users["nima_reader"]),
        ("poetry-corner", "گوشه‌ی شعر", "شعرهایی که دوست داریم با هم بخوانیم و درباره‌شان حرف بزنیم.", users["sara_books"]),
        ("mystery-circle", "حلقه‌ی معما", "سرنخ‌ها، شخصیت‌ها و پایان‌های غافلگیرکننده.", users["arman_quotes"]),
    )
    communities = {}
    for slug, name, description, owner in community_data:
        community = db.session.scalar(select(Community).where(Community.slug == slug))
        if community is None:
            community = Community(slug=slug, name=name, description=description, owner_id=owner.id)
            db.session.add(community)
            db.session.flush()
        communities[slug] = community
        for username in ("admin", "nima_reader", "sara_books", "arman_quotes"):
            existing = db.session.scalar(select(CommunityMember).where(
                CommunityMember.community_id == community.id,
                CommunityMember.user_id == users[username].id,
            ))
            if not existing:
                db.session.add(CommunityMember(
                    community_id=community.id,
                    user_id=users[username].id,
                    role="owner" if users[username].id == owner.id else "member",
                ))

    db.session.flush()
    category_items = (
        ("fantasy-shelf", "جهان‌سازی", "جزئیات جهان‌های داستانی"),
        ("fantasy-shelf", "شخصیت‌ها", "مسیر و انتخاب‌های شخصیت‌ها"),
        ("poetry-corner", "تصویرها", "تصویرهای شاعرانه و استعاره‌ها"),
        ("mystery-circle", "سرنخ‌ها", "سرنخ‌هایی که نباید از دست داد"),
    )
    for slug, name, description in category_items:
        community = communities[slug]
        if not db.session.scalar(select(Category.id).where(Category.community_id == community.id, Category.name == name)):
            db.session.add(Category(community_id=community.id, name=name, description=description))

    quote_data = (
        ("fantasy-shelf", "گاهی شجاعت یعنی چراغ کوچکی را روشن نگه داری، حتی وقتی راه هنوز پیدا نیست.", "نقشه‌ی فانوس‌ها", "رها", "nima_reader", ["شجاعت", "سفر"]),
        ("fantasy-shelf", "هیچ دری قفل نبود؛ ما فقط یادمان رفته بود از هم سؤال کنیم.", "شهرِ پشتِ مه", "آوید", "sara_books", ["دوستی", "راز"]),
        ("poetry-corner", "باران که می‌آید، پنجره هم چیزی برای گفتن پیدا می‌کند.", "دفترِ روزهای روشن", "مینا", "sara_books", ["باران", "خانه"]),
        ("poetry-corner", "راه دور نمی‌شود اگر هر قدم را با نامی مهربان صدا بزنی.", "باغِ واژه‌ها", "سام", "arman_quotes", ["راه", "امید"]),
        ("mystery-circle", "سرنخ‌ها گاهی در سکوت آدم‌هایی پنهان‌اند که عجله‌ای برای پاسخ ندارند.", "اتاقِ ساعت خاموش", "نیلو", "nima_reader", ["معما", "سکوت"]),
        ("mystery-circle", "وقتی همه به یک پنجره نگاه می‌کردند، کلید پشت در مانده بود.", "آخرین چراغِ ایستگاه", "کاوه", "arman_quotes", ["سرنخ", "کلید"]),
    )
    quotes = {}
    for slug, text, reference, character, username, tags in quote_data:
        community = communities[slug]
        quote = db.session.scalar(select(Quote).where(
            Quote.community_id == community.id,
            Quote.user_id == users[username].id,
            Quote.text == text,
        ))
        if quote is None:
            quote = Quote(
                community_id=community.id,
                user_id=users[username].id,
                text=text,
                reference=reference,
                character=character,
                tags=tags,
            )
            db.session.add(quote)
            db.session.flush()
        quotes[text] = quote

    quote_items = list(quotes.values())
    for quote, username in zip(quote_items, ("sara_books", "arman_quotes", "nima_reader", "nima_reader")):
        if quote.user_id != users[username].id and not db.session.get(QuoteLike, (users[username].id, quote.id)):
            db.session.add(QuoteLike(user_id=users[username].id, quote_id=quote.id))

    reply_text = "این جمله را برای روزهایی نگه می‌دارم که شروع دوباره سخت به نظر می‌رسد."
    parent = quote_items[0]
    if not db.session.scalar(select(Quote.id).where(Quote.parent_id == parent.id, Quote.text == reply_text)):
        db.session.add(Quote(
            community_id=parent.community_id,
            user_id=users["sara_books"].id,
            parent_id=parent.id,
            text=reply_text,
            reference=parent.reference,
            tags=[],
        ))

    book_items = (
        ("fantasy-shelf", "نقشه‌ی فانوس‌ها", "مهتاب راد", "داستانی", 80, "یک داستان خیال‌انگیز درباره‌ی سفر و پیدا کردن راه خانه.", "nima_reader"),
        ("poetry-corner", "باغِ واژه‌ها", "هومن سپید", "شعر", 60, "مجموعه‌ای از شعرهای کوتاه و تازه برای خواندن در عصرهای آرام.", "sara_books"),
        ("mystery-circle", "اتاقِ ساعت خاموش", "آوا نیک‌پی", "معمایی", 120, "معمایی دوستانه با سرنخ‌هایی برای خواندن دوباره.", "arman_quotes"),
    )
    books = {}
    for slug, title, author, genre, price, description, seller_name in book_items:
        book = db.session.scalar(select(Book).where(Book.title == title, Book.seller_id == users[seller_name].id))
        if book is None:
            book = Book(
                community_id=communities[slug].id,
                seller_id=users[seller_name].id,
                title=title,
                author=author,
                genre=genre,
                price=price,
                description=description,
            )
            db.session.add(book)
            db.session.flush()
        books[title] = book

    discount = db.session.get(Discount, "KETAB10")
    if discount is None:
        db.session.add(Discount(code="KETAB10", percent=10, created_by_id=users["admin"].id))

    group = db.session.scalar(select(ChatGroup).where(ChatGroup.name == "خوانندگان قفسه‌ی خیال"))
    if group is None:
        group = ChatGroup(name="خوانندگان قفسه‌ی خیال", community_id=communities["fantasy-shelf"].id, owner_id=users["nima_reader"].id)
        db.session.add(group)
        db.session.flush()
    for username in ("nima_reader", "sara_books", "arman_quotes"):
        if not db.session.scalar(select(GroupMember.id).where(GroupMember.group_id == group.id, GroupMember.user_id == users[username].id)):
            db.session.add(GroupMember(group_id=group.id, user_id=users[username].id))
    message_text = "این هفته کدام کتاب را با هم شروع کنیم؟"
    if not db.session.scalar(select(Message.id).where(Message.group_id == group.id, Message.body == message_text)):
        db.session.add(Message(group_id=group.id, sender_id=users["nima_reader"].id, body=message_text))

    loan_book = books["اتاقِ ساعت خاموش"]
    if not db.session.scalar(select(Loan.id).where(Loan.book_id == loan_book.id, Loan.borrower_id == users["sara_books"].id)):
        db.session.add(Loan(book_id=loan_book.id, borrower_id=users["sara_books"].id, lender_id=users["arman_quotes"].id, status="approved"))

    community = communities["fantasy-shelf"]
    if not db.session.get(CommunityLike, (users["sara_books"].id, community.id)):
        db.session.add(CommunityLike(user_id=users["sara_books"].id, community_id=community.id))
    if not db.session.scalar(select(Notification.id).where(Notification.user_id == users["nima_reader"].id, Notification.title == "کتاب هفته")):
        db.session.add(Notification(user_id=users["nima_reader"].id, title="کتاب هفته", body="جامعه‌ی قفسه‌ی خیال برای گفت‌وگوی این هفته آماده است."))
    if not db.session.scalar(select(CreditTransaction.id).where(CreditTransaction.user_id == users["nima_reader"].id, CreditTransaction.kind == "demo_seed")):
        db.session.add(CreditTransaction(user_id=users["nima_reader"].id, amount=500, kind="demo_seed", note="Starting local demo balance"))

    db.session.commit()


def register_cli(app) -> None:
    @app.cli.command("seed-demo")
    def seed_demo_command():
        """Add repeatable local sample users, communities, quotes, books, and messages."""
        seed_demo_data()
        click.echo("Paragrapher demo data is ready. Local demo password: " + DEMO_PASSWORD)
