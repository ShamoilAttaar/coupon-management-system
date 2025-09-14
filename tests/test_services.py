import pytest
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock

from app.database import Base, Coupon
from app.models import Cart, CartItem, CouponType
from app.services import CartWiseProcessor, ProductWiseProcessor, BxGyProcessor, CouponService

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_coupon.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def sample_cart():
    return Cart(items=[
        CartItem(product_id=1, quantity=2, price=50.0),
        CartItem(product_id=2, quantity=1, price=30.0),
        CartItem(product_id=3, quantity=3, price=25.0)
    ])

@pytest.fixture
def cart_wise_coupon():
    coupon = Mock()
    coupon.is_active = True
    coupon.expires_at = None
    coupon.details = json.dumps({
        "threshold": 100.0,
        "discount_percentage": 10.0,
        "max_discount_amount": None
    })
    return coupon

@pytest.fixture
def product_wise_coupon():
    coupon = Mock()
    coupon.is_active = True
    coupon.expires_at = None
    coupon.details = json.dumps({
        "product_id": 1,
        "discount_percentage": 20.0,
        "max_discount_amount": None,
        "min_quantity": 1
    })
    return coupon

@pytest.fixture
def bxgy_coupon():
    coupon = Mock()
    coupon.is_active = True
    coupon.expires_at = None
    coupon.details = json.dumps({
        "buy_products": [
            {"product_id": 1, "quantity": 2},
            {"product_id": 2, "quantity": 1}
        ],
        "get_products": [
            {"product_id": 3, "quantity": 1}
        ],
        "repetition_limit": 2
    })
    return coupon

class TestCartWiseProcessor:
    def test_is_applicable_success(self, cart_wise_coupon, sample_cart):
        processor = CartWiseProcessor()
        # Cart total: 2*50 + 1*30 + 3*25 = 100 + 30 + 75 = 205
        assert processor.is_applicable(cart_wise_coupon, sample_cart) == True

    def test_is_applicable_below_threshold(self, cart_wise_coupon, sample_cart):
        processor = CartWiseProcessor()
        # Modify cart to have total below threshold
        small_cart = Cart(items=[
            CartItem(product_id=1, quantity=1, price=50.0)
        ])
        assert processor.is_applicable(cart_wise_coupon, small_cart) == False

    def test_calculate_discount(self, cart_wise_coupon, sample_cart):
        processor = CartWiseProcessor()
        # Cart total: 205, 10% discount = 20.5
        discount = processor.calculate_discount(cart_wise_coupon, sample_cart)
        assert discount == 20.5

    def test_calculate_discount_with_max_limit(self, sample_cart):
        coupon = Mock()
        coupon.is_active = True
        coupon.expires_at = None
        coupon.details = json.dumps({
            "threshold": 100.0,
            "discount_percentage": 20.0,
            "max_discount_amount": 15.0
        })
        
        processor = CartWiseProcessor()
        # Cart total: 205, 20% discount = 41, but max is 15
        discount = processor.calculate_discount(coupon, sample_cart)
        assert discount == 15.0

class TestProductWiseProcessor:
    def test_is_applicable_success(self, product_wise_coupon, sample_cart):
        processor = ProductWiseProcessor()
        # Product 1 exists in cart with quantity 2
        assert processor.is_applicable(product_wise_coupon, sample_cart) == True

    def test_is_applicable_product_not_in_cart(self, product_wise_coupon, sample_cart):
        processor = ProductWiseProcessor()
        # Modify coupon to target product not in cart
        coupon = Mock()
        coupon.is_active = True
        coupon.expires_at = None
        coupon.details = json.dumps({
            "product_id": 99,
            "discount_percentage": 20.0,
            "max_discount_amount": None,
            "min_quantity": 1
        })
        assert processor.is_applicable(coupon, sample_cart) == False

    def test_calculate_discount(self, product_wise_coupon, sample_cart):
        processor = ProductWiseProcessor()
        # Product 1: 2 * 50 = 100, 20% discount = 20
        discount = processor.calculate_discount(product_wise_coupon, sample_cart)
        assert discount == 20.0

