import os
import json
import pdfplumber
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TesseractCliOcrOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from services.llm import text_to_llm
from models.directionalsurvey import DirectionalSurvey


import sys

def process_pdf(pdf_path):
    document_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_dir = f"output/{document_name}"
    drawings_dir = os.path.join(output_dir, "drawings")
    os.makedirs(drawings_dir, exist_ok=True)

    pipeline_options = PdfPipelineOptions(
        do_ocr=True,
        do_table_structure=True,
        table_structure_options=dict(do_cell_matching=True)
    )
    ocr_options = TesseractCliOcrOptions(force_full_page_ocr=True)
    pipeline_options.ocr_options = ocr_options

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    print(f"🔄 Converting PDF {pdf_path} with Docling...")
    result = converter.convert(pdf_path)

    plat_markdown = result.document.export_to_markdown()
    md_file_path = os.path.join(output_dir, f"{document_name}.md")
    with open(md_file_path, "w") as md_file:
        md_file.write(plat_markdown)
    print(f"✅ Markdown saved: {md_file_path}")

    print("🤖 Processing text with LLM...")
    DirectionalSurveyObj = text_to_llm(
        llm_model="gpt-4.1",
        feature_model=DirectionalSurvey,
        document_text=plat_markdown
    )

    survey_json = DirectionalSurveyObj.model_dump()

    print("🖼️ Extracting drawings and OCR labels...")
    drawing_data = []

    with pdfplumber.open(pdf_path) as pdf:
        for idx, pic in enumerate(result.document.pictures, start=1):
            page_no = pic.prov[0].page_no
            bbox = pic.prov[0].bbox
            img_id = f"page{page_no}_pic{idx}"
            img_path = os.path.join(drawings_dir, f"{img_id}.png")

            try:
                pdf_page = pdf.pages[page_no - 1]  # 0-based indexing
                crop_box = (bbox.l, bbox.b, bbox.r, bbox.t)
                region = pdf_page.within_bbox(crop_box)

                img = region.to_image(resolution=300).original
                img.save(img_path)
                print(f"✅ Saved drawing: {img_id}")

                words = region.extract_words()
                ocr_text_blocks = [
                    {
                        "text": word["text"],
                        "bbox": {
                            "x0": word["x0"],
                            "top": word["top"],
                            "x1": word["x1"],
                            "bottom": word["bottom"]
                        }
                    }
                    for word in words
                ]

                drawing_data.append({
                    "page": page_no,
                    "picture_index": idx,
                    "drawing_id": img_id,
                    "file": img_path,
                    "bbox": bbox.to_dict(),
                    "ocr_labels": ocr_text_blocks
                })
            except Exception as e:
                print(f"❌ Failed to extract drawing {img_id}: {e}")
                continue

    survey_json["drawings"] = drawing_data

    json_file_path = os.path.join(output_dir, f"{document_name}.json")
    with open(json_file_path, "w") as json_file:
        json.dump(survey_json, json_file, indent=4)
    print(f"✅ JSON saved: {json_file_path}")

    print("🎉 PlatMaster processing complete.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python plat_service.py <pdf_path>")
        sys.exit(1)
    pdf_path = sys.argv[1]
    process_pdf(pdf_path)