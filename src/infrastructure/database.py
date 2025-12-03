from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import text
from contextlib import contextmanager, asynccontextmanager
from typing import Generator, AsyncGenerator
from src.config.settings import get_settings
from src.utilities.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Create database engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    pool_pre_ping=True
)

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Metadata for table creation
metadata = MetaData()

# Keep the existing synchronous context manager
@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for database sessions with proper error handling"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database session error: {str(e)}")
        raise
    finally:
        db.close()

# ADD THIS: Async context manager
@asynccontextmanager
async def get_db_session_async() -> AsyncGenerator[Session, None]:
    """Async context manager for database sessions"""
    db = SessionLocal()
    try:
        yield db
        db.commit()  # Note: SQLAlchemy ORM is synchronous
    except Exception as e:
        db.rollback()
        logger.error(f"Database session error: {str(e)}")
        raise
    finally:
        db.close()

def get_db_dependency() -> Generator[Session, None, None]:
    """Dependency for FastAPI to get database session"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error(f"Database session error: {str(e)}")
        raise
    finally:
        db.close()

class DatabaseManager:
    """Manages database operations"""
    def __init__(self):
        self.engine = engine
        self.metadata = metadata
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around a series of operations."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error during database session: {str(e)}")
            raise
        finally:
            session.close()

    # ADD THIS: Async version
    @asynccontextmanager
    async def get_session_async(self) -> AsyncGenerator[Session, None]:
        """Async version: Provide a transactional scope around a series of operations."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error during database session: {str(e)}")
            raise
        finally:
            session.close()

    def create_tables(self):
        """Create all tables"""
        try:
            self.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {str(e)}")
            raise

    def drop_tables(self):
        """Drop all tables"""
        try:
            self.metadata.drop_all(bind=self.engine)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop tables: {str(e)}")
            raise

    def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            with self.engine.connect() as connection:
                connection.scalar(text("SELECT 1"))
            logger.info("Database health check passed")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False

# Global database manager instance
_db_manager = DatabaseManager()

def get_db() -> DatabaseManager:
    """Return the database manager instance"""
    return _db_manager