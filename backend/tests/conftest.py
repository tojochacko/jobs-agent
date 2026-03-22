import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker
from backend.database import Base, get_db

# Import models to register them with Base before creating engine
import backend.models


@pytest.fixture(scope="function")
def db_engine():
    from sqlalchemy.pool import StaticPool
    
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Use StaticPool to keep single connection for :memory:
    )
    Base.metadata.create_all(engine)
    
    # Verify tables were created
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "preferences" in tables, f"preferences table not created. Tables: {tables}"
    
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    SessionLocal = sessionmaker(bind=db_engine)
    with SessionLocal() as session:
        yield session


@pytest.fixture(scope="function")
def client(db_engine):
    # Import here to avoid circular issues before app is assembled
    from backend.main import app

    # Verify tables exist on this engine
    inspector = inspect(db_engine)
    tables = inspect(db_engine).get_table_names()
    assert "preferences" in tables, f"preferences table missing before client setup. Tables: {tables}"

    SessionLocal = sessionmaker(bind=db_engine)
    
    def override_get_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()
