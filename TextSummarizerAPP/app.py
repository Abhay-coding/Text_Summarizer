from fastapi import FastAPI, Request
from pydantic import BaseModel
from transformers import BartForConditionalGeneration, BartTokenizer
import torch
import re 
from fastapi.templating import Jinja2Templates # UI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles


app = FastAPI(title="Text Summarizer App", description="Text Summarization using Bart", version="1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

model = BartForConditionalGeneration.from_pretrained("./saved_summary_model")
tokenizer = BartTokenizer.from_pretrained("./saved_summary_model")


if torch.cuda.is_available():
    device = torch.device("cuda")
else:
    device = torch.device("cpu")

model.to(device)

templates = Jinja2Templates(directory="templates")

class DialogueInput(BaseModel):
    dialogue: str


def clean_data(text):
    text = re.sub(r"\r\n", " ", text) 
    text = re.sub(r"\s+", " ", text) 
    text = re.sub(r"<.*?>", " ", text) 
    text = text.strip().lower()
    return text

def summarize_dialogue(dialogue : str) -> str:
    dialogue = clean_data(dialogue)

    inputs = tokenizer(
        dialogue,
        padding="max_length",
        max_length=512,
        truncation=True,
        return_tensors="pt"
    ).to(device)

    model.to(device)
    targets = model.generate(
        input_ids=inputs["input_ids"],
        attention_mask=inputs["attention_mask"],
        max_length=150,
        num_beams=4,
        early_stopping=True
    )
    
    summary = tokenizer.decode(targets[0], skip_special_tokens=True) # EOS, SEP
    return summary


@app.post("/summarize/")
async def summarize(dialogue_input: DialogueInput):
    summary = summarize_dialogue(dialogue_input.dialogue)
    return {"summary": summary}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {"request": request}
    )