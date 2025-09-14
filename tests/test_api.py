import pytest
import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db, Coupon

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_api.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def sample_coupons():
    return [
        {
            "name": "Cart Discount 10%",
            "type": "cart-wise",
            "details": {
                "threshold": 100.0,
                "discount_percentage": 10.0
            }
        },
        {
            "name": "Product A Discount",
            "type": "product-wise",
            "details": {
                "product_id": 1,
                "discount_percentage": 20.0,
                "min_quantity": 1
            }
        },
        {
            "name": "Buy 2 Get 1 Free",
            "type": "bxgy",
            "details": {
                "buy_products": [
                    {"product_id": 1, "quantity": 2}
                ],
                "get_products": [
                    {"product_id": 2, "quantity": 1}
                ],
                "repetition_limit": 2
            }
        }
    ]

class TestCouponCRUD:
    def test_create_coupon_cart_wise(self, client, sample_coupons):
        response = client.post("/coupons", json=sample_coupons[0])
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Cart Discount 10%"
        assert data["type"] == "cart-wise"
        assert data["details"]["threshold"] == 100.0

    def test_create_coupon_product_wise(self, client, sample_coupons):
        response = client.post("/coupons", json=sample_coupons[1])
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Product A Discount"
        assert data["type"] == "product-wise"
        assert data["details"]["product_id"] == 1

    def test_create_coupon_bxgy(self, client, sample_coupons):
        response = client.post("/coupons", json=sample_coupons[2])
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Buy 2 Get 1 Free"
        assert data["type"] == "bxgy"
        assert len(data["details"]["buy_products"]) == 1

    def test_get_coupons(self, client, sample_coupons):
        # Create multiple coupons
        for coupon in sample_coupons:
            client.post("/coupons", json=coupon)
        
        response = client.get("/coupons")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_get_coupon_by_id(self, client, sample_coupons):
        # Create a coupon
        create_response = client.post("/coupons", json=sample_coupons[0])
        coupon_id = create_response.json()["id"]
        
        # Get the coupon
        response = client.get(f"/coupons/{coupon_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == coupon_id
        assert data["name"] == "Cart Discount 10%"

    def test_get_coupon_not_found(self, client):
        response = client.get("/coupons/999")
        assert response.status_code == 404

    def test_update_coupon(self, client, sample_coupons):
        # Create a coupon
        create_response = client.post("/coupons", json=sample_coupons[0])
        coupon_id = create_response.json()["id"]
        
        # Update the coupon
        update_data = {"name": "Updated Cart Discount", "is_active": False}
        response = client.put(f"/coupons/{coupon_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Cart Discount"
        assert data["is_active"] == False

    def test_delete_coupon(self, client, sample_coupons):
        # Create a coupon
        create_response = client.post("/coupons", json=sample_coupons[0])
        coupon_id = create_response.json()["id"]
        
        # Delete the coupon
        response = client.delete(f"/coupons/{coupon_id}")
        assert response.status_code == 204
        
        # Verify it's deleted
        get_response = client.get(f"/coupons/{coupon_id}")
        assert get_response.status_code == 404

class TestCouponApplication:
    def test_get_applicable_coupons(self, client, sample_coupons):
        # Create coupons
        for coupon in sample_coupons:
            client.post("/coupons", json=coupon)
        
        # Test cart
        cart_data = {
            "cart": {
                "items": [
                    {"product_id": 1, "quantity": 3, "price": 50.0},
                    {"product_id": 2, "quantity": 2, "price": 30.0}
                ]
            }
        }
        
        response = client.post("/applicable-coupons", json=cart_data)
        assert response.status_code == 200
        data = response.json()
        assert len(data["applicable_coupons"]) >= 1

    def test_apply_coupon_cart_wise(self, client, sample_coupons):
        # Create cart-wise coupon
        create_response = client.post("/coupons", json=sample_coupons[0])
        coupon_id = create_response.json()["id"]
        
        # Test cart with total > 100
        cart_data = {
            "cart": {
                "items": [
                    {"product_id": 1, "quantity": 3, "price": 50.0}  # Total: 150
                ]
            }
        }
        
        response = client.post(f"/apply-coupon/{coupon_id}", json=cart_data)
        assert response.status_code == 200
        data = response.json()
        assert data["total_discount"] == 15.0  # 10% of 150
        assert data["final_price"] == 135.0

    def test_apply_coupon_product_wise(self, client, sample_coupons):
        # Create product-wise coupon
        create_response = client.post("/coupons", json=sample_coupons[1])
        coupon_id = create_response.json()["id"]
        
        # Test cart with product 1
        cart_data = {
            "cart": {
                "items": [
                    {"product_id": 1, "quantity": 2, "price": 50.0}  # Total: 100
                ]
            }
        }
        
        response = client.post(f"/apply-coupon/{coupon_id}", json=cart_data)
        assert response.status_code == 200
        data = response.json()
        assert data["total_discount"] == 20.0  # 20% of 100
        assert data["final_price"] == 80.0

    def test_apply_coupon_bxgy(self, client, sample_coupons):
        # Create BxGy coupon
        create_response = client.post("/coupons", json=sample_coupons[2])
        coupon_id = create_response.json()["id"]
        
        # Test cart with 2 of product 1 and 1 of product 2
        cart_data = {
            "cart": {
                "items": [
                    {"product_id": 1, "quantity": 2, "price": 50.0},
                    {"product_id": 2, "quantity": 1, "price": 30.0}
                ]
            }
        }
        
        response = client.post(f"/apply-coupon/{coupon_id}", json=cart_data)
        assert response.status_code == 200
        data = response.json()
        assert data["total_discount"] == 30.0  # 1 product 2 free
        assert data["final_price"] == 100.0

    def test_apply_coupon_not_found(self, client):
        cart_data = {
            "cart": {
                "items": [
                    {"product_id": 1, "quantity": 1, "price": 50.0}
                ]
            }
        }
        
        response = client.post("/apply-coupon/999", json=cart_data)
        assert response.status_code == 400

    def test_apply_coupon_not_applicable(self, client, sample_coupons):
        # Create cart-wise coupon with high threshold
        high_threshold_coupon = {
            "name": "High Threshold",
            "type": "cart-wise",
            "details": {
                "threshold": 1000.0,
                "discount_percentage": 10.0
            }
        }
        
        create_response = client.post("/coupons", json=high_threshold_coupon)
        coupon_id = create_response.json()["id"]
        
        # Test cart with low total
        cart_data = {
            "cart": {
                "items": [
                    {"product_id": 1, "quantity": 1, "price": 50.0}  # Total: 50
                ]
            }
        }
        
        response = client.post(f"/apply-coupon/{coupon_id}", json=cart_data)
        assert response.status_code == 400

class TestHealthEndpoints:
    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
