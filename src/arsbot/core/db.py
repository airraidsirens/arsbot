from contextlib import contextmanager
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@contextmanager
def bot_session():
    database_uri = os.environ.get("BOT_SQLALCHEMY_DATABASE_URI")
    engine = create_engine(database_uri)

    with Session(engine) as session:
        yield session
