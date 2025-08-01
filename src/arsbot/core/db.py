from contextlib import contextmanager
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

engine = None


def get_engine():
    global engine

    return engine


def set_engine(engine_):
    global engine

    engine = engine_


@contextmanager
def bot_session():
    database_uri = os.environ.get("BOT_SQLALCHEMY_DATABASE_URI")

    if not (engine := get_engine()):
        engine = create_engine(database_uri)

        set_engine(engine)

    with Session(engine) as session:
        yield session
