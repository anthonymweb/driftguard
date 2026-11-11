"""DemoCommerce store, customer API and researcher configuration controls."""
import hashlib
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from . import models
from .database import Base, engine, get_db, SessionLocal
from .middleware import SecurityProfileMiddleware
from .schemas import (
    CartItemIn, CartItemUpdate, LoginIn, OrderCreate, OrderRead, OrderStatusUpdate,
    ContactCreate, ProductCreate, ProductRead, ProfileChange, ProfileRead, ProfileUpdate, RegisterIn,
)
from .security import (
    SESSION_COOKIE, clear_session_cookie, current_profile, hash_password,
    new_session, profile_settings, set_session_cookie, verify_password,
)

CATALOGUE = [
    ("aero-wireless-headphones", "Aero Wireless Headphones", "Audio", "Rich, balanced sound with soft memory-foam cushions and 38 hours of listening time.", 12900, 15900, 24, True),
    ("arc-desk-lamp", "Arc Dimmable Desk Lamp", "Desk", "A sculpted aluminium lamp with warm dimming, touch controls and a weighted base.", 8400, None, 18, True),
    ("field-notes-weekender", "Field Notes Weekender", "Carry", "A durable recycled-canvas weekender with a clean profile and room for a short trip.", 11200, None, 15, True),
    ("everyday-ceramic-set", "Everyday Ceramic Set", "Home", "A four-piece stoneware set, finished by hand in a soft, speckled glaze.", 5800, 6900, 31, False),
    ("orbit-bluetooth-speaker", "Orbit Bluetooth Speaker", "Audio", "Room-filling portable sound, a tactile woven finish and an easy-carry loop.", 7600, None, 20, True),
    ("ridge-water-bottle", "Ridge Insulated Bottle", "Outdoor", "Double-wall stainless steel keeps drinks cold through the longest afternoon.", 3200, None, 42, False),
    ("form-wireless-charger", "Form Wireless Charger", "Desk", "A compact, softly textured charging stand designed to keep your workspace clear.", 4600, None, 27, False),
    ("weekend-knit-throw", "Weekend Knit Throw", "Home", "A lightweight cotton-blend throw with a relaxed weave and generous proportions.", 6900, 7900, 13, True),
]
PROFILE_NAMES = ("BASELINE", "TEST_CHANGE", "RESTORED")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        for row in CATALOGUE:
            slug, name, category, description, price, compare, stock, featured = row
            if not db.scalar(select(models.Product).where(models.Product.slug == slug)):
                db.add(models.Product(slug=slug, name=name, category=category, description=description,
                                      price_cents=price, compare_at_cents=compare, stock=stock, featured=featured))
        setting = db.get(models.AppSetting, "security_profile")
        if setting is None:
            db.add(models.AppSetting(key="security_profile", value={"profile": "BASELINE"}))
            db.commit()
            setting = db.get(models.AppSetting, "security_profile")
        else:
            db.commit()
        app.state.security_profile = setting.value.get("profile", "BASELINE")
    yield


app = FastAPI(title="DemoCommerce API", version="0.1.0", description="DemoCommerce controlled test store API", lifespan=lifespan)
app.add_middleware(SecurityProfileMiddleware)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> models.User:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Sign in to continue")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    session = db.scalar(select(models.SessionToken).where(models.SessionToken.token_hash == token_hash))
    expires_at = session.expires_at.replace(tzinfo=timezone.utc) if session and session.expires_at.tzinfo is None else (session.expires_at if session else None)
    if session is None or expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired. Sign in again")
    user = db.get(models.User, session.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Account is unavailable")
    return user


def require_admin(user: models.User = Depends(get_current_user)) -> models.User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user


def user_read(user: models.User) -> dict:
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "phone": user.phone, "role": user.role}


def cart_read(db: Session, user: models.User) -> dict:
    rows = db.scalars(select(models.CartItem).options(selectinload(models.CartItem.product)).where(models.CartItem.user_id == user.id)).all()
    items = [{
        "id": row.id, "product_id": row.product_id, "quantity": row.quantity,
        "product": ProductRead.model_validate(row.product).model_dump(),
        "line_total_cents": row.product.price_cents * row.quantity,
    } for row in rows if row.product and row.product.active]
    return {"items": items, "item_count": sum(row["quantity"] for row in items), "subtotal_cents": sum(row["line_total_cents"] for row in items)}


def order_query():
    return select(models.Order).options(selectinload(models.Order.items)).order_by(models.Order.created_at.desc())


