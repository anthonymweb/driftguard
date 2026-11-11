from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    name: str
    category: str
    description: str
    price_cents: int
    compare_at_cents: int | None
    stock: int
    featured: bool
    active: bool


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ProfileRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    phone: str
    role: str


class ProfileUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(default="", max_length=40)


class CartItemIn(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=20)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1, le=20)


class OrderCreate(BaseModel):
    shipping_name: str = Field(min_length=2, max_length=120)
    shipping_address: str = Field(min_length=5, max_length=300)


class OrderStatusUpdate(BaseModel):
    status: Literal["received", "processing", "shipped", "delivered", "cancelled"]


class ProductCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=2, max_length=180)
    category: str = Field(min_length=2, max_length=60)
    description: str = Field(min_length=10, max_length=2000)
    price_cents: int = Field(ge=1, le=5_000_000)
    compare_at_cents: int | None = Field(default=None, ge=1, le=5_000_000)
    stock: int = Field(default=0, ge=0, le=100_000)
    featured: bool = False
    active: bool = True


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int | None
    product_name: str
    unit_price_cents: int
    quantity: int


class OrderRead(BaseModel):
    id: int
    reference: str
    status: str
    total_cents: int
    shipping_name: str
    shipping_address: str
    payment_method: str
    created_at: datetime
    items: list[OrderItemRead]


class ProfileChange(BaseModel):
    profile: Literal["BASELINE", "TEST_CHANGE", "RESTORED"]
    note: str = Field(default="Research configuration change", min_length=3, max_length=300)


class ContactCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    subject: str = Field(min_length=3, max_length=140)
    message: str = Field(min_length=10, max_length=3000)
