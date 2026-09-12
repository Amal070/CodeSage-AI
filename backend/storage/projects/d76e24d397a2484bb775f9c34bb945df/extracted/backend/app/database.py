from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = 'postgresql+psycopg2://postgres:secret@localhost:5432/codesage_db'

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_connection():
    '''Yields transactional PostgreSQL database session.'''
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
