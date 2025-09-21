import json
import os
import ahocorasick
from typing import Dict, Any, Tuple, List

# Import your dictionaries
from service.template_matching.legal_keywords import (
    INDIAN_LEGAL_DOCUMENT_KEYWORDS,
    CATEGORY_MAPPING,
)


class TemplateMatcher:
    def _init_(
        self,
        input_path="/home/aks_new/documint/ai-backend/data/processed/docai_parsed_20250918_124117.json",
        output_path="data/processed/system/template_match_output.json"
    ):
        self.input_path = input_path
        self.output_path = output_path
        self.keywords = INDIAN_LEGAL_DOCUMENT_KEYWORDS
        self.category_mapping = CATEGORY_MAPPING
        self.automaton = self._build_automaton()

    def _build_automaton(self) -> ahocorasick.Automaton:
        """Build Aho-Corasick automaton for all keywords"""
        A = ahocorasick.Automaton()
        for subcat, kw_list in self.keywords.items():
            for kw in kw_list:
                A.add_word(kw.lower(), (subcat, kw))
        A.make_automaton()
        return A

    def load_input(self) -> Dict[str, Any]:
        """Load parsed document JSON"""
        if not os.path.exists(self.input_path):
            raise FileNotFoundError(f"Input file not found: {self.input_path}")
        with open(self.input_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def match_keywords(self, extracted_text: str) -> Tuple[str, str, List[str]]:
        """Run Aho-Corasick search and return best category & subcategory"""
        text_lower = extracted_text.lower()
        subcat_hits = {}

        for _, (subcat, kw) in self.automaton.iter(text_lower):
            if subcat not in subcat_hits:
                subcat_hits[subcat] = []
            subcat_hits[subcat].append(kw)

        # Aggregate hits into categories
        category_scores = {}
        for major_cat, subcats in self.category_mapping.items():
            score = sum(len(subcat_hits.get(sc, [])) for sc in subcats)
            if score > 0:
                category_scores[major_cat] = score

        if not category_scores:
            return None, None, []

        # Pick best category + subcategory
        best_category = max(category_scores, key=category_scores.get)
        best_subcategory = max(
            subcat_hits, key=lambda sc: len(subcat_hits.get(sc, []))
        )
        matched_keywords = subcat_hits.get(best_subcategory, [])

        return best_category, best_subcategory, matched_keywords

    def run(self) -> Dict[str, Any]:
        """Pipeline: load input → classify → save"""
        raw_data = self.load_input()

        document_id = raw_data.get("metadata", {}).get("document_id")
        extracted_text = raw_data.get("full_text", "")

        best_category, best_subcategory, matched_keywords = self.match_keywords(extracted_text)

        result = {
            "document_id": document_id,
            "category": best_category,
            "subcategory": best_subcategory,
            "matched_keywords": matched_keywords
        }

        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4, ensure_ascii=False)

        return result