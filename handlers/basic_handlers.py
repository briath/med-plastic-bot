import logging
from aiogram import Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from models.repositories import UserRepository, ServiceRepository, ChatLogRepository
from keyboards.reply_keyboards import get_main_keyboard
from states.consultation import ConsultationStates
from services.openai_service import openai_service, fallback_service
from config.settings import settings
from utils.message_splitter import split_message

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message, session: AsyncSession, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()
    
    # Получаем или создаем пользователя
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    
    if not user:
        user = await user_repo.create(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
    
    # Приветственное сообщение
    welcome_text = f"""👋 Добрый день, {message.from_user.first_name or 'гость'}!

Вас приветствует виртуальный помощник клиники **"{settings.clinic_name}"**. 
Меня зовут Анна, и я готова ответить на ваши вопросы о пластике верхних век.

Я могу помочь вам:
📋 Рассказать об услуге подробно
💰 Проинформировать о ценах
📅 Записать на консультацию
👨‍💼 Связать с живым менеджером
❓ Ответить на частые вопросы

Выберите интересующий вас пункт ниже 👇"""
    
    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )
    
    # Логируем обращение
    chat_log_repo = ChatLogRepository(session)
    await chat_log_repo.create(
        user_id=user.id,
        message="/start",
        response=welcome_text,
        intent="start"
    )


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    help_text = """🆘 *Помощь*

Доступные команды:
/start - Начать диалог
/help - Показать это сообщение
/cancel - Отменить текущее действие

Основные функции:
📋 Узнать об услуге - подробная информация о блефаропластике
💰 Цены - информация о стоимости процедур
📅 Записаться на консультацию - запись на очную консультацию
👨‍💼 Связаться с менеджером - быстрый контакт с живым специалистом
❓ Частые вопросы - ответы на популярные вопросы

Если у вас возникли проблемы, напишите @admin"""
    
    await message.answer(help_text, parse_mode="Markdown")


@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    """Обработчик команды /cancel"""
    await state.clear()
    await message.answer(
        "❌ Действие отменено. Вы в главном меню.",
        reply_markup=get_main_keyboard()
    )


@router.message(F.text == "❌ Отмена")
async def btn_cancel(message: types.Message, state: FSMContext):
    """Обработчик кнопки Отмена"""
    await state.clear()
    await message.answer(
        "❌ Действие отменено. Вы в главном меню.",
        reply_markup=get_main_keyboard()
    )


@router.message(F.text == "🔙 В главное меню")
async def btn_main_menu(message: types.Message, state: FSMContext):
    """Обработчик кнопки возврата в главное меню"""
    await state.clear()
    await message.answer(
        "🏠 Вы в главном меню. Чем могу помочь?",
        reply_markup=get_main_keyboard()
    )


@router.message(F.text == "📋 Узнать об услуге")
async def btn_service_info(message: types.Message, session: AsyncSession):
    """Обработчик кнопки 'Узнать об услуге'"""
    service_repo = ServiceRepository(session)
    services = await service_repo.get_all()
    
    if services:
        service = services[0]  # Берем первую услугу (блефаропластика)
        
        info_text = f"""📋 *{service.name}*

{service.description or ''}

📍 *Показания:*
{service.indications or 'Консультация хирурга'}

⏰ *Длительность:*
{service.duration or '1-2 часа'}

🔧 *Методики:*
{service.methods or 'Хирургическая, трансконъюнктивальная'}

🏥 *Реабилитация:*
{service.recovery or '7-10 дней'}

💰 *Стоимость:*
{service.price_range or 'от 50 000 рублей'}

Хотите задать конкретный вопрос или записаться на консультацию?"""
        
        # Разделяем длинное сообщение на части
        message_parts = split_message(info_text)
        
        # Отправляем части сообщения
        for part in message_parts:
            await message.answer(part, parse_mode="Markdown")
    else:
        await message.answer(
            "😔 Информация об услугах временно недоступна. "
            "Пожалуйста, свяжитесь с живым менеджером."
        )


@router.message(F.text == "💰 Цены")
async def btn_prices(message: types.Message, session: AsyncSession):
    """Обработчик кнопки 'Цены'"""
    service_repo = ServiceRepository(session)
    services = await service_repo.get_all()
    
    if services:
        service = services[0]
        
        price_text = f"""💰 *Цены на {service.name}*

{service.price_range or 'от 50 000 до 120 000 рублей'}

Стоимость зависит от:
• Сложности операции
• Выбранной методики
• Индивидуальных особенностей
• Необходимости госпитализации

💡 *Точную стоимость назовет хирург после очной консультации.*

Хотите записаться на бесплатную консультацию?"""
        
        await message.answer(price_text, parse_mode="Markdown")
    else:
        await message.answer(
            "😔 Информация о ценах временно недоступна. "
            "Пожалуйста, свяжитесь с менеджером для уточнения."
        )


