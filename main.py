import os
import stripe
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Osorio Contadores y Asociados - RESICO SaaS API")

# Configuración de credenciales de Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Configuración del servicio de Declaración Mensual RESICO ($85 USD)
RESICO_SERVICE_TITLE = "Elaboración de Declaración Mensual RESICO"
RESICO_SERVICE_COST = "$85.00 USD"
RESICO_PRICE_ID = os.getenv("STRIPE_RESICO_PRICE_ID", "price_dummy_resico_usd")


class CheckoutSessionRequest(BaseModel):
    customer_email: str
    target_month: str  # Ej: "Enero 2026"
    success_url: str
    cancel_url: str


@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Osorio Contadores y Asociados - RESICO API",
        "description": "Automatización de pagos y recepción para declaración mensual RESICO",
    }


@app.post("/create-checkout-session")
def create_checkout_session(data: CheckoutSessionRequest):
    """Genera el enlace de pago en Stripe por $85 USD para la

    elaboración de la declaración mensual de RESICO del periodo seleccionado.
    """
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price": RESICO_PRICE_ID,
                    "quantity": 1,
                }
            ],
            mode="payment",  # Pago único por la declaración mensual
            customer_email=data.customer_email,
            metadata={
                "service_name": RESICO_SERVICE_TITLE,
                "target_month": data.target_month,
                "service_cost": RESICO_SERVICE_COST,
            },
            success_url=data.success_url,
            cancel_url=data.cancel_url,
        )
        return {
            "checkout_url": checkout_session.url,
            "target_month": data.target_month,
            "cost": RESICO_SERVICE_COST,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Webhook de Stripe que verifica el pago exitoso de los $85 USD

    para la declaración mensual de RESICO y activa la solicitud de datos.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Payload inválido de Stripe"
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(
            status_code=400, detail="Firma de webhook inválida en Stripe"
        )

    # Validar que el pago se haya completado exitosamente
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        
        # Validación de seguridad: Asegurar que el estatus de pago sea 'paid'
        if session.get("payment_status") == "paid":
            customer_email = session.get("customer_email")
            customer_name = session.get("customer_details", {}).get(
                "name", "Estimado contribuyente"
            )

            metadata = session.get("metadata", {})
            target_month = metadata.get("target_month", "Periodo actual")
            service_cost = metadata.get("service_cost", RESICO_SERVICE_COST)
            service_name = metadata.get("service_name", RESICO_SERVICE_TITLE)

            if customer_email:
                send_tax_onboarding_email(
                    customer_email, customer_name, target_month, service_cost, service_name
                )

    return {"status": "success"}


def send_tax_onboarding_email(
    to_email: str, client_name: str, target_month: str, service_cost: str, service_name: str
):
    """Envía el correo electrónico automatizado notificando el pago de $85 USD

    y solicitando los archivos XML, CIEC y e.firma para la declaración RESICO.
    """
    # Aquí puedes reemplazar el print con tu integración de API de correo (ej. SendGrid o Resend)
    print(f"\n==================================================")
    print(f"CORREO AUTOMÁTICO DE OSOPIO CONTADORES PARA: {to_email}")
    print(f"==================================================")
    print(f"Estimado/a {client_name},")
    print(f"Hemos confirmado de recibido tu pago por concepto de: {service_name}.")
    print(f"Periodo fiscal a declarar: {target_month}.")
    print(f"Monto total cubierto: {service_cost}.\n")
    print("--- REQUISITOS OBLIGATORIOS PARA TU DECLARACIÓN EN EL SAT ---")
    print("Por favor, responde directamente a este correo adjuntando:")
    print("1. Tus archivos XML de ingresos y gastos del mes correspondiente.")
    print("2. Tu clave CIEC actualizada del SAT.")
    print("3. Tus archivos de la e.firma (en caso de requerirse).")
    print("\nEn cuanto recibamos tu información, procederemos a elaborar tu cálculo en el portal del SAT")
    print("y te enviaremos tu Acuse de Presentación junto con tu Línea de Captura.")
    print("\nNota: Para dudas adicionales o seguimiento operativo, cuentas con nuestro canal de WhatsApp.")
    print(f"==================================================\n")


@app.post("/notify-whatsapp-support")
def notify_whatsapp_support(phone_number: str, message: str):
    """Generador de enlace de WhatsApp para soporte posterior al pago."""
    whatsapp_url = f"https://wa.me/{phone_number}?text={message}"
    return {
        "status": "ready",
        "whatsapp_followup_link": whatsapp_url,
        "note": "Canal exclusivo para seguimiento y soporte operativo posterior al pago.",
    }