@app.get("/health")
def health():
    return {"status": "ok", "service": "democommerce-api", "profile": app.state.security_profile}


@app.get("/api/internal/security-profile", include_in_schema=False)
def internal_security_profile():
    """Profile signal consumed by the private reverse-proxy auth subrequest."""
    return Response(status_code=204, headers={"X-Active-Profile": app.state.security_profile})


@app.get("/api/products", response_model=list[ProductRead], tags=["catalogue"])
def products(q: str | None = Query(default=None, max_length=100), category: str | None = Query(default=None, max_length=60), featured: bool | None = None, db: Session = Depends(get_db)):
    statement = select(models.Product).where(models.Product.active.is_(True))
    if q:
        term = f"%{q.strip()}%"
        statement = statement.where(or_(models.Product.name.ilike(term), models.Product.description.ilike(term), models.Product.category.ilike(term)))
    if category and category.lower() != "all":
        statement = statement.where(func.lower(models.Product.category) == category.lower())
    if featured is not None:
        statement = statement.where(models.Product.featured.is_(featured))
    return list(db.scalars(statement.order_by(models.Product.featured.desc(), models.Product.name)))


@app.get("/api/products/{slug}", response_model=ProductRead, tags=["catalogue"])
def product_detail(slug: str, db: Session = Depends(get_db)):
    product = db.scalar(select(models.Product).where(models.Product.slug == slug, models.Product.active.is_(True)))
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.post("/api/auth/register", response_model=ProfileRead, status_code=201, tags=["authentication"])
def register(payload: RegisterIn, response: Response, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    if db.scalar(select(models.User).where(models.User.email == email)):
        raise HTTPException(status_code=409, detail="An account with that email already exists")
    user = models.User(email=email, full_name=payload.full_name.strip(), password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()
    db.add(models.AuditEvent(actor_user_id=user.id, event="customer.registered", details={}))
    token = new_session(db, user)
    db.commit()
    db.refresh(user)
    set_session_cookie(response, token, current_profile_from_app())
    return user_read(user)


def current_profile_from_app() -> str:
    return app.state.security_profile


@app.post("/api/auth/login", response_model=ProfileRead, tags=["authentication"])
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    user = db.scalar(select(models.User).where(models.User.email == email))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    token = new_session(db, user)
    db.add(models.AuditEvent(actor_user_id=user.id, event="auth.login", details={"role": user.role}))
    db.commit()
    set_session_cookie(response, token, current_profile_from_app())
    return user_read(user)


@app.post("/api/auth/logout", tags=["authentication"])
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        session = db.scalar(select(models.SessionToken).where(models.SessionToken.token_hash == token_hash))
        if session:
            db.delete(session)
            db.commit()
    clear_session_cookie(response)
    return {"status": "signed_out"}


@app.get("/api/auth/me", response_model=ProfileRead, tags=["authentication"])
def get_profile(user: models.User = Depends(get_current_user)):
    return user_read(user)


@app.patch("/api/auth/me", response_model=ProfileRead, tags=["customer"])
def update_profile(payload: ProfileUpdate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    user.full_name = payload.full_name.strip()
    user.phone = payload.phone.strip()
    db.add(models.AuditEvent(actor_user_id=user.id, event="customer.profile_updated", details={}))
    db.commit()
    db.refresh(user)
    return user_read(user)


@app.get("/api/cart", tags=["cart"])
def get_cart(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return cart_read(db, user)


@app.post("/api/cart/items", tags=["cart"])
def add_cart_item(payload: CartItemIn, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    product = db.get(models.Product, payload.product_id)
    if product is None or not product.active:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.stock < payload.quantity:
        raise HTTPException(status_code=409, detail="Not enough stock available")
    item = db.scalar(select(models.CartItem).where(models.CartItem.user_id == user.id, models.CartItem.product_id == product.id))
    if item:
        if item.quantity + payload.quantity > min(product.stock, 20):
            raise HTTPException(status_code=409, detail="Requested quantity exceeds available stock")
        item.quantity += payload.quantity
    else:
        db.add(models.CartItem(user_id=user.id, product_id=product.id, quantity=payload.quantity))
    db.commit()
    return cart_read(db, user)


@app.patch("/api/cart/items/{item_id}", tags=["cart"])
def update_cart_item(item_id: int, payload: CartItemUpdate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    item = db.get(models.CartItem, item_id)
    if item is None or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Cart item not found")
    product = db.get(models.Product, item.product_id)
    if product is None or payload.quantity > min(product.stock, 20):
        raise HTTPException(status_code=409, detail="Requested quantity exceeds available stock")
    item.quantity = payload.quantity
    db.commit()
    return cart_read(db, user)


@app.delete("/api/cart/items/{item_id}", tags=["cart"])
def delete_cart_item(item_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    item = db.get(models.CartItem, item_id)
    if item is None or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Cart item not found")
    db.delete(item)
    db.commit()
    return cart_read(db, user)


@app.post("/api/orders", response_model=OrderRead, status_code=201, tags=["orders"])
def place_order(payload: OrderCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    cart_items = db.scalars(select(models.CartItem).options(selectinload(models.CartItem.product)).where(models.CartItem.user_id == user.id)).all()
    if not cart_items:
        raise HTTPException(status_code=400, detail="Your cart is empty")
    total = 0
    for item in cart_items:
        if not item.product or not item.product.active or item.product.stock < item.quantity:
            raise HTTPException(status_code=409, detail=f"{item.product.name if item.product else 'A product'} is no longer available in that quantity")
        total += item.product.price_cents * item.quantity
    order = models.Order(
        reference=f"DC-{secrets.token_hex(4).upper()}", user_id=user.id, total_cents=total,
        shipping_name=payload.shipping_name.strip(), shipping_address=payload.shipping_address.strip(),
        payment_method="simulated — no payment collected",
    )
    db.add(order)
    db.flush()
    for item in cart_items:
        product = item.product
        order.items.append(models.OrderItem(product_id=product.id, product_name=product.name,
                                            unit_price_cents=product.price_cents, quantity=item.quantity))
        product.stock -= item.quantity
        db.delete(item)
    db.add(models.AuditEvent(actor_user_id=user.id, event="order.placed", details={"reference": order.reference, "total_cents": total}))
    db.commit()
    db.refresh(order)
    return order


@app.get("/api/orders", response_model=list[OrderRead], tags=["orders"])
def customer_orders(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return list(db.scalars(order_query().where(models.Order.user_id == user.id)))


@app.get("/api/orders/{reference}", response_model=OrderRead, tags=["orders"])
def customer_order(reference: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    order = db.scalar(order_query().where(models.Order.reference == reference, models.Order.user_id == user.id))
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.post("/api/contact", status_code=201, tags=["customer"])
def create_contact_message(payload: ContactCreate, db: Session = Depends(get_db)):
    message = models.ContactMessage(name=payload.name.strip(), email=str(payload.email).lower(),
                                    subject=payload.subject.strip(), message=payload.message.strip())
    db.add(message)
    db.commit()
    return {"status": "received", "reference": f"MSG-{message.id:05d}"}


@app.get("/api/admin/products", response_model=list[ProductRead], tags=["administration"])
def admin_products(db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)):
    return list(db.scalars(select(models.Product).order_by(models.Product.name)))


@app.post("/api/admin/products", response_model=ProductRead, status_code=201, tags=["administration"])
def create_product(payload: ProductCreate, db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    if db.scalar(select(models.Product).where(models.Product.slug == payload.slug)):
        raise HTTPException(status_code=409, detail="Product slug already exists")
    product = models.Product(**payload.model_dump())
    db.add(product)
    db.flush()
    db.add(models.AuditEvent(actor_user_id=admin.id, event="admin.product_created", details={"product_id": product.id, "slug": product.slug}))
    db.commit()
    db.refresh(product)
    return product


@app.put("/api/admin/products/{product_id}", response_model=ProductRead, tags=["administration"])
def update_product(product_id: int, payload: ProductCreate, db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    product = db.get(models.Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    collision = db.scalar(select(models.Product).where(models.Product.slug == payload.slug, models.Product.id != product_id))
    if collision:
        raise HTTPException(status_code=409, detail="Product slug already exists")
    for key, value in payload.model_dump().items():
        setattr(product, key, value)
    db.add(models.AuditEvent(actor_user_id=admin.id, event="admin.product_updated", details={"product_id": product.id}))
    db.commit()
    db.refresh(product)
    return product


@app.delete("/api/admin/products/{product_id}", tags=["administration"])
def archive_product(product_id: int, db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    product = db.get(models.Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    product.active = False
    db.add(models.AuditEvent(actor_user_id=admin.id, event="admin.product_archived", details={"product_id": product.id}))
    db.commit()
    return {"status": "archived"}


@app.get("/api/admin/orders", tags=["administration"])
def admin_orders(db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)):
    orders = db.scalars(order_query()).all()
    return [{**OrderRead.model_validate(order).model_dump(mode="json"), "customer_email": order.user.email, "customer_name": order.user.full_name} for order in orders]


@app.patch("/api/admin/orders/{order_id}/status", tags=["administration"])
def update_order_status(order_id: int, payload: OrderStatusUpdate, db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    order = db.scalar(select(models.Order).options(selectinload(models.Order.items)).where(models.Order.id == order_id))
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = payload.status
    db.add(models.AuditEvent(actor_user_id=admin.id, event="admin.order_status_changed", details={"order_id": order.id, "status": order.status}))
    db.commit()
    db.refresh(order)
    return OrderRead.model_validate(order)


@app.get("/api/admin/customers", tags=["administration"])
def admin_customers(db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)):
    customers = db.scalars(select(models.User).where(models.User.role == "customer").order_by(models.User.created_at.desc())).all()
    return [{"id": row.id, "email": row.email, "full_name": row.full_name, "phone": row.phone,
             "created_at": row.created_at, "order_count": len(row.orders)} for row in customers]


@app.get("/api/admin/contact-messages", tags=["administration"])
def admin_contact_messages(db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)):
    messages = db.scalars(select(models.ContactMessage).order_by(models.ContactMessage.created_at.desc())).all()
    return [{"id": row.id, "name": row.name, "email": row.email, "subject": row.subject,
             "message": row.message, "status": row.status, "created_at": row.created_at} for row in messages]


@app.get("/api/admin/security-profile", tags=["research configuration"])
def get_security_profile(db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)):
    setting = db.get(models.AppSetting, "security_profile")
    history = db.scalars(select(models.ConfigAudit).order_by(models.ConfigAudit.changed_at.desc()).limit(30)).all()
    profile = setting.value.get("profile", "BASELINE") if setting else "BASELINE"
    config = profile_settings(profile)
    return {
        "profile": profile,
        "test_profiles_enabled": os.getenv("DEMO_TEST_PROFILES_ENABLED", "0").lower() in {"1", "true", "yes"},
        "effective": {"headers": config["headers"], "cors": "*" if config["cors_wildcard"] else config["cors"],
                      "cookie": {"secure": config["cookie_secure"], "httponly": config["cookie_httponly"], "samesite": config["cookie_samesite"]}},
        "history": [{"profile": row.profile, "note": row.note, "changed_at": row.changed_at, "admin_user_id": row.admin_user_id} for row in history],
    }


@app.post("/api/admin/security-profile", tags=["research configuration"])
def set_security_profile(payload: ProfileChange, request: Request, db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    client_host = request.client.host if request.client else ""
    loopback_clients = {"127.0.0.1", "::1", "localhost", "testclient"}
    trusted_proxies = {value.strip() for value in os.getenv("DEMO_TRUSTED_PROXY_IPS", "").split(",") if value.strip()}
    local_proxy_clients = {value.strip() for value in os.getenv("DEMO_LOCAL_PROXY_CLIENTS", "").split(",") if value.strip()}
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    via_local_proxy = client_host in trusted_proxies and forwarded_for in (loopback_clients | local_proxy_clients)
    if client_host not in loopback_clients and not via_local_proxy:
        raise HTTPException(status_code=403, detail="Research configuration controls are local-only")
    if payload.profile == "TEST_CHANGE" and os.getenv("DEMO_TEST_PROFILES_ENABLED", "0").lower() not in {"1", "true", "yes"}:
        raise HTTPException(status_code=403, detail="TEST_CHANGE profile is disabled by server configuration")
    setting = db.get(models.AppSetting, "security_profile")
    previous = setting.value.get("profile", "BASELINE") if setting else "BASELINE"
    if setting is None:
        setting = models.AppSetting(key="security_profile", value={"profile": payload.profile})
        db.add(setting)
    else:
        setting.value = {"profile": payload.profile}
    db.add(models.ConfigAudit(admin_user_id=admin.id, profile=payload.profile, note=payload.note))
    db.add(models.AuditEvent(actor_user_id=admin.id, event="admin.security_profile_changed", details={"from": previous, "to": payload.profile, "note": payload.note}))
    db.commit()
    request.app.state.security_profile = payload.profile
    return {"profile": payload.profile, "previous_profile": previous, "status": "applied"}


@app.get("/api/admin/audit", tags=["administration"])
def audit_log(db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)):
    events = db.scalars(select(models.AuditEvent).order_by(models.AuditEvent.created_at.desc()).limit(100)).all()
    return [{"id": row.id, "actor_user_id": row.actor_user_id, "event": row.event,
             "details": row.details, "created_at": row.created_at} for row in events]
