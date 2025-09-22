from fastapi import APIRouter
from service.template_matching.class_template import TemplateMatcher

router = APIRouter()
matcher = TemplateMatcher()

@router.get("/template-match")
def run_template_match():
    """
    Run template matching on parsed JSON and return classification result.
    """
    result = matcher.run()
    return {
        "status": "success",
        "document_id": result["document_id"],
        "category": result["category"],
        "subcategory": result["subcategory"],
        "matched_keywords": result["matched_keywords"],
        "saved_to": matcher.output_path
    }
