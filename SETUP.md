# Quick Setup Guide

## Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

## Installation Steps

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**
   ```bash
   python run.py
   ```
   Or alternatively:
   ```bash
   python -m uvicorn app.main:app --reload
   ```

3. **Access the API**
   - API Base URL: `http://localhost:8000`
   - Interactive Documentation: `http://localhost:8000/docs`
   - Alternative Documentation: `http://localhost:8000/redoc`

4. **Run Tests**
   ```bash
   pytest
   ```

5. **Run Example Demo**
   ```bash
   python example_usage.py
   ```

## Quick Test

Once the server is running, you can test it with:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy", "timestamp": "2024-01-01T12:00:00.000000"}
```

## Project Structure

```
coupon-management-system/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── models.py            # Pydantic models
│   ├── database.py          # Database configuration
│   └── services.py          # Business logic
├── tests/
│   ├── __init__.py
│   ├── test_api.py          # API endpoint tests
│   └── test_services.py     # Business logic tests
├── requirements.txt         # Python dependencies
├── run.py                   # Application runner
├── example_usage.py         # Demo script
├── README.md               # Comprehensive documentation
├── SETUP.md                # This file
└── .gitignore              # Git ignore rules
```

## Next Steps

1. Read the comprehensive [README.md](README.md) for detailed documentation
2. Explore the API documentation at `http://localhost:8000/docs`
3. Run the example script to see the system in action
4. Check the test suite to understand expected behavior
