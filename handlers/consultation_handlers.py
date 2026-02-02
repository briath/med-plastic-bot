import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date

from models.repositories import UserRepository, ServiceRepository, ConsultationRequestRepository, ChatLogRepository
from keyboards.reply_keyboards import get_services_keyboard, get_confirmation_keyboard, get_main_keyboard
from states.consultation import ConsultationStates
from config.settings import settings

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith("service_"))
async def select_service(callback: types.CallbackQuery, session: AsyncSession, state: FSMContext):
    """Выбор услуги для консультации"""
    service_id = int(callback.data.split("_")[1])
    
    service_repo = ServiceRepository(session)
    service = await service_repo.get_by_id(service_id)
    
    if not service:
        await callback.answer("❌ Услуга не найдена", show_alert=True)
        return
    
    # Сохраняем ID услуги в состоянии
    await state.update_data(service_id=service_id, service_name=service.name)
    
    # Переходим к вводу имени
    await state.set_state(ConsultationStates.entering_name)
    
    await callback.message.edit_text(
        f"✅ Выбрана услуга: *{service.name}*\n\n"
        "Теперь, пожалуйста, введите ваше имя:",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(ConsultationStates.entering_name)
async def process_name(message: types.Message, state: FSMContext):
    """Обработка ввода имени"""
    name = message.text.strip()
    
    if len(name) < 2:
        await message.answer(
            "❌ Имя слишком короткое. Пожалуйста, введите полное имя:",
            reply_markup=types.ReplyKeyboardRemove()
        )
        return
    
    # Сохраняем имя и переходим к телефону
    await state.update_data(name=name)
    await state.set_state(ConsultationStates.entering_phone)
    
    await message.answer(
        f"✅ Приятно познакомиться, {name}!\n\n"
        "Теперь, пожалуйста, введите ваш номер телефона в формате +7XXXYYYZZZZ:",
        reply_markup=types.ReplyKeyboardRemove()
    )


@router.message(ConsultationStates.entering_phone)
async def process_phone(message: types.Message, state: FSMContext):
    """Обработка ввода телефона"""
    phone = message.text.strip()
    
    # Простая валидация телефона
    import re
    phone_pattern = r'^(\+7|8)\d{10}$'
    
    if not re.match(phone_pattern, phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')):
        await message.answer(
            "❌ Неверный формат телефона. Пожалуйста, введите номер в формате +7XXXXXXXXXX:",
            reply_markup=types.ReplyKeyboardRemove()
        )
        return
    
    # Нормализуем телефон
    if phone.startswith('8'):
        phone = '+7' + phone[1:]
    
    # Сохраняем телефон и переходим к дате
    await state.update_data(phone=phone)
    await state.set_state(ConsultationStates.entering_date)
    
    await message.answer(
        "✅ Телефон принят!\n\n"
        "Теперь введите предпочтительную дату консультации (формат ДД.ММ.ГГГГ) "
        "или напишите 'удобно в любое время':",
        reply_markup=types.ReplyKeyboardRemove()
    )


@router.message(ConsultationStates.entering_date)
async def process_date(message: types.Message, state: FSMContext):
    """Обработка ввода даты"""
    date_input = message.text.strip()
    preferred_date = None
    
    if date_input.lower() not in ['удобно в любое время', 'любое время', 'когда удобно']:
        # Пытаемся распарсить дату
        try:
            # Поддерживаем разные форматы
            for fmt in ('%d.%m.%Y', '%d.%m.%y', '%d-%m-%Y', '%d-%m-%y'):
                try:
                    parsed_date = datetime.strptime(date_input, fmt).date()
                    # Проверяем, что дата не в прошлом
                    if parsed_date >= date.today():
                        preferred_date = parsed_date
                        break
                except ValueError:
                    continue
            
            if preferred_date is None:
                await message.answer(
                    "❌ Неверный формат даты или дата в прошлом. "
                    "Пожалуйста, введите дату в формате ДД.ММ.ГГГГ "
                    "или напишите 'удобно в любое время':",
                    reply_markup=types.ReplyKeyboardRemove()
                )
                return
                
        except Exception:
            await message.answer(
                "❌ Не удалось распознать дату. "
                "Пожалуйста, введите дату в формате ДД.ММ.ГГГГ "
                "или напишите 'удобно в любое время':",
                reply_markup=types.ReplyKeyboardRemove()
            )
            return
    
    # Сохраняем дату и переходим к комментарию
    await state.update_data(preferred_date=preferred_date, date_input=date_input)
    await state.set_state(ConsultationStates.entering_comment)
    
    await message.answer(
        "✅ Дата принята!\n\n"
        "Теперь вы можете добавить комментарий (если есть что уточнить) "
        "или просто нажмите 'Пропустить':",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="Пропустить")]],
            resize_keyboard=True
        )
    )


