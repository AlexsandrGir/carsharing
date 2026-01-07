from contextlib import asynccontextmanager
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Импортируем наш обновленный файл с логикой БД
import request as rq 
from models import init_db

# Схемы данных для входящих запросов (Pydantic)
class BookingRequest(BaseModel):
    tg_id: int
    car_id: int

class FinishRequest(BaseModel):
    booking_id: int

@asynccontextmanager
async def lifespan(app_: FastAPI):
    # 1. Инициализируем таблицы в базе данных
    await init_db()
    # 2. Наполняем базу тестовыми машинами (функция в dao.py)
    await rq.seed_cars()
    print('--- Carsharing Backend Started ---')
    yield

app = FastAPI(title="Carsharing API", lifespan=lifespan)

# Настройка CORS для работы с Firebase и Telegram
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Эндпоинты (Маршруты) ---

# 1. Получить список всех доступных машин для карты
@app.get("/api/cars")
async def get_cars():
    cars = await rq.get_available_cars()
    return cars

# 2. Получить профиль пользователя (баланс, ID)
@app.get("/api/profile/{tg_id}")
async def get_profile(tg_id: int):
    user = await rq.add_user(tg_id)
    # Получаем информацию об активных поездках, если они есть
    active_booking = await rq.get_active_booking(user.id)
    
    return {
        "id": user.tg_id,
        "balance": user.balance,
        "active_booking": active_booking
    }

# 3. Забронировать машину
@app.post("/api/booking/start")
async def start_booking(data: BookingRequest):
    user = await rq.add_user(data.tg_id)
    
    # Пытаемся забронировать
    success, message = await rq.create_booking(user.id, data.car_id)
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
        
    return {"status": "ok", "message": message}

# 4. Завершить поездку
@app.post("/api/booking/finish")
async def finish_booking(data: FinishRequest):
    result = await rq.finish_ride(data.booking_id)
    if not result:
        raise HTTPException(status_code=400, detail="Не удалось завершить поездку")
    return {"status": "ok", "cost": result}

# Тестовый эндпоинт проверки связи
@app.get("/api/health")
async def health():
    return {"status": "working"}