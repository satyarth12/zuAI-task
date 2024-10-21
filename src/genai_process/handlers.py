from dataclasses import dataclass, field
from typing import Any, Dict, Union

import google.generativeai as genai
from google.generativeai import GenerativeModel

from server import LOGGER, server_settings
from src.sample_paper.schema import SamplePaper


@dataclass
class GeminiHandler:
    model_name: str = field(default="gemini-1.5-pro")
    model: GenerativeModel = field(init=False)

    def __post_init__(self):
        genai.configure(api_key=server_settings.GEMINI_API_KEY)
        self.model = GenerativeModel(self.model_name)

    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        import json

        try:
            response_text = response_text.replace("```json", "").replace("```", "")
            return json.loads(response_text)
        except json.JSONDecodeError:
            LOGGER.error("Failed to parse Gemini response as JSON")
            return {
                "title": "Parsing Error",
                "type": "error",
                "time": 0,
                "marks": 0,
                "params": {"board": "", "grade": 0, "subject": ""},
                "tags": [],
                "chapters": [],
                "sections": [],
            }

    def _process_content(self, content: Union[str, Any]) -> SamplePaper:
        prompt = """
        Analyze the given content and extract the following information to create a structured JSON format for a sample paper. Use the exact format provided below:

        {
            "title": "string",
            "type": "string",
            "time": int,
            "marks": int,
            "params": {
                "board": "string",
                "grade": int,
                "subject": "string"
            },
            "tags": ["string"],
            "chapters": ["string"],
            "sections": [
                {
                    "marks_per_question": int,
                    "type": "string",
                    "questions": [
                        {
                            "question": "string",
                            "answer": "string",
                            "type": "string",
                            "question_slug": "string",
                            "reference_id": "string",
                            "hint": "string",
                            "params": {}
                        }
                    ]
                }
            ]
        }

        Instructions:
        1. Title: Extract the main title of the sample paper.
        2. Type: Determine the type of the sample paper (e.g., "previous_year", "practice", etc.).
        3. Time: Extract the total time allowed for the paper in minutes.
        4. Marks: Extract the total marks for the paper.
        5. Params: Identify the board (eg., "CBSE", "ICSE", "IB"), grade, and subject of the paper.
        6. Tags: List relevant tags for the paper content.
        7. Chapters: List the chapters covered in the paper.
        8. Sections: For each section of the paper:
           - Determine the marks per question
           - Identify the type of the section
           - For each question in the section:
             * Extract the question text
             * Provide the answer if available
             * Determine the question type (e.g., "short", "long", "mcq")
             * Generate a suitable question_slug
             * Assign a reference_id
             * Provide a hint if possible
             * Include any additional parameters in the params object

        Ensure that all JSON keys and values are properly formatted and escaped. If any information is not available, use null or an empty string/array as appropriate.
        """

        response = self.model.generate_content([prompt, content])
        sample_paper_dict = self._parse_gemini_response(response.text)
        return SamplePaper(**sample_paper_dict)

    def process_pdf(self, file_path: str) -> SamplePaper:
        try:
            uploaded_file = genai.upload_file(file_path)
            return self._process_content(uploaded_file)
        except Exception as e:
            LOGGER.error(f"Error processing PDF with Gemini: {str(e)}")
            raise

    def process_text(self, text_content: str) -> SamplePaper:
        try:
            return self._process_content(text_content)
        except Exception as e:
            LOGGER.error(f"Error processing text with Gemini: {str(e)}")
            raise


if __name__ == "__main__":
    import asyncio

    async def main():
        gemini_handler = GeminiHandler()

        # Process PDF
        pdf_result = gemini_handler.process_pdf("sample_paper.pdf")
        print("PDF Processing Result:", pdf_result)

        # Process Text
        sample_text = "This is a sample paper for CBSE Class 10 Mathematics..."
        text_result = gemini_handler.process_text(sample_text)
        print("Text Processing Result:", text_result)

    asyncio.run(main())
