from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
from sqlalchemy.orm import Session
from .models import (
    CouponType, CartItem, Cart, ApplicableCoupon, 
    CartWiseDetails, ProductWiseDetails, BxGyDetails,
    BxGyProduct
)
from .database import Coupon

class CouponProcessor(ABC):
    """Abstract base class for coupon processors"""
    
    def _is_expired(self, coupon: Coupon) -> bool:
        """Check if coupon is expired"""
        if not coupon.expires_at:
            return False
        return datetime.utcnow() > coupon.expires_at
    
    @abstractmethod
    def is_applicable(self, coupon: Coupon, cart: Cart) -> bool:
        """Check if coupon is applicable to the cart"""
        pass
    
    @abstractmethod
    def calculate_discount(self, coupon: Coupon, cart: Cart) -> float:
        """Calculate discount amount for the coupon"""
        pass
    
    @abstractmethod
    def apply_coupon(self, coupon: Coupon, cart: Cart) -> Tuple[Cart, float]:
        """Apply coupon to cart and return updated cart with discount"""
        pass

class CartWiseProcessor(CouponProcessor):
    """Processor for cart-wise coupons"""
    
    def is_applicable(self, coupon: Coupon, cart: Cart) -> bool:
        if not coupon.is_active or self._is_expired(coupon):
            return False
            
        details = json.loads(coupon.details)
        cart_total = sum(item.price * item.quantity for item in cart.items)
        
        return cart_total >= details['threshold']
    
    def calculate_discount(self, coupon: Coupon, cart: Cart) -> float:
        if not self.is_applicable(coupon, cart):
            return 0.0
            
        details = json.loads(coupon.details)
        cart_total = sum(item.price * item.quantity for item in cart.items)
        
        discount_value = details.get('discount', details.get('discount_percentage', 0))
        discount = (cart_total * discount_value) / 100
        
        # Apply maximum discount limit if specified
        if details.get('max_discount_amount'):
            discount = min(discount, details['max_discount_amount'])
            
        return round(discount, 2)
    
    def apply_coupon(self, coupon: Coupon, cart: Cart) -> Tuple[Cart, float]:
        discount = self.calculate_discount(coupon, cart)
        
        # For cart-wise coupons, distribute the discount proportionally across items
        updated_items = []
        cart_total = sum(item.price * item.quantity for item in cart.items)
        
        for item in cart.items:
            item_total = item.price * item.quantity
            # Calculate proportional discount for this item
            item_discount = (item_total / cart_total) * discount if cart_total > 0 else 0
            
            new_item = CartItem(
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.price,
                total_discount=round(item_discount, 2)
            )
            updated_items.append(new_item)
        
        updated_cart = Cart(items=updated_items)
        return updated_cart, discount

class ProductWiseProcessor(CouponProcessor):
    """Processor for product-wise coupons"""
    
    def is_applicable(self, coupon: Coupon, cart: Cart) -> bool:
        if not coupon.is_active or self._is_expired(coupon):
            return False
            
        details = json.loads(coupon.details)
        target_product_id = details['product_id']
        min_quantity = details.get('min_quantity', 1)
        
        # Check if target product exists in cart with sufficient quantity
        for item in cart.items:
            if item.product_id == target_product_id and item.quantity >= min_quantity:
                return True
                
        return False
    
    def calculate_discount(self, coupon: Coupon, cart: Cart) -> float:
        if not self.is_applicable(coupon, cart):
            return 0.0
            
        details = json.loads(coupon.details)
        target_product_id = details['product_id']
        
        # Find the target product in cart
        for item in cart.items:
            if item.product_id == target_product_id:
                item_total = item.price * item.quantity
                discount_value = details.get('discount', details.get('discount_percentage', 0))
                discount = (item_total * discount_value) / 100
                
                # Apply maximum discount limit if specified
                if details.get('max_discount_amount'):
                    discount = min(discount, details['max_discount_amount'])
                    
                return round(discount, 2)
                
        return 0.0
    
    def apply_coupon(self, coupon: Coupon, cart: Cart) -> Tuple[Cart, float]:
        discount = self.calculate_discount(coupon, cart)
        
        # Create updated cart with discount applied to the specific product
        updated_items = []
        for item in cart.items:
            new_item = CartItem(
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.price,
                total_discount=0.0
            )
            
            # Apply discount to the target product
            details = json.loads(coupon.details)
            if item.product_id == details['product_id']:
                new_item.total_discount = discount
                
            updated_items.append(new_item)
        
        updated_cart = Cart(items=updated_items)
        return updated_cart, discount

