from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Основная клавиатура с главными опциями"""
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(text="📋 Узнать об услуге"),
        KeyboardButton(text="💰 Цены"),
    )
    builder.row(
        KeyboardButton(text="📅 Записаться на консультацию"),
        KeyboardButton(text="👨‍💼 Связаться с менеджером"),
    )
    builder.row(
        KeyboardButton(text="❓ Частые вопросы"),
        KeyboardButton(text="ℹ️ О клинике"),
    )
    
    return builder.as_markup(resize_keyboard=True)


def get_services_keyboard(services: list) -> InlineKeyboardMarkup:
    """Клавиатура с выбором услуг"""
    builder = InlineKeyboardBuilder()
    
    for service in services:
        builder.row(
            InlineKeyboardButton(
                text=service.name,
                callback_data=f"service_{service.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_consultation")
    )
    
    return builder.as_markup()


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения записи"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_request"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_consultation")
    )
    
    return builder.as_markup()


def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """Админская клавиатура"""
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(text="📋 Новые заявки"),
        KeyboardButton(text="📊 Статистика"),
    )
    builder.row(
        KeyboardButton(text="📝 Обновить услуги"),
        KeyboardButton(text="📤 Экспорт CSV"),
    )
    builder.row(
        KeyboardButton(text="🔙 В главное меню"),
    )
    
    return builder.as_markup(resize_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой отмены"""
    builder = ReplyKeyboardBuilder()
    
    builder.row(KeyboardButton(text="❌ Отмена"))
    
    return builder.as_markup(resize_keyboard=True)


def get_faq_categories_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура категорий FAQ"""
    builder = InlineKeyboardBuilder()
    
    categories = [
        ("💰 Цены и стоимость", "category_price"),
        ("⏰ Длительность и реабилитация", "category_recovery"),
        ("⚕️ Безопасность и риски", "category_safety"),
        ("📋 Подготовка к операции", "category_preparation"),
        ("🏥 Общие вопросы", "category_general"),
    ]
    
    for text, callback_data in categories:
        builder.row(
            InlineKeyboardButton(text=text, callback_data=callback_data)
        )
    
    builder.row(
        InlineKeyboardButton(text="❌ Закрыть", callback_data="close_faq")
    )
    
    return builder.as_markup()


def get_request_status_keyboard(request_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для управления статусом заявки (админ)"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📞 Связаться", callback_data=f"contact_{request_id}"),
        InlineKeyboardButton(text="📅 Назначить", callback_data=f"appoint_{request_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_{request_id}"),
        InlineKeyboardButton(text="✅ Завершить", callback_data=f"complete_{request_id}"),
    )
    
    return builder.as_markup()
