from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import our custom services
# Note: These will initialize the models when the server starts (might take 10-20s)
from llm_service import generate_quiz
from parser_service import extract_text_from_image

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TextRequest(BaseModel):
    text: str

@app.get("/")
def read_root():
    return {"status": "EduSync AI Core Online"}

# --- Endpoint 1: Upload Image -> Get Text (OCR) ---
@app.post("/extract-text")
async def extract_text(file: UploadFile = File(...)):
    contents = await file.read()
    extracted_text = extract_text_from_image(contents)
    return {"extracted_text": extracted_text}

# --- Endpoint 2: Send Text -> Get Quiz (LLM) ---
@app.post("/generate-quiz")
def create_quiz(request: TextRequest):
    quiz_json = generate_quiz(request.text)
    return {"quiz": quiz_json}