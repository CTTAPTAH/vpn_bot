from VPNBot import callbacks

def test_unique_callback_values():
    """Проверка на то, что все callback значения уникальны"""
    values = [v for k, v in vars(callbacks).items() if k.isupper()]
    assert len(values) == len(set(values)), "callback_data значения должны быть уникальными"

def test_callbacks_not_empty():
    """Проверка на то, что все callback значения не являются пустыми строками"""
    values = [v for k, v in vars(callbacks).items() if k.isupper()]
    assert all(values), "callback_data не должны быть пустыми строками"