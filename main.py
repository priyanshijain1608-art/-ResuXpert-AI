import os
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Loading environment variables from .env file
load_dotenv()

app = FastAPI(
    title="ResuXpert API",
    description="AI-Powered Resume Parsing and Optimization Engine for Google STEP"
)

# Reading frontend URL from environment file (Fallback to * for safety if empty)
origin = os.getenv("ORIGIN", "*")

# Enable CORS safely using the environment variable
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows any local frontend port to connect
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize the official Google GenAI client (Natively picks up GEMINI_API_KEY from environment)
try:
    client = genai.Client()
except Exception as e:
    print(f"Warning: Gemini Client initialization failed. Error: {e}")
    client = None

# --- PYDANTIC SCHEMAS ---
class ResumeOptimizationRequest(BaseModel):
    raw_resume_text: str = Field(..., min_length=20, description="The text content of your current resume")
    target_job_description: str = Field(..., min_length=20, description="The job posting text you want to target")

class OptimizedBulletPoint(BaseModel):
    original: str
    optimized: str
    explanation: str = Field(..., description="Why this change aligns with the Google X-Y-Z formula")

class OptimizationResponse(BaseModel):
    summary_of_gaps: str = Field(..., description="Overall analysis of missing skills or keywords")
    optimized_bullets: list[OptimizedBulletPoint]
    recommended_skills_to_add: list[str]

# --- ENDPOINTS ---
@app.get("/")
def read_root():
    return {"status": "online", "message": "Welcome to the ResuXpert AI Engine"}

@app.post(
    "/api/v1/optimize", 
    response_model=OptimizationResponse, 
    status_code=status.HTTP_200_OK
)
async def optimize_resume(payload: ResumeOptimizationRequest):
    if not client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gemini API Client is not configured. Please set the GEMINI_API_KEY environment variable."
        )

    system_prompt = (
        "You are an expert technical resume reviewer specializing in FAANG hiring standards. "
        "Your task is to analyze the user's raw resume text against the provided target job description. "
        "Identify critical skill gaps, rewrite weak resume bullets into high-impact lines using the "
        "Google X-Y-Z formula (Accomplished X, measured by Y, by doing Z), and suggest missing technical keywords."
    )
    
    user_prompt = f"""
    Target Job Description:
    {payload.target_job_description}

    User's Raw Resume Text:
    {payload.raw_resume_text}
    """

    try:
        # UPDATED: Using gemini-3.8-flash as explicitly required by the API service
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=OptimizationResponse, 
                temperature=0.3,
            )
        )
        
        if not response.parsed:
             raise ValueError("Failed to retrieve valid parsed structured JSON schema output from Gemini service model context.")
             
        return response.parsed

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error communicating with Gemini AI Studio service engine: {str(e)}"
        )
