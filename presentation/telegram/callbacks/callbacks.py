from aiogram.filters.callback_data import CallbackData

import domain.enums as enums

# Тарифы, покупка
class PlansCallback(CallbackData, prefix="plans"):
    action: enums.PaymentAction
    key_id: int | None = None

class PurchasePendingCallback(CallbackData, prefix="purchase_pending"):
    action: enums.PaymentAction
    plan_id: int
    key_id: int | None = None

class CancelPaymentCallback(CallbackData, prefix="cancel_payment"):
    payment_id: int

class PurchaseSuccessCallback(CallbackData, prefix="purchase_success"):
    action: enums.PaymentAction
    payment_id: int
    key_id: int | None = None

class SelectedKeyCallback(CallbackData, prefix="selected_key"):
    key_id: int

# Пробный период
class ExtendTrialCallback(CallbackData, prefix="extend_trial"):
    key_id: int

# Мои ключи
class ConfirmDeleteKeyCallback(CallbackData, prefix="confirm_delete_key"):
    key_id: int

class DeleteKeyCallback(CallbackData, prefix="delete_key"):
    key_id: int