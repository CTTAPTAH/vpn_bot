from aiogram.fsm.state import State, StatesGroup

class SupportStates(StatesGroup):
    main = State()
    faq = State()
    my_request = State()
    writing = State()