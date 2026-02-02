from aiogram.fsm.state import State, StatesGroup


class ConsultationStates(StatesGroup):
    """Состояния для записи на консультацию"""
    
    choosing_service = State()  # Выбор услуги
    entering_name = State()     # Ввод имени
    entering_phone = State()    # Ввод телефона
    entering_date = State()     # Ввод предпочтительной даты
    entering_comment = State()  # Ввод комментария
