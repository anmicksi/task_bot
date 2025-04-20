from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()
DB_URL = f"mysql+mysqlconnector://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

engine = create_engine(DB_URL, echo=True)
Session = sessionmaker(bind=engine)
Base = declarative_base()

def get_session():
    return Session()

def create_db_and_tables():
    from models import User, Task
    Base.metadata.create_all(engine)