class TestBxGyProcessor:
    def test_is_applicable_success(self, bxgy_coupon, sample_cart):
        processor = BxGyProcessor()
        # We have 2 of product 1 and 1 of product 2 (total 3), need 2+1=3
        # We have 3 of product 3 to give away
        assert processor.is_applicable(bxgy_coupon, sample_cart) == True

    def test_is_applicable_insufficient_buy_products(self, bxgy_coupon, sample_cart):
        processor = BxGyProcessor()
        # Modify cart to have insufficient buy products
        small_cart = Cart(items=[
            CartItem(product_id=1, quantity=1, price=50.0),  # Only 1, need 2
            CartItem(product_id=3, quantity=3, price=25.0)
        ])
        assert processor.is_applicable(bxgy_coupon, small_cart) == False

    def test_calculate_discount(self, bxgy_coupon, sample_cart):
        processor = BxGyProcessor()
        # Can apply coupon 1 time (3 buy products / 3 required = 1)
        # Get 1 product 3 free = 1 * 25 = 25
        discount = processor.calculate_discount(bxgy_coupon, sample_cart)
        assert discount == 25.0

    def test_apply_coupon(self, bxgy_coupon, sample_cart):
        processor = BxGyProcessor()
        updated_cart, discount = processor.apply_coupon(bxgy_coupon, sample_cart)
        
        # Check that product 3 has discount applied
        product_3_item = next(item for item in updated_cart.items if item.product_id == 3)
        assert product_3_item.total_discount == 25.0
        assert discount == 25.0

class TestCouponService:
    def test_get_applicable_coupons(self, db_session, sample_cart):
        # Create test coupons
        cart_wise_coupon = Coupon(
            name="Cart Discount",
            type="cart-wise",
            details=json.dumps({
                "threshold": 100.0,
                "discount_percentage": 10.0
            }),
            is_active=True
        )
        
        product_wise_coupon = Coupon(
            name="Product Discount",
            type="product-wise",
            details=json.dumps({
                "product_id": 1,
                "discount_percentage": 20.0,
                "min_quantity": 1
            }),
            is_active=True
        )
        
        db_session.add(cart_wise_coupon)
        db_session.add(product_wise_coupon)
        db_session.commit()
        
        service = CouponService()
        applicable_coupons = service.get_applicable_coupons(db_session, sample_cart)
        
        assert len(applicable_coupons) == 2
        assert applicable_coupons[0].coupon_id == cart_wise_coupon.id
        assert applicable_coupons[1].coupon_id == product_wise_coupon.id

    def test_apply_coupon_success(self, db_session, sample_cart):
        # Create test coupon
        coupon = Coupon(
            name="Test Coupon",
            type="product-wise",
            details=json.dumps({
                "product_id": 1,
                "discount_percentage": 20.0,
                "min_quantity": 1
            }),
            is_active=True
        )
        
        db_session.add(coupon)
        db_session.commit()
        
        service = CouponService()
        updated_cart, discount, applied_coupon = service.apply_coupon(
            db_session, coupon.id, sample_cart
        )
        
        assert discount == 20.0
        assert applied_coupon.id == coupon.id
        
        # Check that product 1 has discount applied
        product_1_item = next(item for item in updated_cart.items if item.product_id == 1)
        assert product_1_item.total_discount == 20.0

    def test_apply_coupon_not_found(self, db_session, sample_cart):
        service = CouponService()
        
        with pytest.raises(ValueError, match="Coupon with ID 999 not found"):
            service.apply_coupon(db_session, 999, sample_cart)

    def test_apply_coupon_not_applicable(self, db_session, sample_cart):
        # Create coupon that won't be applicable
        coupon = Coupon(
            name="High Threshold Coupon",
            type="cart-wise",
            details=json.dumps({
                "threshold": 1000.0,  # Very high threshold
                "discount_percentage": 10.0
            }),
            is_active=True
        )
        
        db_session.add(coupon)
        db_session.commit()
        
        service = CouponService()
        
        with pytest.raises(ValueError, match="Coupon .* is not applicable"):
            service.apply_coupon(db_session, coupon.id, sample_cart)