@router.message(ConsultationStates.entering_comment, F.text == "Пропустить")
async def skip_comment(message: types.Message, state: FSMContext):
    """Пропуск комментария"""
    await state.update_data(comment="")
    await show_confirmation(message, state)


@router.message(ConsultationStates.entering_comment)
async def process_comment(message: types.Message, state: FSMContext):
    """Обработка комментария"""
    comment = message.text.strip()
    await state.update_data(comment=comment)
    await show_confirmation(message, state)


async def show_confirmation(message: types.Message, state: FSMContext):
    """Показываем подтверждение записи"""
    data = await state.get_data()
    
    confirmation_text = f"""📋 *Проверьте данные для записи:*

👤 Имя: {data['name']}
📞 Телефон: {data['phone']}
🏥 Услуга: {data['service_name']}
📅 Дата: {data.get('date_input', 'удобно в любое время')}
💬 Комментарий: {data.get('comment', 'нет')}

Все верно? Подтвердите запись или отмените."""
    
    await message.answer(
        confirmation_text,
        parse_mode="Markdown",
        reply_markup=get_confirmation_keyboard()
    )


@router.callback_query(F.data == "confirm_request")
async def confirm_request(callback: types.CallbackQuery, session: AsyncSession, state: FSMContext):
    """Подтверждение записи на консультацию"""
    data = await state.get_data()
    
    try:
        # Получаем пользователя
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        
        # Если пользователя нет в базе, создаем его
        if user is None:
            user = await user_repo.create(
                telegram_id=callback.from_user.id,
                username=callback.from_user.username,
                first_name=callback.from_user.first_name,
                last_name=callback.from_user.last_name,
                phone=data.get('phone')  # Сохраняем телефон если есть
            )
        
        # Обновляем телефон пользователя
        if not user.phone and data.get('phone'):
            await user_repo.update_phone(user.id, data['phone'])
        
        # Создаем заявку на консультацию
        request_repo = ConsultationRequestRepository(session)
        consultation_request = await request_repo.create(
            user_id=user.id,
            service_id=data['service_id'],
            name=data['name'],
            phone=data['phone'],
            preferred_date=data.get('preferred_date'),
            comment=data.get('comment', ''),
            status='new'
        )
        
        # Очищаем состояние
        await state.clear()
        
        # Отправляем подтверждение
        success_text = f"""✅ *Заявка успешно создана!*

📝 *Номер заявки:* #{consultation_request.id}
👤 *Имя:* {data['name']}
📞 *Телефон:* {data['phone']}
🏥 *Услуга:* {data['service_name']}

Наш менеджер свяжется с вами в течение 2 часов в рабочее время 
для подтверждения времени консультации.

⏰ *Время работы:* Пн-Пт с 9:00 до 18:00
📞 *Телефон клиники:* {settings.clinic_phone}

Спасибо за обращение в клинику "{settings.clinic_name}"!"""
        
        await callback.message.edit_text(
            success_text,
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        
        # Логируем создание заявки
        chat_log_repo = ChatLogRepository(session)
        await chat_log_repo.create(
            user_id=user.id,
            message="Запись на консультацию",
            response=success_text,
            intent="consultation_request"
        )
        
        await callback.answer("✅ Заявка создана!")
        
        # Здесь можно добавить отправку уведомления админу
        
    except Exception as e:
        logger.error(f"Error creating consultation request: {e}")
        await callback.answer("❌ Ошибка при создании заявки", show_alert=True)


@router.callback_query(F.data == "cancel_consultation")
async def cancel_consultation(callback: types.CallbackQuery, state: FSMContext):
    """Отмена записи на консультацию"""
    await state.clear()
    
    await callback.message.edit_text(
        "❌ Запись на консультацию отменена.\n\n"
        "Вы в главном меню. Чем могу помочь?",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()


@router.message(F.text == "📅 Записаться на консультацию")
async def start_consultation(message: types.Message, session: AsyncSession, state: FSMContext):
    """Начало процесса записи на консультацию"""
    await state.clear()
    
    # Получаем список услуг
    service_repo = ServiceRepository(session)
    services = await service_repo.get_all()
    
    if not services:
        await message.answer(
            "😔 К сожалению, услуги временно недоступны. "
            "Пожалуйста, свяжитесь с живым менеджером.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Показываем выбор услуги
    await message.answer(
        "📅 *Запись на консультацию*\n\n"
        "Пожалуйста, выберите услугу:",
        parse_mode="Markdown",
        reply_markup=get_services_keyboard(services)
    )
