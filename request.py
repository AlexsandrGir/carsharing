from sqlalchemy import select, update
from models import async_session, User, Car, Booking
from datetime import datetime

# 1. Наполнение базы тестовыми данными
async def seed_cars():
    async with async_session() as session:
        result = await session.execute(select(Car))
        if not result.scalars().first():
            cars = [
                Car(model="Tesla Model 3", number="А777АА77", lat=55.7558, lng=37.6173, price_per_minute=15.0),
                Car(model="BMW 3", number="В123ВВ77", lat=55.7590, lng=37.6250, price_per_minute=12.0),
                Car(model="Audi A4", number="О001ОО77", lat=55.7512, lng=37.6011, price_per_minute=11.0)
            ]
            session.add_all(cars)
            await session.commit()

# 2. Получение юзера или его создание
async def add_user(tg_id):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if not user:
            user = User(tg_id=tg_id, balance=1000.0) # Стартовый баланс
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user

# 3. Список свободных машин
async def get_available_cars():
    async with async_session() as session:
        result = await session.scalars(select(Car).where(Car.status == "free"))
        # Превращаем объекты SQLAlchemy в обычные словари для JSON
        cars = []
        for car in result:
            cars.append({
                "id": car.id,
                "model": car.model,
                "number": car.number,
                "lat": car.lat,
                "lng": car.lng,
                "fuel": car.fuel,
                "price": car.price_per_minute
            })
        return cars

# 4. Создание бронирования
async def create_booking(user_id, car_id):
    async with async_session() as session:
        # Проверяем, нет ли активных поездок
        active = await session.scalar(select(Booking).where(Booking.user_id == user_id, Booking.status == "active"))
        if active:
            return False, "У вас уже есть активная поездка"

        # Создаем бронь
        new_booking = Booking(user_id=user_id, car_id=car_id)
        session.add(new_booking)
        
        # Меняем статус машины
        await session.execute(update(Car).where(Car.id == car_id).values(status="booked"))
        
        await session.commit()
        return True, "Автомобиль забронирован"

# 5. Информация об активной поездке
async def get_active_booking(user_id):
    async with async_session() as session:
        booking = await session.scalar(select(Booking).where(Booking.user_id == user_id, Booking.status == "active"))
        if booking:
            car = await session.get(Car, booking.car_id)
            return {
                "id": booking.id,
                "car_model": car.model,
                "start_time": booking.start_time.isoformat(),
                "price": car.price_per_minute
            }
        return None

# 6. Завершение поездки и расчет
async def finish_ride(booking_id):
    async with async_session() as session:
        booking = await session.get(Booking, booking_id)
        if not booking or booking.status == "finished":
            return None

        # Фиксируем время конца
        end_time = datetime.now()
        duration = (end_time - booking.start_time).total_seconds() / 60
        if duration < 1: duration = 1 # Минимум 1 минута

        car = await session.get(Car, booking.car_id)
        cost = round(duration * car.price_per_minute, 2)

        # Обновляем бронь
        booking.end_time = end_time
        booking.total_cost = cost
        booking.status = "finished"

        # Списываем деньги у юзера
        user = await session.get(User, booking.user_id)
        user.balance -= cost

        # Освобождаем машину
        car.status = "free"

        await session.commit()
        return cost