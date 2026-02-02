from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import csv
import io
from datetime import datetime, date

from models.base import async_session_maker
from models.repositories import ConsultationRequestRepository, UserRepository, ServiceRepository
from models.database import ConsultationRequest, User, Service
from config.settings import settings

app = FastAPI(title="Med-Plastic Admin Panel", version="1.0.0")

# Настройка шаблонов
templates = Jinja2Templates(directory="admin/templates")

# Статические файлы
app.mount("/static", StaticFiles(directory="admin/static"), name="static")


async def get_session():
    """Dependency для получения сессии БД"""
    async with async_session_maker() as session:
        yield session


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_session)):
    """Главная панель администратора"""
    
    # Получаем статистику
    request_repo = ConsultationRequestRepository(session)
    user_repo = UserRepository(session)
    
    # Новые заявки
    new_requests = await request_repo.get_all(status="new")
    
    # Статистика по статусам
    stats_query = select(
        ConsultationRequest.status,
        func.count(ConsultationRequest.id)
    ).group_by(ConsultationRequest.status)
    stats_result = await session.execute(stats_query)
    stats = dict(stats_result.all())
    
    # Всего пользователей и заявок
    total_users = await session.execute(select(func.count(User.id)))
    total_requests = await session.execute(select(func.count(ConsultationRequest.id)))
    
    context = {
        "request": request,
        "new_requests": new_requests[:5],  # Последние 5 заявок
        "stats": stats,
        "total_users": total_users.scalar(),
        "total_requests": total_requests.scalar(),
        "clinic_name": settings.clinic_name
    }
    
    return templates.TemplateResponse("dashboard.html", context)


@app.get("/requests", response_class=HTMLResponse)
async def requests_page(
    request: Request, 
    status: str = None,
    session: AsyncSession = Depends(get_session)
):
    """Страница со всеми заявками"""
    
    request_repo = ConsultationRequestRepository(session)
    requests = await request_repo.get_all(status=status)
    
    # Получаем информацию о пользователях и услугах
    for req in requests:
        # Загружаем связанные данные
        user = await session.get(User, req.user_id)
        service = await session.get(Service, req.service_id)
        req.user_name = user.first_name if user else "Unknown"
        req.user_phone = user.phone if user else "Unknown"
        req.service_name = service.name if service else "Unknown"
    
    context = {
        "request": request,
        "requests": requests,
        "current_status": status,
        "clinic_name": settings.clinic_name
    }
    
    return templates.TemplateResponse("requests.html", context)


@app.post("/api/requests/{request_id}/status")
async def update_request_status(
    request_id: int,
    status: str,
    session: AsyncSession = Depends(get_session)
):
    """Обновление статуса заявки"""
    
    request_repo = ConsultationRequestRepository(session)
    updated_request = await request_repo.update_status(request_id, status)
    
    if not updated_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    return {"success": True, "status": status}


@app.get("/api/requests/export")
async def export_requests(session: AsyncSession = Depends(get_session)):
    """Экспорт заявок в CSV"""
    
    request_repo = ConsultationRequestRepository(session)
    requests = await request_repo.get_all()
    
    # Создаем CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Заголовки
    writer.writerow([
        'ID', 'Имя', 'Телефон', 'Услуга', 'Статус', 
        'Предпочтительная дата', 'Комментарий', 'Дата создания'
    ])
    
    # Данные
    for req in requests:
        user = await session.get(User, req.user_id)
        service = await session.get(Service, req.service_id)
        
        writer.writerow([
            req.id,
            req.name,
            req.phone,
            service.name if service else 'Unknown',
            req.status,
            req.preferred_date.strftime('%d.%m.%Y') if req.preferred_date else '',
            req.comment,
            req.created_at.strftime('%d.%m.%Y %H:%M')
        ])
    
    # Возвращаем файл
    output.seek(0)
    return JSONResponse(
        content={
            "csv": output.getvalue(),
            "filename": f"requests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )


@app.get("/services", response_class=HTMLResponse)
async def services_page(request: Request, session: AsyncSession = Depends(get_session)):
    """Страница управления услугами"""
    
    service_repo = ServiceRepository(session)
    services = await service_repo.get_all()
    
    context = {
        "request": request,
        "services": services,
        "clinic_name": settings.clinic_name
    }
    
    return templates.TemplateResponse("services.html", context)


@app.post("/api/services/{service_id}")
async def update_service(
    service_id: int,
    service_data: dict,
    session: AsyncSession = Depends(get_session)
):
    """Обновление информации об услуге"""
    
    service_repo = ServiceRepository(session)
    updated_service = await service_repo.update(service_id, **service_data)
    
    if not updated_service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    return {"success": True}


@app.get("/api/stats")
async def get_stats(session: AsyncSession = Depends(get_session)):
    """Получение статистики для графиков"""
    
    # Заявки по дням за последние 30 дней
    daily_stats_query = select(
        func.date(ConsultationRequest.created_at).label('date'),
        func.count(ConsultationRequest.id).label('count')
    ).where(
        ConsultationRequest.created_at >= datetime.now().replace(day=1)
    ).group_by(func.date(ConsultationRequest.created_at))
    
    daily_result = await session.execute(daily_stats_query)
    daily_stats = [
        {"date": str(row.date), "count": row.count}
        for row in daily_result
    ]
    
    # Статистика по статусам
    status_stats_query = select(
        ConsultationRequest.status,
        func.count(ConsultationRequest.id)
    ).group_by(ConsultationRequest.status)
    
    status_result = await session.execute(status_stats_query)
    status_stats = dict(status_result.all())
    
    return {
        "daily": daily_stats,
        "status": status_stats
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
