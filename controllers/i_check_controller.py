from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from codescripts.i_check import MemoryManager
from utils.process_agent_params import process_agent_params, get_standard_model_name
from codescripts.text_extractor import ExtractText
from codescripts.optimiser import Optimiser

app = FastAPI()

class GetMemoryRequest(BaseModel):
    user_id: str
    agent: str
    documents: List[str]
    parameters: Dict[str, Any]

class StoreMemoryRequest(BaseModel):
    user_id: str
    agent: str
    documents: List[str]
    parameters: Dict[str, Any]
    provided_response: Dict[str, Any]


@app.post("/get_memory")
async def get_memory(request: GetMemoryRequest):
    """
    Retrieve memory content for a specific agent.
    """
    try:
        user_id = request.user_id
        agent = request.agent
        documents = request.documents
        parameters = request.parameters

        if not user_id or not agent or not documents:
            raise ValueError("User ID or agent or documents are missing")
        
        is_valid_params, processed_params, missing_params = process_agent_params(agent, parameters)

        if not is_valid_params:
            raise ValueError(f"Missing parameters for agent {agent}: {missing_params}")
        doc_hashes = []
        total_extracted_text = ""
        for doc in documents:    
            try:
                print('Extracting Text')
                extracted_text = ExtractText().get_text(doc)
                total_extracted_text += extracted_text
                hashed_text = ExtractText().hash_text(extracted_text)
                doc_hashes.append(hashed_text)

            except Exception as e:
                print(f"Error extracting text: {e}")
                return JSONResponse(
                    {
                        "message": "Error extracting text from file(s)",
                        "data": {}
                    }, status_code = 500)
        print(f"Document hashes: {doc_hashes}")
        memory_content = MemoryManager().get_memory_content(user_id, agent, doc_hashes, processed_params)
        model_name = parameters.get("model_name", "gpt-4o")  
        model_name = get_standard_model_name(model_name)

        optimiser = Optimiser(model_name, agent, total_extracted_text)
        if agent == "k_search":
            optimisation_metrics = optimiser.compute(memory_content.get("processing_content", {}),memory_content.get("memory_content", {}), processed_params, i_check_result=memory_content.get("i_check_result", {}))
        else:    
            optimisation_metrics = optimiser.compute(memory_content.get("processing_content", {}),memory_content.get("memory_content", {}), processed_params, i_check_result=None)

        # Inject into response
        memory_content["optimisation"] = optimisation_metrics
        return JSONResponse(
            memory_content,
            status_code=200
        )
    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse(
            {"message": "Error in retrieving memory: " + str(e)},
            status_code=500
        )

@app.post("/save_memory")
async def save_memory(request: StoreMemoryRequest):
    """
    Save memory content for a specific agent.
    """
    try:
        user_id = request.user_id
        agent = request.agent
        documents = request.documents
        parameters = request.parameters
        provided_response = request.provided_response

        if not user_id or not agent or not documents or not provided_response:
            raise ValueError("User ID or agent or documents or response are missing")
        
        is_valid_params, processed_params, missing_params = process_agent_params(agent, parameters)

        if not is_valid_params:
            raise ValueError(f"Missing parameters for agent {agent}: {missing_params}")

        doc_hashes = []
        for doc in documents:    
            try:
                print('Extracting Text')
                extracted_text = ExtractText().get_text(doc)
                hashed_text = ExtractText().hash_text(extracted_text)
                doc_hashes.append(hashed_text)

            except Exception as e:
                print(f"Error extracting text: {e}")
                return JSONResponse(
                    {
                        "message": "Error extracting text from file(s)",
                        "data": {}
                    }, status_code = 500)
        print(f"Document hashes: {doc_hashes}")

        memory_content = MemoryManager().save_memory_content(user_id, agent, doc_hashes, processed_params, provided_response)
        
        return JSONResponse(
            {
                "message": str(memory_content)
            },
            status_code=200
        )
    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse(
            {"message": "Error in saving memory: " + str(e)},
            status_code=500
        )