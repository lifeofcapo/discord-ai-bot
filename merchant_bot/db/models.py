from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, String, Text, ForeignKey, Boolean, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# (text-embedding-3-small = 1536)
EMBEDDING_DIM = 1536


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    display_name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    threads: Mapped[list["AIThread"]] = relationship(back_populates="student")
    screenshots: Mapped[list["Screenshot"]] = relationship(back_populates="student")
    referral_code: Mapped["ReferralCode"] = relationship(back_populates="owner", uselist=False)


class ReferralCode(Base):
    __tablename__ = "referral_codes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("students.id"), unique=True)
    balance_cents: Mapped[int] = mapped_column(BigInteger, default=0)  # виртуальный баланс, в центах
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped["Student"] = relationship(back_populates="referral_code")
    conversions: Mapped[list["ReferralConversion"]] = relationship(back_populates="referral_code")


class ReferralConversion(Base):
    __tablename__ = "referral_conversions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    referral_code_id: Mapped[int] = mapped_column(ForeignKey("referral_codes.id"))
    stripe_payment_id: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    payer_email: Mapped[str] = mapped_column(String(255))
    amount_cents: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    referral_code: Mapped["ReferralCode"] = relationship(back_populates="conversions")


class AIThread(Base):
    __tablename__ = "ai_threads"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Discord thread ID
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    kind: Mapped[str] = mapped_column(String(20))  # "merchant_ai" | "support"
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    summary: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    student: Mapped["Student"] = relationship(back_populates="threads")
    messages: Mapped[list["AIMessage"]] = relationship(back_populates="thread", order_by="AIMessage.created_at")


class AIMessage(Base):
    __tablename__ = "ai_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("ai_threads.id"))
    role: Mapped[str] = mapped_column(String(20))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)  # json for multi media
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    thread: Mapped["AIThread"] = relationship(back_populates="messages")


class KnowledgeBaseEntry(Base):
    __tablename__ = "knowledge_base"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    added_by: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ClosedThreadSummary(Base):
    __tablename__ = "closed_thread_summaries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    summary: Mapped[str] = mapped_column(Text)
    message_count: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Screenshot(Base):
    __tablename__ = "screenshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    thread_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    s3_key: Mapped[str] = mapped_column(String(300))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    student: Mapped["Student"] = relationship(back_populates="screenshots")