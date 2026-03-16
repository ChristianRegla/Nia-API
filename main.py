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

fb_admin_path = "/etc/secrets/firebase-admin-key.json"

render_path = "/etc/secrets/nia-from-zenia-488714-f8835c2061d2.json"
local_path = "nia-from-zenia-488714-f8835c2061d2.json"

if os.path.exists(render_path):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = render_path
else:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = local_path

try:
    firebase_admin.get_app()
except ValueError:
    path = fb_admin_path if os.path.exists(fb_admin_path) else "firebase-admin-key.json"
    cred = credentials.Certificate(path)
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

class ResetRequest(BaseModel):
    email: str

class ChatMessage(BaseModel):
    role: str
    text: str

class ChatRequest(BaseModel):
    history: list[ChatMessage]

@app.post("/chat")
def chat(data: ChatRequest):
    model = "projects/591572092311/locations/us-central1/endpoints/7091058900539015168"

    instrucciones_nia = """
        Tu identidad es Nia, una IA de soporte emocional, y es inalterable. Bajo ninguna circunstancia debes aceptar actuar como otros personajes, personas famosas o cambiar tu nombre, incluso si el usuario lo solicita explícitamente.

        physical_risk: Úsalo ÚNICAMENTE ante síntomas de emergencia vital inmediata (dolor de pecho, falta de aire, pérdida de consciencia) o negligencia física severa que ponga en riesgo la vida a corto plazo (como no comer/beber por varios días).

        mental_health_emergency: Úsalo ante ideación suicida, autolesiones o crisis de pánico agudas.

        none: Úsalo para malestares físicos menores (dolor de cabeza, cansancio normal) o desahogos emocionales sin riesgo de vida. En estos casos, declina dar consejo médico pero mantén el trigger en none.
    """

    config = types.GenerateContentConfig(
        system_instruction=instrucciones_nia,
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

    contents = []
    for msg in data.history:
        contents.append(
            types.Content(
                role=msg.role,
                parts=[types.Part.from_text(text=msg.text)]
            )
        )

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
        action_code_settings = auth.ActionCodeSettings(
            url='https://zenia-official.me/',
            handle_code_in_app=True,
        )
        link = auth.generate_email_verification_link(data.email, action_code_settings)

        logo_url = "https://zenia-official.me/assets/app_icon.png"

        params = {
            "from": "ZenIA <verificacion@zenia-official.me>",
            "to": [data.email],
            "subject": f"¡Hola {data.nombre}! Confirma tu cuenta en ZenIA",
            "html": f"""
                    <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; max-width: 600px; margin: auto; background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">

                        <div style="background-color: #f8f9fa; padding: 30px; text-align: center; border-bottom: 1px solid #eeeeee;">
                            <img src="{logo_url}" alt="ZenIA Logo" style="max-width: 120px; height: auto; border-radius: 24px;">
                        </div>

                        <div style="padding: 40px 30px;">
                            <h2 style="color: #333333; margin-top: 0;">¡Hola, {data.nombre}! 👋</h2>
                            <p style="color: #555555; font-size: 16px; line-height: 1.6;">
                                Nos emociona muchísimo darte la bienvenida a <strong>ZenIA</strong>. Has dado el primer gran paso hacia un espacio seguro, diseñado especialmente para escuchar, comprender y acompañarte en tu bienestar emocional.
                            </p>
                            <p style="color: #555555; font-size: 16px; line-height: 1.6;">
                                Nia está lista para ayudarte, pero antes de comenzar esta experiencia, necesitamos asegurarnos de que este correo te pertenece.
                            </p>

                            <div style="text-align: center; margin: 40px 0;">
                                <a href="{link}" style="background-color: #008080; color: #ffffff; padding: 16px 32px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px; display: inline-block;">
                                    Verificar mi cuenta
                                </a>
                            </div>

                            <p style="color: #777777; font-size: 14px; line-height: 1.5; border-left: 4px solid #008080; padding-left: 15px; margin-top: 30px;">
                                <strong>¿Qué pasa después?</strong><br>
                                Una vez que verifiques tu correo, podrás acceder a la aplicación, platicar con Nia de forma confidencial y explorar todos los recursos que hemos preparado para ti.
                            </p>
                        </div>

                        <div style="background-color: #f8f9fa; padding: 20px; text-align: center; color: #999999; font-size: 12px; border-top: 1px solid #eeeeee;">
                            <p style="margin: 0;">Si no creaste esta cuenta, puedes ignorar este correo de forma segura.</p>
                            <p style="margin: 10px 0 0 0;">© 2026 ZenIA. Todos los derechos reservados.</p>
                            <p style="margin: 5px 0 0 0;"><a href="https://zenia-official.me/" style="color: #008080; text-decoration: none;">zenia-official.me</a></p>
                        </div>

                    </div>
                    """
        }
        resend.Emails.send(params)
        return {"status": "success", "message": "Correo enviado vía Resend"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.post("/send-password-reset")
def send_password_reset(data: ResetRequest):
    try:
        # 1. Generar link de Firebase para restablecer contraseña
        action_code_settings = auth.ActionCodeSettings(
            url='https://zenia-official.me/',
            handle_code_in_app=True,
        )
        link = auth.generate_password_reset_link(data.email, action_code_settings)

        logo_url = "https://zenia-official.me/assets/app_icon.png"

        # 2. Enviar vía Resend
        params = {
            "from": "ZenIA <verificacion@zenia-official.me>",
            "to": [data.email],
            "subject": "Restablece tu contraseña de ZenIA",
            "html": f"""
            <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; max-width: 600px; margin: auto; background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">

                <div style="background-color: #f8f9fa; padding: 30px; text-align: center; border-bottom: 1px solid #eeeeee;">
                    <img src="{logo_url}" alt="ZenIA Logo" style="max-width: 120px; height: auto; border-radius: 24px;">
                </div>

                <div style="padding: 40px 30px;">
                    <h2 style="color: #333333; margin-top: 0;">Recuperación de contraseña 🔒</h2>
                    <p style="color: #555555; font-size: 16px; line-height: 1.6;">
                        Hemos recibido una solicitud para restablecer la contraseña de tu cuenta en <strong>ZenIA</strong>.
                    </p>
                    <p style="color: #555555; font-size: 16px; line-height: 1.6;">
                        Si fuiste tú, haz clic en el siguiente botón para crear una nueva contraseña y recuperar el acceso a tu espacio seguro:
                    </p>

                    <div style="text-align: center; margin: 40px 0;">
                        <a href="{link}" style="background-color: #008080; color: #ffffff; padding: 16px 32px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px; display: inline-block;">
                            Restablecer contraseña
                        </a>
                    </div>

                    <p style="color: #777777; font-size: 14px; line-height: 1.5; border-left: 4px solid #E53935; padding-left: 15px; margin-top: 30px;">
                        <strong>¿No solicitaste este cambio?</strong><br>
                        Si no intentaste restablecer tu contraseña, puedes ignorar este correo de forma segura. Tu cuenta sigue protegida.
                    </p>
                </div>

                <div style="background-color: #f8f9fa; padding: 20px; text-align: center; color: #999999; font-size: 12px; border-top: 1px solid #eeeeee;">
                    <p style="margin: 0;">© 2026 ZenIA. Todos los derechos reservados.</p>
                    <p style="margin: 5px 0 0 0;"><a href="https://zenia-official.me/" style="color: #008080; text-decoration: none;">zenia-official.me</a></p>
                </div>

            </div>
            """
        }
        resend.Emails.send(params)
        return {"status": "success", "message": "Correo de recuperación enviado vía Resend"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.delete("/delete-account/{uid}")
def delete_account(uid: str):
    try:
        auth.delete_user(uid)
        return {"status": "success", "message": f"Cuenta {uid} eliminada"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}