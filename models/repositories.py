from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from models.database import User, Service, ConsultationRequest, ChatLog, FAQ


class UserRepository:
    """Repository for User operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID"""
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create(self, telegram_id: int, username: str = None, 
                    first_name: str = None, last_name: str = None) -> User:
        """Create new user"""
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def update_phone(self, user_id: int, phone: str) -> Optional[User]:
        """Update user phone"""
        stmt = update(User).where(User.id == user_id).values(phone=phone)
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.session.get(User, user_id)


class ServiceRepository:
    """Repository for Service operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_all(self) -> List[Service]:
        """Get all services"""
        stmt = select(Service).order_by(Service.name)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_by_id(self, service_id: int) -> Optional[Service]:
        """Get service by ID"""
        return await self.session.get(Service, service_id)
    
    async def get_by_name(self, name: str) -> Optional[Service]:
        """Get service by name"""
        stmt = select(Service).where(Service.name.ilike(f"%{name}%"))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create(self, **kwargs) -> Service:
        """Create new service"""
        service = Service(**kwargs)
        self.session.add(service)
        await self.session.commit()
        await self.session.refresh(service)
        return service
    
    async def update(self, service_id: int, **kwargs) -> Optional[Service]:
        """Update service"""
        stmt = update(Service).where(Service.id == service_id).values(**kwargs)
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.session.get(Service, service_id)


class ConsultationRequestRepository:
    """Repository for ConsultationRequest operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, **kwargs) -> ConsultationRequest:
        """Create new consultation request"""
        request = ConsultationRequest(**kwargs)
        self.session.add(request)
        await self.session.commit()
        await self.session.refresh(request)
        return request
    
    async def get_all(self, status: str = None) -> List[ConsultationRequest]:
        """Get all requests, optionally filtered by status"""
        stmt = select(ConsultationRequest)
        if status:
            stmt = stmt.where(ConsultationRequest.status == status)
        stmt = stmt.order_by(ConsultationRequest.created_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_by_user_id(self, user_id: int) -> List[ConsultationRequest]:
        """Get requests by user ID"""
        stmt = select(ConsultationRequest).where(
            ConsultationRequest.user_id == user_id
        ).order_by(ConsultationRequest.created_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def update_status(self, request_id: int, status: str) -> Optional[ConsultationRequest]:
        """Update request status"""
        stmt = update(ConsultationRequest).where(
            ConsultationRequest.id == request_id
        ).values(status=status)
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.session.get(ConsultationRequest, request_id)


class ChatLogRepository:
    """Repository for ChatLog operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, user_id: int, message: str, response: str, 
                    intent: str = None) -> ChatLog:
        """Create new chat log entry"""
        log = ChatLog(
            user_id=user_id,
            message=message,
            response=response,
            intent=intent
        )
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log
    
    async def get_user_logs(self, user_id: int, limit: int = 50) -> List[ChatLog]:
        """Get user chat history"""
        stmt = select(ChatLog).where(
            ChatLog.user_id == user_id
        ).order_by(ChatLog.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()


class FAQRepository:
    """Repository for FAQ operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_all(self) -> List[FAQ]:
        """Get all FAQ entries"""
        stmt = select(FAQ).order_by(FAQ.question)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def search(self, query: str, limit: int = 5) -> List[FAQ]:
        """Search FAQ by keywords"""
        stmt = select(FAQ).where(
            FAQ.question.ilike(f"%{query}%") |
            FAQ.keywords.ilike(f"%{query}%")
        ).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def create(self, question: str, answer: str, 
                    keywords: str = None, service_id: int = None) -> FAQ:
        """Create new FAQ entry"""
        faq = FAQ(
            question=question,
            answer=answer,
            keywords=keywords,
            service_id=service_id
        )
        self.session.add(faq)
        await self.session.commit()
        await self.session.refresh(faq)
        return faq
