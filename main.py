# LangChain compatibility patch for PaddleOCR/PaddleX dependencies
# Must be installed before importing PaddleOCR to handle import redirection
import sys
try:
    import langchain_text_splitters
    # Create module alias to maintain compatibility with legacy import paths
    sys.modules["langchain.text_splitter"] = langchain_text_splitters
    print("[Compat Patch] langchain.text_splitter shim installed in main.py")
except ImportError:
    print("[Compat Patch] langchain-text-splitters not available, skipping text_splitter shim")

try:
    from langchain_core import documents
    sys.modules["langchain.docstore.document"] = documents
    print("[Compat Patch] langchain.docstore.document shim installed in main.py")
except ImportError:
    print("[Compat Patch] langchain-core not available, skipping docstore.document shim")

import cv2
import numpy as np
import os
import json
from services.llm import text_to_llm
from models.directionalsurvey import DirectionalSurvey
from pdf2image import convert_from_path
from paddleocr import PaddleOCR
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

# Initialize PaddleOCR with layout analysis (structure parsing)
# Force CPU mode since no GPU is available
OCR_MODEL = PaddleOCR(
    use_gpu=False,  # Explicitly disable GPU
    device="cpu",   # Force CPU device
    lang="en",
    use_textline_orientation=False,
    use_doc_orientation_classify=False,
    use_doc_unwarping=False
)

def pdf_to_images(pdf_path):
    """Convert PDF pages to a list of PIL images at 300 DPI."""
    return convert_from_path(pdf_path, dpi=300)

def detect_and_ocr(image_pil):
    """
    Detect text regions and run OCR using PaddleOCR's predict method.
    Returns a list of recognized text blocks with their bounding boxes.
    """
    image_np = np.array(image_pil)
    result = OCR_MODEL.predict(image_np)

    text_blocks = []
    
    if len(result) > 0:
        ocr_result = result[0]  # Get the first OCRResult object
        json_result = ocr_result.json
        
        # Extract text results from the JSON structure
        res = json_result.get('res', {})
        rec_texts = res.get('rec_texts', [])
        rec_polys = res.get('rec_polys', [])
        rec_scores = res.get('rec_scores', [])
        
        # Process each detected text
        for i, (text, poly, score) in enumerate(zip(rec_texts, rec_polys, rec_scores)):
            if text and text.strip():
                text_blocks.append((poly, text))
                print(f"[DEBUG] Detected text: '{text}' with confidence {score:.2f}")

    print(f"[DEBUG] Total detected text blocks: {len(text_blocks)}")
    return text_blocks, result

def draw_ocr_boxes(image, ocr_result, output_path, font_scale=0.5, font_thickness=1):
    """
    Draw OCR bounding boxes and text labels on the image.
    :param image: PIL Image
    :param ocr_result: PaddleOCR result (list containing OCRResult objects)
    :param output_path: Path to save the image with boxes
    """
    image_np = np.array(image).copy()

    if len(ocr_result) > 0:
        ocr_data = ocr_result[0]  # Get the first OCRResult object
        json_result = ocr_data.json
        
        # Extract text results from the JSON structure
        res = json_result.get('res', {})
        rec_texts = res.get('rec_texts', [])
        rec_polys = res.get('rec_polys', [])
        rec_scores = res.get('rec_scores', [])
        
        # Process each detected text
        for text, poly, score in zip(rec_texts, rec_polys, rec_scores):
            if text and text.strip():
                points = np.array(poly, dtype=np.int32)  # Polygon coordinates
                
                # Draw bounding box
                cv2.polylines(image_np, [points.reshape((-1, 1, 2))], isClosed=True, color=(0, 255, 0), thickness=2)

                # Put text label near the box
                text_pos = tuple(points[0])
                cv2.putText(
                    image_np,
                    f"{text} ({score:.2f})",
                    text_pos,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale,
                    (255, 0, 0),
                    font_thickness,
                    lineType=cv2.LINE_AA
                )

    # Save the annotated image
    cv2.imwrite(output_path, cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR))
    print(f"[DEBUG] Saved annotated image with OCR boxes at {output_path}")

