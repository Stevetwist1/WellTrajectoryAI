
import os
import uuid
import shutil
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TesseractCliOcrOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from services.llm import text_to_llm
from models.directionalsurvey import DirectionalSurvey
import tempfile
from typing import Dict, Any
from main import extract_and_merge_survey
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Directional Survey API",
    description="Extract structured data from oil and gas directional survey",
    version="1.0.0"
)

@app.post("/extract", response_model=Dict[str, Any])
async def extract_plat_data(file: UploadFile = File(...)):
    """
    Extract structured data from a PDF directional survey document.
    
    Args:
        file: PDF file upload
        
    Returns:
        JSON object containing extracted plat data
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400, 
            detail="Only PDF files are supported"
        )
    
    # Create temporary file to store uploaded PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        try:
            # Write uploaded file to temporary location
            content = await file.read()
            temp_file.write(content)
            temp_pdf_path = temp_file.name
            
            logger.info(f"Processing uploaded file: {file.filename}")

            # Use the new extract_and_merge_survey function for full extraction and merging
            merged_result = extract_and_merge_survey(temp_pdf_path)
            logger.info(f"Successfully processed {file.filename}")
            return JSONResponse(
                content=merged_result,
                status_code=200
            )
            
        except Exception as e:
            logger.error(f"Error processing {file.filename}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error processing PDF: {str(e)}"
            )
        finally:
            # Clean up temporary file
            if os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "PlatMaster API"}

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Directional Survey API",
        "description": "Extract structured data from oil and gas directional survey documents",
        "endpoints": {
            "/extract": "POST - Upload PDF file for data extraction",
            "/health": "GET - Health check",
            "/docs": "GET - Interactive API documentation"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7777)
