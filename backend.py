from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import HTTPException
import os
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware # type: ignore
GEMINI_API_KEY = "AIzaSyCadfER6pugEk0e16UtaKFxZXq-4ZDn9kY"
app = FastAPI()

# Allow CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

UPLOAD_DIR = "uploaded_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)


import os
import base64
from dotenv import load_dotenv
load_dotenv()
import base64
import random
import requests

# Convert image to base64
def image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

# Function to describe image
def describe_image(image_path: str) -> str:
    
    GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    base64_image = image_to_base64(image_path)

    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",  # or image/png
                            "data": base64_image
                        }
                    },
                    {
                        "text": "shortly Describe the person or object in image with expression and describe the image as well no need to do markup"
                    }
                ]
            }
        ]
    }

    # Send the POST request using requests
    response = requests.post(GEMINI_URL, headers=headers, params=params, json=payload)

    if response.status_code != 200:
        return f"❌ Error {response.status_code}: {response.text}"

    data = response.json()
    return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response")

def generate_text_from_prompt(prompt: str) -> str:
    GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent"

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }

    response = requests.post(GEMINI_URL, headers=headers, json=payload)

    if response.status_code != 200:
        return f"❌ Error {response.status_code}: {response.text}"

    data = response.json()
    return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response")

def gemini_image_edit(image_path: str, prompt: str, output_path: str = "gemini_edited_image.png") -> str:
    GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-preview-image-generation:generateContent"

    # Convert image to base64
    with open(image_path, "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",  # or image/png
                            "data": image_base64
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"]
        }
    }

    response = requests.post(GEMINI_URL, headers=headers, json=payload)

    if response.status_code != 200:
        return f"❌ Error {response.status_code}: {response.text}"

    data = response.json()
    # print(data)
    # Extract base64 image data
    try:
        image_base64_response  = data["candidates"][0]["content"]["parts"][1]["inlineData"]["data"]
    except (KeyError, IndexError):
        return "❌ Image response not found in the response."

    # Decode and save the image
    with open(output_path, "wb") as out_file:
        out_file.write(base64.b64decode(image_base64_response))

    return output_path.split("/")[-1]  # Return the filename

@app.post("/upload_image")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        return JSONResponse(status_code=400, content={"error": "Only image files are allowed."})

    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as image:
        content = await file.read()
        image.write(content)
    description = describe_image(file_path)
    print(f"Image description: {description}")
    banana = generate_text_from_prompt("Generate a pazhamcholl in malayalam for: " + description + 'send only the pazhamcholl without any other text')
    print(f"Generated pazhamcholl: {banana}")
    new_image = gemini_image_edit(file_path, f'based on the image and the pazhamcholl:{banana} create a cartoonistic image', output_path=os.path.join(UPLOAD_DIR, "edited_" + filename))
    print(f"New image path: {new_image}")
    return {"message": "Image uploaded successfully!", "description": description, "banana": banana, "filename": filename, "new_image": new_image}


# static
@app.get("/static/{filename}")
async def get_static_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

@app.get("/")
async def get_index():
    file_path = os.path.join(os.getcwd(), "pazhacholl.html")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)