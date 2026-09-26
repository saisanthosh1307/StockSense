import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base, get_db
from backend.main import app
from backend.seed_data import seed_database

# Use the real seeded test database
@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