def merge_text_blocks(text_blocks):
    """Merge all OCR text blocks into a single string."""
    all_text = "\n".join([text for _, text in text_blocks])
    return all_text

def extract_survey_structured(text):
    """Use the directionalsurvey model and LLM service to extract structured JSON data."""
    llm_model = "gpt-4.1"  # or your preferred deployment name
    try:
        return text_to_llm(llm_model, DirectionalSurvey, text)
    except Exception as e:
        print(f"[LLM Extraction Error]: {e}")
        return {}

def main():
    plats_dir = "plats"
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    for filename in os.listdir(plats_dir):
        if not filename.lower().endswith(".pdf"):
            continue
        pdf_path = os.path.join(plats_dir, filename)
        images = pdf_to_images(pdf_path)
        base_name = os.path.splitext(filename)[0]

        all_page_texts = []
        all_survey_points = []
        merged_metadata = {}
        metadata_fields = [
            "uwi", "operator", "vendor", "contact_info", "county", "method", "north_ref",
            "shl_lat", "shl_lon", "shl_x", "shl_y", "bhl_lat", "bhl_lon", "bhl_x", "bhl_y",
            "lease_location", "job_number", "map_system", "geo_datum", "system_datum", "map_zone",
            "ground_level_elevation", "datum_elevation", "date_created"
        ]
        for field in metadata_fields:
            merged_metadata[field] = None

        for idx, img_pil in enumerate(images):
            img_save_path = os.path.join(output_dir, f"{base_name}_page{idx+1}_input.png")
            img_pil.save(img_save_path)

            text_blocks, ocr_result = detect_and_ocr(img_pil)

            # Save image with bounding boxes for debugging
            boxes_preview_path = os.path.join(output_dir, f"{base_name}_page{idx+1}_boxes.png")
            draw_ocr_boxes(img_pil, ocr_result, boxes_preview_path)

            # Merge OCR results
            all_text = merge_text_blocks(text_blocks)
            merged_txt_path = os.path.join(output_dir, f"{base_name}_page{idx+1}_ocr_merged.txt")
            with open(merged_txt_path, "w") as f:
                f.write(all_text)
            all_page_texts.append(all_text)

            print(f"[OCR Result for {filename} page {idx+1}]\n", all_text)
            structured = extract_survey_structured(all_text)
            print(f"[Extracted JSON for {filename} page {idx+1}]\n", structured.model_dump_json() if isinstance(structured, DirectionalSurvey) else structured)

            # Write output JSON
            output_file = os.path.join(output_dir, f"{base_name}_page{idx+1}.json")
            with open(output_file, "w") as f:
                json.dump(structured.model_dump_json(), f, indent=2) if isinstance(structured, DirectionalSurvey) else f.write(str(structured))

            # Merge survey points and metadata
            if isinstance(structured, DirectionalSurvey):
                all_survey_points.extend(structured.survey_points)
                page_metadata = structured.model_dump()
            elif isinstance(structured, dict) and "survey_points" in structured:
                all_survey_points.extend(structured["survey_points"])
                page_metadata = dict(structured)
            else:
                page_metadata = {}
            # For each metadata field, take the first non-empty value
            for field in metadata_fields:
                val = page_metadata.get(field)
                if val not in [None, ""] and merged_metadata[field] in [None, ""]:
                    merged_metadata[field] = val

        # Save merged OCR text for all pages
        merged_text = "\n".join(all_page_texts)
        merged_txt_path = os.path.join(output_dir, f"{base_name}_ocr_merged.txt")
        with open(merged_txt_path, "w") as f:
            f.write(merged_text)
        print(f"[Merged OCR text for {filename}] saved to {merged_txt_path}")

        # Save merged JSON: single dict with merged metadata and all survey points
        merged_metadata = {k: v for k, v in merged_metadata.items() if v not in [None, ""]}
        if all_survey_points:
            merged_metadata["survey_points"] = [sp.model_dump() if hasattr(sp, "model_dump") else sp for sp in all_survey_points]
        merged_json_path = os.path.join(output_dir, f"{base_name}_ocr_merged.json")
        with open(merged_json_path, "w") as f:
            json.dump(merged_metadata, f, indent=2)
        print(f"[Merged JSON for {filename}] saved to {merged_json_path}")

