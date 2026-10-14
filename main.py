from fastapi import FastAPI, Request, HTTPException
import stripe
import os

app = FastAPI(title="Osorio Contadores - RESICO Tax API")

# Configura tu llave secreta de Stripe (puedes usar variables de entorno en Render)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "tu_clave_secreta_de_stripe")

@app.get("/")
def read_root():
    return {"status": "online", "message": "Osorio Contadores RESICO API is running."}

@app.post("/calculate-tax")
def calculate_tax(ingresos: float):
    """
    Motor fiscal RESICO 2026: Calcula ISR según la tabla y el IVA (16% general o 8% fronterizo).
    """
    if ingresos <= 25000.0:
        tasa_isr = 0.010
    elif ingresos <= 50000.0:
        tasa_isr = 0.011
    elif ingresos <= 83333.33:
        tasa_isr = 0.015
    elif ingresos <= 308333.33:
        tasa_isr = 0.020
    else:
        tasa_isr = 0.025

    isr_calculado = round(ingresos * tasa_isr, 2)
    iva_calculado = round(ingresos * 0.16, 2) # Ajustable a 0.08 si aplica estímulo fronterizo
    
    return {
        "ingresos_declarados": ingresos,
        "tasa_isr_aplicada": tasa_isr * 100,
        "isr_a_pagar": isr_calculado,
        "iva_16": iva_calculado
    }

@app.post("/webhook-stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    # Aquí procesas el evento de suscripción pagada de $85 USD
    return {"status": "success"}