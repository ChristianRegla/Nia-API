from fastapi import FastAPI
from pydantic import BaseModel
from google import genai
from google.genai import types
import os
import json

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "nia-from-zenia-488714-f8835c2061d2.json"

app = FastAPI()

client = genai.Client(
    vertexai=True,
    project="591572092311",
    location="us-central1"
)


class Message(BaseModel):
    message: str


@app.post("/chat")
def chat(data: Message):
    model_endpoint = "projects/591572092311/locations/us-central1/endpoints/7091058900539015168"

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
            model=model_endpoint,
            contents=contents,
            config=config,
        )

        return json.loads(response.text)

    except Exception as e:
        return {"error": str(e)}