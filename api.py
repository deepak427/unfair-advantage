from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from config.settings import settings
from agent.agent import create_root_agent

app = FastAPI(title="Dynamic Agentic Book API")

class ChatRequest(BaseModel):
    message: str
    book: str

class ChatResponse(BaseModel):
    response: str
    book: str

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    book_key = request.book.lower()
    
    # 1. Instantiate the agent dynamically based on the requested book
    root_agent = create_root_agent(book_key)
    
    if not root_agent:
        raise HTTPException(status_code=500, detail=f"Failed to create agent for book: {book_key}")
    
    # 2. Run the agent natively passing the message dict
    # Adk expects run(message) where message can be a dict
    msg = {
        "role": "user",
        "parts": [{"text": request.message}]
    }
    
    try:
        # Pass standard dict to ADK LlmAgent
        result = root_agent.run(msg)
        answer = result.get("output", {}).get("final_answer", "")
        # fallback if somehow different output key
        if not answer:
            answer = str(result)
            
        return ChatResponse(response=answer, book=book_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.app_port)
