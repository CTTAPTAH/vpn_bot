from aiogram.filters.callback_data import CallbackData

import domain.enums as enums

# Тарифы, покупка
class PlansCallback(CallbackData, prefix="plans"):
    action: enums.PaymentAction
    sub_id: int | None = None

class PurchasePendingCallback(CallbackData, prefix="purchase_pending"):
    action: enums.PaymentAction
    plan_id: int
    sub_id: int | None = None

class PurchaseSuccessCallback(CallbackData, prefix="purchase_success"):
    action: enums.PaymentAction
    payment_id: int
    sub_id: int | None = None