from VPNBot.state_manager import StateManager

def test_push_and_get_state():
    """Проверяет добавление и получение элемента из стека у пользователя"""
    sm = StateManager()
    sm.push_state(1, "main")
    assert sm.get_state(1) == "main"

def test_push_multiple_states_and_pop():
    """Проверяет несколько (два) добавлений и получение элемента из стека у пользователя"""
    sm = StateManager()
    sm.push_state(1, "main")
    sm.push_state(1, "buy")
    assert sm.get_state(1) == "buy"
    sm.pop_state(1)
    assert sm.get_state(1) == "main"

def test_pop_empty_stack_returns_none():
    """Проверяет правильность удаления и получения элемента из стека"""
    sm = StateManager()
    assert sm.pop_state(1) is None
    assert sm.get_state(1) is None