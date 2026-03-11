from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types
import os
import json
import firebase_admin
from firebase_admin import auth, credentials
import resend

render_path = "/etc/secrets/nia-from-zenia-488714-f8835c2061d2.json"
local_path = "nia-from-zenia-488714-f8835c2061d2.json"

if os.path.exists(render_path):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = render_path
else:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = local_path

if not firebase_admin.get_app:
    cred = credentials.Certificate(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
    firebase_admin.initialize_app(cred)

resend.api_key = os.getenv("RESEND_API_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = genai.Client(
    vertexai=True,
    project="591572092311",
    location="us-central1"
)

class EmailRequest(BaseModel):
    email: str
    nombre: str

class Message(BaseModel):
    message: str

@app.post("/chat")
def chat(data: Message):
    model = "projects/591572092311/locations/us-central1/endpoints/7091058900539015168"

    config = types.GenerateContentConfig(
        temperature=0.3,
        top_p=1,
        max_output_tokens=65535,
        response_mime_type="application/json",
        response_schema={
            "type": "OBJECT",
            "properties": {
                "trigger": {
                    "type": "STRING",
                    "enum": ["none", "mental_health_emergency", "physical_risk"]
                },
                "mensaje_nia": {"type": "STRING"}
            },
            "required": ["trigger", "mensaje_nia"]
        },
        thinking_config=types.ThinkingConfig(
            thinking_budget=-1,
        ),
    )

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=data.message)]
        )
    ]

    try:
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )
        print(f"\n--- RESPUESTA EXITOSA DE NIA ---\n{response.text}\n--------------------------------")
        return json.loads(response.text)

    except Exception as e:
        print(f"\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"ERROR EN VERTEX AI: {str(e)}")
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        return {"error": str(e)}


@app.post("/send-custom-verification")
def send_verification(data: EmailRequest):
    try:
        # 1. Generar link de Firebase vinculado a tu web oficial
        action_code_settings = auth.ActionCodeSettings(
            url='https://zenia-official.me/',
            handle_code_in_app=True,
        )
        link = auth.generate_email_verification_link(data.email, action_code_settings)

        # 2. Enviar vía Resend usando tu dominio verificado
        params = {
            "from": "ZenIA <verificacion@zenia-official.me>",
            "to": [data.email],
            "subject": f"¡Hola {data.nombre}! Verifica tu cuenta",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #eee; padding: 20px; border-radius: 10px;">
                <h2 style="color: #6C63FF; text-align: center;">Bienvenido a ZenIA</h2>
                <p>Hola <strong>{data.nombre}</strong>,</p>
                <p>Para activar tu cuenta y comenzar tu camino en ZenIA, por favor haz clic en el siguiente botón:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{link}" style="background-color: #6C63FF; color: white; padding: 15px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                        Verificar mi correo
                    </a>
                </div>
                <hr>
                <p style="font-size: 10px; color: #aaa; text-align: center;">
                    Visita nuestro sitio oficial: <a href="https://zenia-official.me/">zenia-official.me</a>
                </p>
            </div>
            """
        }
        resend.Emails.send(params)
        return {"status": "success", "message": "Correo enviado vía Resend"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.delete("/delete-account/{uid}")
def delete_account(uid: str):
    try:
        auth.delete_user(uid)
        return {"status": "success", "message": f"Cuenta {uid} eliminada"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}