class BxGyProcessor(CouponProcessor):
    """Processor for Buy X Get Y coupons"""
    
    def is_applicable(self, coupon: Coupon, cart: Cart) -> bool:
        if not coupon.is_active or self._is_expired(coupon):
            return False
            
        details = json.loads(coupon.details)
        buy_products = details['buy_products']
        get_products = details['get_products']
        
        # Check if we have enough products from buy_products
        total_buy_quantity = 0
        for buy_product in buy_products:
            for item in cart.items:
                if item.product_id == buy_product['product_id']:
                    total_buy_quantity += item.quantity
                    break
        
        # Check if we have any products from get_products
        has_get_products = any(
            any(item.product_id == get_product['product_id'] for item in cart.items)
            for get_product in get_products
        )
        
        # Calculate how many times the coupon can be applied
        required_buy_quantity = sum(bp['quantity'] for bp in buy_products)
        max_applications = total_buy_quantity // required_buy_quantity
        repetition_limit = details.get('repetition_limit', 1)
        
        return max_applications > 0 and has_get_products and max_applications <= repetition_limit
    
    def calculate_discount(self, coupon: Coupon, cart: Cart) -> float:
        if not self.is_applicable(coupon, cart):
            return 0.0
            
        details = json.loads(coupon.details)
        buy_products = details['buy_products']
        get_products = details['get_products']
        repetition_limit = details.get('repetition_limit', 1)
        
        # Calculate total buy quantity
        total_buy_quantity = 0
        for buy_product in buy_products:
            for item in cart.items:
                if item.product_id == buy_product['product_id']:
                    total_buy_quantity += item.quantity
                    break
        
        # Calculate how many times the coupon can be applied
        required_buy_quantity = sum(bp['quantity'] for bp in buy_products)
        max_applications = min(
            total_buy_quantity // required_buy_quantity,
            repetition_limit
        )
        
        # Calculate discount based on free products
        total_discount = 0.0
        for get_product in get_products:
            for item in cart.items:
                if item.product_id == get_product['product_id']:
                    # Calculate how many of this product can be made free
                    free_quantity = min(
                        item.quantity,
                        get_product['quantity'] * max_applications
                    )
                    total_discount += free_quantity * item.price
                    break
        
        return round(total_discount, 2)
    
    def apply_coupon(self, coupon: Coupon, cart: Cart) -> Tuple[Cart, float]:
        discount = self.calculate_discount(coupon, cart)
        
        details = json.loads(coupon.details)
        buy_products = details['buy_products']
        get_products = details['get_products']
        repetition_limit = details.get('repetition_limit', 1)
        
        # Calculate how many times the coupon can be applied
        total_buy_quantity = 0
        for buy_product in buy_products:
            for item in cart.items:
                if item.product_id == buy_product['product_id']:
                    total_buy_quantity += item.quantity
                    break
        
        required_buy_quantity = sum(bp['quantity'] for bp in buy_products)
        max_applications = min(
            total_buy_quantity // required_buy_quantity,
            repetition_limit
        )
        
        # Create updated cart
        updated_items = []
        for item in cart.items:
            new_item = CartItem(
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.price,
                total_discount=0.0
            )
            
            # Check if this is a "get" product that should be free
            for get_product in get_products:
                if item.product_id == get_product['product_id']:
                    free_quantity = min(
                        item.quantity,
                        get_product['quantity'] * max_applications
                    )
                    new_item.total_discount = free_quantity * item.price
                    break
            
            updated_items.append(new_item)
        
        updated_cart = Cart(items=updated_items)
        return updated_cart, discount

class CouponService:
    """Service class for coupon operations"""
    
    def __init__(self):
        self.processors = {
            CouponType.CART_WISE: CartWiseProcessor(),
            CouponType.PRODUCT_WISE: ProductWiseProcessor(),
            CouponType.BXGY: BxGyProcessor()
        }
    
    def get_processor(self, coupon_type: CouponType) -> CouponProcessor:
        """Get the appropriate processor for coupon type"""
        return self.processors.get(coupon_type)
    
    def get_applicable_coupons(self, db: Session, cart: Cart) -> List[ApplicableCoupon]:
        """Get all applicable coupons for a cart"""
        coupons = db.query(Coupon).filter(Coupon.is_active == True).all()
        applicable_coupons = []
        
        for coupon in coupons:
            processor = self.get_processor(CouponType(coupon.type))
            if processor and processor.is_applicable(coupon, cart):
                discount = processor.calculate_discount(coupon, cart)
                if discount > 0:
                    applicable_coupons.append(ApplicableCoupon(
                        coupon_id=coupon.id,
                        type=CouponType(coupon.type),
                        discount=discount,
                        details=json.loads(coupon.details)
                    ))
        
        return applicable_coupons
    
    def apply_coupon(self, db: Session, coupon_id: int, cart: Cart) -> Tuple[Cart, float, Coupon]:
        """Apply a specific coupon to the cart"""
        coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
        if not coupon:
            raise ValueError(f"Coupon with ID {coupon_id} not found")
        
        processor = self.get_processor(CouponType(coupon.type))
        if not processor:
            raise ValueError(f"Unsupported coupon type: {coupon.type}")
        
        if not processor.is_applicable(coupon, cart):
            raise ValueError(f"Coupon {coupon_id} is not applicable to this cart")
        
        updated_cart, discount = processor.apply_coupon(coupon, cart)
        return updated_cart, discount, coupon