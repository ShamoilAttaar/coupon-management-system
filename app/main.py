from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import json
from datetime import datetime

from .database import get_db, create_tables, Coupon
from .models import (
    CouponCreate, CouponUpdate, CouponResponse, 
    ApplicableCouponsResponse, ApplyCouponRequest, ApplyCouponResponse,
    Cart, CartItem
)
from .services import CouponService

# Create FastAPI app
app = FastAPI(
    title="Coupon Management System",
    description="RESTful API for managing and applying discount coupons",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize coupon service
coupon_service = CouponService()

# Create database tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()

@app.get("/")
async def root():
    return {"message": "Coupon Management System API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# CRUD Operations for Coupons

@app.post("/coupons", response_model=CouponResponse, status_code=status.HTTP_201_CREATED)
async def create_coupon(coupon_data: CouponCreate, db: Session = Depends(get_db)):
    """Create a new coupon"""
    try:
        # Convert details to JSON string
        details_json = json.dumps(coupon_data.details.dict())
        
        # Create coupon in database
        db_coupon = Coupon(
            name=coupon_data.name,
            type=coupon_data.type.value,
            details=details_json,
            expires_at=coupon_data.expires_at
        )
        
        db.add(db_coupon)
        db.commit()
        db.refresh(db_coupon)
        
        # Return response
        return CouponResponse(
            id=db_coupon.id,
            name=db_coupon.name,
            type=coupon_data.type,
            details=json.loads(db_coupon.details),
            is_active=db_coupon.is_active,
            created_at=db_coupon.created_at,
            expires_at=db_coupon.expires_at
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create coupon: {str(e)}"
        )

@app.get("/coupons", response_model=List[CouponResponse])
async def get_coupons(
    skip: int = 0, 
    limit: int = 100, 
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """Retrieve all coupons with optional filtering"""
    query = db.query(Coupon)
    
    if active_only:
        query = query.filter(Coupon.is_active == True)
    
    coupons = query.offset(skip).limit(limit).all()
    
    return [
        CouponResponse(
            id=coupon.id,
            name=coupon.name,
            type=coupon.type,
            details=json.loads(coupon.details),
            is_active=coupon.is_active,
            created_at=coupon.created_at,
            expires_at=coupon.expires_at
        )
        for coupon in coupons
    ]

@app.get("/coupons/{coupon_id}", response_model=CouponResponse)
async def get_coupon(coupon_id: int, db: Session = Depends(get_db)):
    """Retrieve a specific coupon by its ID"""
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coupon with ID {coupon_id} not found"
        )
    
    return CouponResponse(
        id=coupon.id,
        name=coupon.name,
        type=coupon.type,
        details=json.loads(coupon.details),
        is_active=coupon.is_active,
        created_at=coupon.created_at,
        expires_at=coupon.expires_at
    )

@app.put("/coupons/{coupon_id}", response_model=CouponResponse)
async def update_coupon(
    coupon_id: int, 
    coupon_update: CouponUpdate, 
    db: Session = Depends(get_db)
):
    """Update a specific coupon by its ID"""
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coupon with ID {coupon_id} not found"
        )
    
    try:
        # Update fields if provided
        if coupon_update.name is not None:
            coupon.name = coupon_update.name
        if coupon_update.is_active is not None:
            coupon.is_active = coupon_update.is_active
        if coupon_update.expires_at is not None:
            coupon.expires_at = coupon_update.expires_at
        
        db.commit()
        db.refresh(coupon)
        
        return CouponResponse(
            id=coupon.id,
            name=coupon.name,
            type=coupon.type,
            details=json.loads(coupon.details),
            is_active=coupon.is_active,
            created_at=coupon.created_at,
            expires_at=coupon.expires_at
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update coupon: {str(e)}"
        )

@app.delete("/coupons/{coupon_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_coupon(coupon_id: int, db: Session = Depends(get_db)):
    """Delete a specific coupon by its ID"""
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coupon with ID {coupon_id} not found"
        )
    
    try:
        db.delete(coupon)
        db.commit()
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete coupon: {str(e)}"
        )

# Coupon Application Operations

@app.post("/applicable-coupons", response_model=ApplicableCouponsResponse)
async def get_applicable_coupons(
    request: ApplyCouponRequest, 
    db: Session = Depends(get_db)
):
    """Fetch all applicable coupons for a given cart and calculate discounts"""
    try:
        applicable_coupons = coupon_service.get_applicable_coupons(db, request.cart)
        
        return ApplicableCouponsResponse(applicable_coupons=applicable_coupons)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get applicable coupons: {str(e)}"
        )

@app.post("/apply-coupon/{coupon_id}", response_model=ApplyCouponResponse)
async def apply_coupon(
    coupon_id: int, 
    request: ApplyCouponRequest, 
    db: Session = Depends(get_db)
):
    """Apply a specific coupon to the cart and return updated cart"""
    try:
        updated_cart, discount, coupon = coupon_service.apply_coupon(
            db, coupon_id, request.cart
        )
        
        # Calculate totals
        total_price = sum(item.price * item.quantity for item in updated_cart.items)
        total_discount = sum(item.total_discount for item in updated_cart.items)
        final_price = total_price - total_discount
        
        # Create coupon response
        coupon_response = CouponResponse(
            id=coupon.id,
            name=coupon.name,
            type=coupon.type,
            details=json.loads(coupon.details),
            is_active=coupon.is_active,
            created_at=coupon.created_at,
            expires_at=coupon.expires_at
        )
        
        return ApplyCouponResponse(
            updated_cart=updated_cart,
            total_price=round(total_price, 2),
            total_discount=round(total_discount, 2),
            final_price=round(final_price, 2),
            applied_coupon=coupon_response
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply coupon: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
