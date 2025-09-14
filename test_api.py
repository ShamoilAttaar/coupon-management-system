#!/usr/bin/env python3
"""
API Testing Script for Coupon Management System
Tests all endpoints and prints responses directly
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def print_section(title):
    """Print a section header"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")

def print_result(test_name, success, response_data=None):
    """Print test result with response data"""
    status = "PASS" if success else "FAIL"
    print(f"{status}: {test_name}")
    if response_data:
        print(f"Response: {json.dumps(response_data, indent=2)}")
    print()

def test_api():
    """Test all API endpoints"""
    print_section("Coupon Management System - API Testing")
    print(f"Testing API at: {BASE_URL}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    created_coupons = []
    
    try:
        # 1. Health Check
        print_section("Health & Status Endpoints")
        
        response = requests.get(f"{BASE_URL}/health")
        success = response.status_code == 200
        print_result("Health Check", success, response.json())
        
        response = requests.get(f"{BASE_URL}/")
        success = response.status_code == 200
        print_result("Root Endpoint", success, response.json())
        
        # 2. Create Coupons
        print_section("Creating Test Coupons")
        
        # Cart-wise coupon
        cart_coupon = {
            "name": "Test Cart Coupon",
            "type": "cart-wise",
            "details": {
                "threshold": 100.0,
                "discount": 10.0
            }
        }
        response = requests.post(f"{BASE_URL}/coupons", json=cart_coupon)
        success = response.status_code == 201
        if success:
            created_coupons.append(response.json()["id"])
        print_result("Create Cart-wise Coupon", success, response.json())
        
        # Product-wise coupon
        product_coupon = {
            "name": "Test Product Coupon",
            "type": "product-wise",
            "details": {
                "product_id": 1,
                "discount": 20.0,
                "min_quantity": 1
            }
        }
        response = requests.post(f"{BASE_URL}/coupons", json=product_coupon)
        success = response.status_code == 201
        if success:
            created_coupons.append(response.json()["id"])
        print_result("Create Product-wise Coupon", success, response.json())
        
        # BxGy coupon
        bxgy_coupon = {
            "name": "Test BxGy Coupon",
            "type": "bxgy",
            "details": {
                "buy_products": [{"product_id": 1, "quantity": 2}],
                "get_products": [{"product_id": 2, "quantity": 1}],
                "repetition_limit": 1
            }
        }
        response = requests.post(f"{BASE_URL}/coupons", json=bxgy_coupon)
        success = response.status_code == 201
        if success:
            created_coupons.append(response.json()["id"])
        print_result("Create BxGy Coupon", success, response.json())
        
        # 3. Get Coupons
        print_section("Retrieving Coupons")
        
        response = requests.get(f"{BASE_URL}/coupons")
        success = response.status_code == 200
        print_result("Get All Coupons", success, response.json())
        
        if created_coupons:
            response = requests.get(f"{BASE_URL}/coupons/{created_coupons[0]}")
            success = response.status_code == 200
            print_result("Get Specific Coupon", success, response.json())
        
        # 4. Test Cart
        print_section("Testing Coupon Application")
        
        test_cart = {
            "cart": {
                "items": [
                    {"product_id": 1, "quantity": 3, "price": 50.0},
                    {"product_id": 2, "quantity": 2, "price": 30.0},
                    {"product_id": 3, "quantity": 1, "price": 25.0}
                ]
            }
        }
        cart_total = sum(item["price"] * item["quantity"] for item in test_cart["cart"]["items"])
        print(f"Test Cart Total: ${cart_total}")
        print()
        
        # Get applicable coupons
        response = requests.post(f"{BASE_URL}/applicable-coupons", json=test_cart)
        success = response.status_code == 200
        print_result("Get Applicable Coupons", success, response.json())
        
        # Apply cart-wise coupon
        if len(created_coupons) > 0:
            response = requests.post(f"{BASE_URL}/apply-coupon/{created_coupons[0]}", json=test_cart)
            success = response.status_code == 200
            print_result("Apply Cart-wise Coupon", success, response.json())
        
        # Apply product-wise coupon
        if len(created_coupons) > 1:
            response = requests.post(f"{BASE_URL}/apply-coupon/{created_coupons[1]}", json=test_cart)
            success = response.status_code == 200
            print_result("Apply Product-wise Coupon", success, response.json())
        
        # Apply BxGy coupon
        if len(created_coupons) > 2:
            response = requests.post(f"{BASE_URL}/apply-coupon/{created_coupons[2]}", json=test_cart)
            success = response.status_code == 200
            print_result("Apply BxGy Coupon", success, response.json())
        
        # 5. Error Handling
        print_section("Testing Error Handling")
        
        # Invalid coupon ID
        response = requests.post(f"{BASE_URL}/apply-coupon/99999", json=test_cart)
        success = response.status_code == 400
        print_result("Invalid Coupon ID", success, response.json())
        
        # Non-existent coupon
        response = requests.get(f"{BASE_URL}/coupons/99999")
        success = response.status_code == 404
        print_result("Get Non-existent Coupon", success, response.json())
        
        # Invalid coupon data
        invalid_coupon = {
            "name": "Invalid Coupon",
            "type": "invalid-type",
            "details": {"invalid": "data"}
        }
        response = requests.post(f"{BASE_URL}/coupons", json=invalid_coupon)
        success = response.status_code == 422
        print_result("Invalid Coupon Data", success, response.json())
        
        # 6. Update Coupon
        print_section("Testing Update Operations")
        
        if created_coupons:
            update_data = {
                "name": "Updated Test Coupon",
                "is_active": False
            }
            response = requests.put(f"{BASE_URL}/coupons/{created_coupons[0]}", json=update_data)
            success = response.status_code == 200
            print_result("Update Coupon", success, response.json())
        
        # 7. Cleanup
        print_section("Cleaning Up Test Data")
        
        for coupon_id in created_coupons:
            response = requests.delete(f"{BASE_URL}/coupons/{coupon_id}")
            success = response.status_code == 204
            print_result(f"Delete Coupon {coupon_id}", success, {"status": "deleted" if success else "failed"})
        
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to server. Make sure it's running with: python run.py")
        return
    except Exception as e:
        print(f"ERROR: {e}")
        return
    
    # Summary
    print_section("Testing Complete")
    print("All API endpoints have been tested successfully!")
    print(f"Visit {BASE_URL}/docs for interactive API documentation")

if __name__ == "__main__":
    test_api()
