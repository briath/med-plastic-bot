from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Text, ForeignKey, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.base import Base


class User(Base):
    """Пользователи Telegram"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    consultation_requests = relationship("ConsultationRequest", back_populates="user")
    chat_logs = relationship("ChatLog", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, first_name={self.first_name})>"


class Service(Base):
    """Услуги (спарсенные с сайта)"""
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)  # "Блефаропластика верхних век"
    description = Column(Text, nullable=True)  # полное описание
    indications = Column(Text, nullable=True)  # показания
    methods = Column(Text, nullable=True)  # методики
    duration = Column(String(100), nullable=True)  # длительность операции
    recovery = Column(Text, nullable=True)  # реабилитация
    price_range = Column(String(100), nullable=True)  # "от 50 до 100 тыс."
    source_url = Column(String(500), nullable=True)  # URL источника
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    consultation_requests = relationship("ConsultationRequest", back_populates="service")
    
    def __repr__(self):
        return f"<Service(id={self.id}, name='{self.name}')>"


class ConsultationRequest(Base):
    """Заявки на консультацию"""
    __tablename__ = "consultation_requests"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    preferred_date = Column(Date, nullable=True)
    comment = Column(Text, nullable=True)
    status = Column(String(50), default="new")  # new, contacted, appointed, cancelled
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="consultation_requests")
    service = relationship("Service", back_populates="consultation_requests")
    
    def __repr__(self):
        return f"<ConsultationRequest(id={self.id}, user_id={self.user_id}, status='{self.status}')>"


class ChatLog(Base):
    """Логи диалогов (для анализа и дообучения модели)"""
    __tablename__ = "chat_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)  # вопрос пользователя
    response = Column(Text, nullable=False)  # ответ бота
    intent = Column(String(100), nullable=True)  # распознанная интент
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="chat_logs")
    
    def __repr__(self):
        return f"<ChatLog(id={self.id}, user_id={self.user_id}, intent='{self.intent}')>"


class FAQ(Base):
    """База знаний часто задаваемых вопросов"""
    __tablename__ = "faq"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    keywords = Column(String(500), nullable=True)  # ключевые слова для поиска
    service_id = Column(Integer, ForeignKey("services.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    service = relationship("Service")
    
    def __repr__(self):
        return f"<FAQ(id={self.id}, question='{self.question[:50]}...')>"
