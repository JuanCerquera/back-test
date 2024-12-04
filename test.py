import mercadopago

from app import settings

sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
plan = sdk.plan().get(settings.MERCADO_PAGO_PLAN_ID)
preference = sdk.preference().create({
    "items": [
        {
            "title": "Test",
            "quantity": 1,
            "currency_id": "ARS",
            "unit_price": 10.0
        }
    ]
})