def extract_and_merge_survey(pdf_path, output_dir="output"):
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.basename(pdf_path)
    base_name = os.path.splitext(filename)[0]
    images = pdf_to_images(pdf_path)

    all_page_texts = []
    all_survey_points = []
    merged_metadata = {}
    metadata_fields = [
        "uwi", "operator", "vendor", "contact_info", "county", "method", "north_ref",
        "shl_lat", "shl_lon", "shl_x", "shl_y", "bhl_lat", "bhl_lon", "bhl_x", "bhl_y",
        "lease_location", "job_number", "map_system", "geo_datum", "system_datum", "map_zone",
        "ground_level_elevation", "datum_elevation", "date_created"
    ]
    for field in metadata_fields:
        merged_metadata[field] = None

    for idx, img_pil in enumerate(images):
        img_save_path = os.path.join(output_dir, f"{base_name}_page{idx+1}_input.png")
        img_pil.save(img_save_path)

        text_blocks, ocr_result = detect_and_ocr(img_pil)

        # Save image with bounding boxes for debugging
        boxes_preview_path = os.path.join(output_dir, f"{base_name}_page{idx+1}_boxes.png")
        draw_ocr_boxes(img_pil, ocr_result, boxes_preview_path)

        # Merge OCR results
        all_text = merge_text_blocks(text_blocks)
        merged_txt_path = os.path.join(output_dir, f"{base_name}_page{idx+1}_ocr_merged.txt")
        with open(merged_txt_path, "w") as f:
            f.write(all_text)
        all_page_texts.append(all_text)

        print(f"[OCR Result for {filename} page {idx+1}]\n", all_text)
        structured = extract_survey_structured(all_text)
        print(f"[Extracted JSON for {filename} page {idx+1}]\n", structured.model_dump_json() if isinstance(structured, DirectionalSurvey) else structured)

        # Write output JSON
        output_file = os.path.join(output_dir, f"{base_name}_page{idx+1}.json")
        with open(output_file, "w") as f:
            json.dump(structured.model_dump_json(), f, indent=2) if isinstance(structured, DirectionalSurvey) else f.write(str(structured))

        # Merge survey points and metadata
        if isinstance(structured, DirectionalSurvey):
            all_survey_points.extend(structured.survey_points)
            page_metadata = structured.model_dump()
        elif isinstance(structured, dict) and "survey_points" in structured:
            all_survey_points.extend(structured["survey_points"])
            page_metadata = dict(structured)
        else:
            page_metadata = {}
        # For each metadata field, take the first non-empty value
        for field in metadata_fields:
            val = page_metadata.get(field)
            if val not in [None, ""] and merged_metadata[field] in [None, ""]:
                merged_metadata[field] = val

    # Save merged OCR text for all pages
    merged_text = "\n".join(all_page_texts)
    merged_txt_path = os.path.join(output_dir, f"{base_name}_ocr_merged.txt")
    with open(merged_txt_path, "w") as f:
        f.write(merged_text)
    print(f"[Merged OCR text for {filename}] saved to {merged_txt_path}")

    # Save merged JSON: single dict with merged metadata and all survey points
    merged_metadata = {k: v for k, v in merged_metadata.items() if v not in [None, ""]}
    if all_survey_points:
        merged_metadata["survey_points"] = [sp.model_dump() if hasattr(sp, "model_dump") else sp for sp in all_survey_points]
    merged_json_path = os.path.join(output_dir, f"{base_name}_ocr_merged.json")
    with open(merged_json_path, "w") as f:
        json.dump(merged_metadata, f, indent=2)
    print(f"[Merged JSON for {filename}] saved to {merged_json_path}")
    return merged_metadata

