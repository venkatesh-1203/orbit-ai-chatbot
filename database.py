import datetime
import os

from dotenv import load_dotenv
from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine, inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./automation.db")

engine_options = (
    {"connect_args": {"check_same_thread": False}}
    if DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class AutomationLog(Base):
    __tablename__ = "automation_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_name = Column(String, index=True, nullable=False)
    prompt_sent = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    timestamp = Column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )


def init_db() -> None:
    if engine.dialect.name == "sqlite":
        inspector = inspect(engine)
        if inspector.has_table(AutomationLog.__tablename__):
            columns = {
                column["name"]
                for column in inspector.get_columns(AutomationLog.__tablename__)
            }
            if "task_name" not in columns:
                with engine.begin() as connection:
                    connection.execute(
                        text("ALTER TABLE automation_logs ADD COLUMN task_name VARCHAR")
                    )
                    connection.execute(
                        text(
                            "UPDATE automation_logs "
                            "SET task_name = :task_name WHERE task_name IS NULL"
                        ),
                        {"task_name": "Legacy task"},
                    )

    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def db_create_log(
    db: Session, task_name: str, prompt_sent: str, ai_response: str
) -> AutomationLog:
    new_log = AutomationLog(
        task_name=task_name,
        prompt_sent=prompt_sent,
        ai_response=ai_response,
    )
    try:
        db.add(new_log)
        db.commit()
        db.refresh(new_log)
        return new_log
    except Exception:
        db.rollback()
        raise
def db_fetch_all_logs(db: Session):
    return db.query(AutomationLog).order_by(AutomationLog.timestamp.desc()).all()


def db_search_logs_by_task(db: Session, query_string: str):
    return (
        db.query(AutomationLog)
        .filter(AutomationLog.task_name.contains(query_string))
        .order_by(AutomationLog.timestamp.desc())
        .all()
    )


def db_delete_log_by_id(db: Session, log_id: int) -> bool:
    try:
        record = db.query(AutomationLog).filter(AutomationLog.id == log_id).first()
        if record is None:
            return False
        db.delete(record)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
