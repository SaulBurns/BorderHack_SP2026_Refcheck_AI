# BorderHack_SP2026_Refcheck_AI
AI-powered basketball officiating analysis tool.

## Run backend
cd backend  
python3 -m venv venv  
source venv/bin/activate  
python3 -m pip install -r requirements.txt  
python3 -m uvicorn main:app --reload --port 8000

## Run frontend
cd frontend  
npm install  
npm run dev
