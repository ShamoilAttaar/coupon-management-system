from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

class CouponType(str, Enum):
    CART_WISE = "cart-wise"
    PRODUCT_WISE = "product-wise"
    BXGY = "bxgy"

class ProductItem(BaseModel):
    product_id: int
    quantity: int
    price: float

class CartItem(BaseModel):
    product_id: int
    quantity: int
    price: float
    total_discount: float = 0.0

class CartWiseDetails(BaseModel):
    threshold: float = Field(..., gt=0, description="Minimum cart total required")
    discount: float = Field(..., ge=0, le=100, description="Discount percentage")
    max_discount_amount: Optional[float] = Field(None, gt=0, description="Maximum discount amount")

class ProductWiseDetails(BaseModel):
    product_id: int = Field(..., gt=0)
    discount: float = Field(..., ge=0, le=100)
    max_discount_amount: Optional[float] = Field(None, gt=0)
    min_quantity: int = Field(1, ge=1, description="Minimum quantity required")

class BxGyProduct(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)

class BxGyDetails(BaseModel):
    buy_products: List[BxGyProduct] = Field(..., min_items=1)
    get_products: List[BxGyProduct] = Field(..., min_items=1)
    repetition_limit: int = Field(..., gt=0, description="Maximum number of times this coupon can be applied")

class CouponCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: CouponType
    details: Union[CartWiseDetails, ProductWiseDetails, BxGyDetails]
    expires_at: Optional[datetime] = None

class CouponUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None

class CouponResponse(BaseModel):
    id: int
    name: str
    type: CouponType
    details: Dict[str, Any]
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True

class Cart(BaseModel):
    items: List[CartItem]

class ApplicableCoupon(BaseModel):
    coupon_id: int
    type: CouponType
    discount: float
    details: Dict[str, Any]

class ApplicableCouponsResponse(BaseModel):
    applicable_coupons: List[ApplicableCoupon]

class ApplyCouponRequest(BaseModel):
    cart: Cart

class ApplyCouponResponse(BaseModel):
    updated_cart: Cart
    total_price: float
    total_discount: float
    final_price: float
    applied_coupon: CouponResponse