def extract_selected_pages_survey(pages_data, selected_page_indices):
    """
    Extract survey data from selected PDF pages only.
    This function is designed to work with the Dash app's page selection feature.
    
    Args:
        pages_data: List of page data with base64 encoded images
        selected_page_indices: List of page indices to process
    
    Returns:
        merged_metadata: Dictionary with merged metadata and survey points
    """
    from PIL import Image
    import base64
    import io
    
    print(f"[DEBUG] Processing {len(selected_page_indices)} selected pages: {selected_page_indices}")
    
    all_page_texts = []
    all_survey_points = []
    merged_metadata = {}
    metadata_fields = [
        "uwi", "operator", "vendor", "contact_info", "county", "method", "north_ref",
        "shl_lat", "shl_lon", "shl_x", "shl_y", "bhl_lat", "bhl_lon", "bhl_x", "bhl_y",
        "lease_location", "job_number", "map_system", "geo_datum", "system_datum", "map_zone",
        "ground_level_elevation", "datum_elevation", "date_created"
    ]
    for field in metadata_fields:
        merged_metadata[field] = None
    
    # Process only selected pages
    for page_idx in selected_page_indices:
        if page_idx >= len(pages_data):
            print(f"[WARNING] Page index {page_idx} is out of range (max: {len(pages_data)-1})")
            continue
            
        page_data = pages_data[page_idx]
        print(f"[DEBUG] Processing page {page_idx+1}")
        
        # Convert base64 back to PIL image
        img_bytes = base64.b64decode(page_data['base64'])
        img_pil = Image.open(io.BytesIO(img_bytes))
        print(f"[DEBUG] Image size for page {page_idx+1}: {img_pil.size}")
        
        # Use the same OCR processing as main
        text_blocks, ocr_result = detect_and_ocr(img_pil)
        all_text = merge_text_blocks(text_blocks)
        all_page_texts.append(all_text)
        
        print(f"[OCR Result for page {page_idx+1}] ({len(text_blocks)} text blocks)\n{all_text[:500]}...")
        
        # Extract structured data using the same function as main
        structured = extract_survey_structured(all_text)
        print(f"[LLM Result for page {page_idx+1}] Type: {type(structured)}")
        if isinstance(structured, DirectionalSurvey):
            print(f"Survey points found: {len(structured.survey_points)}")
        
        # Merge survey points and metadata (same logic as main)
        if isinstance(structured, DirectionalSurvey):
            all_survey_points.extend(structured.survey_points)
            page_metadata = structured.model_dump()
        elif isinstance(structured, dict) and "survey_points" in structured:
            all_survey_points.extend(structured["survey_points"])
            page_metadata = dict(structured)
        else:
            page_metadata = {}
            print(f"[WARNING] No valid structured data extracted from page {page_idx+1}")
        
        # For each metadata field, take the first non-empty value
        for field in metadata_fields:
            val = page_metadata.get(field)
            if val not in [None, ""] and merged_metadata[field] in [None, ""]:
                merged_metadata[field] = val
    
    # Clean up merged metadata and add survey points (same as main)
    merged_metadata = {k: v for k, v in merged_metadata.items() if v not in [None, ""]}
    if all_survey_points:
        merged_metadata["survey_points"] = [sp.model_dump() if hasattr(sp, "model_dump") else sp for sp in all_survey_points]
    
    print(f"[DEBUG] Final result: {len(all_survey_points)} total survey points, {len(merged_metadata)} metadata fields")
    return merged_metadata

if __name__ == "__main__":
    main()
