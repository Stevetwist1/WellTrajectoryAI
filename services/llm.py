import json
import os
import logging
import requests
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def text_to_llm(llm_model: str, feature_model: type[BaseModel], document_text: str) -> type[BaseModel]:
    logger.info("Sending text to LLM for processing.")

    if llm_model == "gpt-4.1":
        url = f"https://ul-openai-finetune-dev.openai.azure.com/openai/deployments/{llm_model}/chat/completions?api-version=2024-10-01-preview"

        headers = {
            "Content-Type": "application/json",
            "api-key": os.getenv("AZURE_OPENAI_API_KEY_EAST2")
        }
    else:
        url = f"https://ul-openai-api-dev.openai.azure.com/openai/deployments/{llm_model}/chat/completions?api-version=2024-10-01-preview"

        headers = {
            "Content-Type": "application/json",
            "api-key": os.getenv("AZURE_OPENAI_API_KEY")
        }
    

    data = {
        "messages": [
            {
                "role": "system",
                "content": 
                    "Extract the features from this text. "  
            },
            {
                "role": "user",
                "content": document_text
            }
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "Extraction_Response",  # Add the name field explicitly
                "strict": True,
                "schema": feature_model.model_json_schema()
            }
        },
        "seed": 7779,
        "stream": False
    }

    try:
        response = requests.post(url, headers=headers, json=data)

        if response.status_code != 200:
            logger.error(f"LLM API Error: {response.status_code} - {response.text}")
            raise Exception(response.json())

        response_json = response.json()
        content = response_json.get("choices", [])[0].get("message", {}).get("content", "{}")
        logger.info(f"Raw LLM response content: {content}")
        logger.info("Text processing completed.")
        return feature_model.model_validate_json(content)

    except Exception as e:
        logger.error(f"Error during LLM interaction: {str(e)}")
        raise