@router.message(F.text == "👨‍💼 Связаться с менеджером")
async def btn_contact_manager(message: types.Message, session: AsyncSession):
    """Обработчик кнопки 'Связаться с менеджером'"""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    
    # Если пользователя нет в базе, создаем его
    if user is None:
        user = await user_repo.create(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
    
    # Здесь можно добавить логику отправки уведомления менеджеру
    # Например, отправить сообщение в админ-чат
    
    contact_text = f"""👨‍💼 *Связь с менеджером*

Ваш запрос передан живому менеджеру клиники.

📞 *Телефон клиники:* {settings.clinic_phone}
📧 *Email:* {settings.clinic_email}

⏰ *Время работы:* Пн-Пт с 9:00 до 18:00

Менеджер свяжется с вами в течение 15 минут в рабочее время.

Могу я помочь вам с чем-то еще пока вы ждете?"""
    
    await message.answer(contact_text, parse_mode="Markdown")
    
    # Логируем запрос
    chat_log_repo = ChatLogRepository(session)
    await chat_log_repo.create(
        user_id=user.id,
        message="Связаться с менеджером",
        response=contact_text,
        intent="contact_manager"
    )


@router.message(F.text == "❓ Частые вопросы")
async def btn_faq(message: types.Message):
    """Обработчик кнопки 'Частые вопросы'"""
    from keyboards.reply_keyboards import get_faq_categories_keyboard
    
    faq_text = """❓ *Частые вопросы*

Выберите категорию вопросов, которая вас интересует:

💰 Цены и стоимость
⏰ Длительность и реабилитация  
⚕️ Безопасность и риски
📋 Подготовка к операции
🏥 Общие вопросы"""
    
    await message.answer(faq_text, parse_mode="Markdown", reply_markup=get_faq_categories_keyboard())


@router.message(F.text == "ℹ️ О клинике")
async def btn_about_clinic(message: types.Message):
    """Обработчик кнопки 'О клинике'"""
    about_text = f"""🏥 *О клинике "{settings.clinic_name}"*

Наша клиника специализируется на пластической хирургии премиум-класса.

✅ *Наши преимущества:*
• Опытные хирурги с международной сертификацией
• Современное оборудование
• Индивидуальный подход к каждому пациенту
• Конфиденциальность и безопасность
• Гарантия качества

📍 *Адрес:* Москва, ул. Примерная, д. 123
📞 *Телефон:* {settings.clinic_phone}
🌐 *Сайт:* med-plastic.ru

Готова ответить на ваши вопросы о процедурах!"""
    
    await message.answer(about_text, parse_mode="Markdown")


@router.message()
async def handle_text_message(message: types.Message, session: AsyncSession, state: FSMContext):
    """Обработчик текстовых сообщений (вопросы пользователей)"""
    
    # Проверяем, не в процессе ли записи на консультацию
    current_state = await state.get_state()
    if current_state:
        return  # Если в процессе FSM, обрабатываем в других хендлерах
    
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    
    # Если пользователя нет в базе, создаем его
    if user is None:
        user = await user_repo.create(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
    
    # Получаем историю диалога
    chat_log_repo = ChatLogRepository(session)
    history = await chat_log_repo.get_user_logs(user.id, limit=5)
    
    # Формируем контекст для LLM с улучшенной историей диалога
    service_repo = ServiceRepository(session)
    services = await service_repo.get_all()
    
    # Получаем историю диалога с ответами бота
    chat_history = []
    if history:
        for log in reversed(history[-6:]):  # Берем больше сообщений для контекста
            # Добавляем сообщение пользователя
            chat_history.append({'role': 'user', 'text': log.message})
            # Добавляем ответ бота
            if log.response:
                chat_history.append({'role': 'assistant', 'text': log.response})
    
    context = {
        'service': services[0].__dict__ if services else None,
        'history': chat_history
    }
    
    # Сначала пробуем получить ответ от OpenAI
    response = await openai_service.generate_response(message.text, context)
    
    # Если LLM недоступен, используем fallback
    if not response:
        response = await fallback_service.get_fallback_response(message.text)
    
    # Если и fallback не сработал, даем стандартный ответ
    if not response:
        response = """Понимаю ваш вопрос. Чтобы дать вам точную информацию, 
пожалуйста, выберите конкретную тему из главного меню или 
свяжитесь с живым менеджером для детальной консультации."""
    
    # Разделяем длинное сообщение на части
    message_parts = split_message(response)
    
    # Отправляем части сообщения
    for part in message_parts:
        await message.answer(part)
    
    # Логируем диалог (полный ответ)
    await chat_log_repo.create(
        user_id=user.id,
        message=message.text,
        response=response,
        intent="question"
    )
