from sqlalchemy import ForeignKey, String, BigInteger, Float, DateTime
from sqlalchemy.orm import Mapped, DeclarativeBase, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from datetime import datetime
from typing import List, Optional

engine = create_async_engine(url='sqlite+aiosqlite:///db.sqlite3', echo=True)
async_session = async_sessionmaker(bind=engine, expire_on_commit=False)

class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id = mapped_column(BigInteger, unique=True)
    balance: Mapped[float] = mapped_column(default=1000.0)  # Дарим 1000р при регистрации
    
    # Связь с поездками
    bookings: Mapped[List["Booking"]] = relationship(back_populates="user_rel")

class Car(Base):
    __tablename__ = 'cars'

    id: Mapped[int] = mapped_column(primary_key=True)
    model: Mapped[str] = mapped_column(String(64))      # Например, "Tesla Model 3"
    number: Mapped[str] = mapped_column(String(10))     # Госномер
    lat: Mapped[float] = mapped_column(Float)           # Широта
    lng: Mapped[float] = mapped_column(Float)           # Долгота
    fuel: Mapped[int] = mapped_column(default=100)      # Топливо в %
    price_per_minute: Mapped[float] = mapped_column(default=10.0)
    status: Mapped[str] = mapped_column(String(20), default="free") # free, booked, in_use

class Booking(Base):
    __tablename__ = 'bookings'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    car_id: Mapped[int] = mapped_column(ForeignKey('cars.id'))
    start_time: Mapped[datetime] = mapped_column(default=datetime.now)
    end_time: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    total_cost: Mapped[float] = mapped_column(default=0.0)
    status: Mapped[str] = mapped_column(default="active") # active, finished

    user_rel: Mapped["User"] = relationship(back_populates="bookings")

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)