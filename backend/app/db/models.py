import uuid

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_user_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    parsed_resumes = relationship("ParsedResume", back_populates="user")
    application_logs = relationship("ApplicationLog", back_populates="user")
    autopilot_settings = relationship("AutopilotSettings", back_populates="user", uselist=False)
    autopilot_runs = relationship("AutopilotRunLog", back_populates="user")


class ParsedResume(Base):
    __tablename__ = "parsed_resumes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    source_filename: Mapped[str | None] = mapped_column(String(255))
    file_path: Mapped[str | None] = mapped_column(String(1024))
    raw_text: Mapped[str | None] = mapped_column(Text)
    parsed_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="parsed_resumes")


class ScrapedJob(Base):
    __tablename__ = "scraped_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(64))
    source_job_id: Mapped[str | None] = mapped_column(String(128), index=True)
    job_title: Mapped[str] = mapped_column(String(255))
    company: Mapped[str] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    employment_type: Mapped[str | None] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(Text)
    required_skills: Mapped[list[str] | None] = mapped_column(JSON)
    application_url: Mapped[str] = mapped_column(String(1024))
    posted_date: Mapped[Date | None] = mapped_column(Date)
    scraped_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    application_logs = relationship("ApplicationLog", back_populates="job")


class ApplicationLog(Base):
    __tablename__ = "application_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("scraped_jobs.id"))
    status: Mapped[str] = mapped_column(String(64))
    mode: Mapped[str] = mapped_column(String(32))
    result_json: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="application_logs")
    job = relationship("ScrapedJob", back_populates="application_logs")


class AutopilotSettings(Base):
    __tablename__ = "autopilot_settings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    auto_submit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    paid_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    legit_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    max_applications_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    limit_per_company: Mapped[int] = mapped_column(Integer, nullable=False, default=25)
    greenhouse_companies: Mapped[list[str] | None] = mapped_column(JSON)
    lever_companies: Mapped[list[str] | None] = mapped_column(JSON)
    title_keywords: Mapped[list[str] | None] = mapped_column(JSON)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship("User", back_populates="autopilot_settings")


class AutopilotRunLog(Base):
    __tablename__ = "autopilot_run_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    trigger: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    jobs_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    jobs_qualified: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    applications_queued: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message: Mapped[str | None] = mapped_column(Text)
    details_json: Mapped[dict | None] = mapped_column(JSON)
    started_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))

    user = relationship("User", back_populates="autopilot_runs")
