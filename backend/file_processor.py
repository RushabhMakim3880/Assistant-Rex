import os
import pypdf
import asyncio
from google import genai
from google.genai import types
from PIL import Image
import io

class FileProcessor:
    """
    The 'Visual Cortex' of R.E.X.
    Processes uploaded files (Images, PDFs) to extract meaning and context.
    """
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key)
        # Use Flash for speed in vision tasks
        self.vision_model = "gemini-2.0-flash-exp" 

    async def process_file(self, file_path, file_type):
        """
        Routes the file to the appropriate processor based on type.
        Returns: Analyzed text context.
        """
        if file_type.startswith("image/"):
            return await self._analyze_image(file_path)
        elif file_type == "application/pdf":
            return await self._extract_pdf_text(file_path)
        elif file_type.startswith("text/") or file_path.endswith(".txt") or file_path.endswith(".py") or file_path.endswith(".js"):
            return await self._read_text_file(file_path)
        else:
            return f"[System Note: User uploaded a file of type {file_type}, but I assume it is text.]\n" + await self._read_text_file(file_path)

    async def _analyze_image(self, image_path):
        """
        Uses Gemini Vision to describe the image.
        """
        try:
            print(f"[Visual Cortex] Analyzing image: {image_path}")
            
            # Open image
            image = Image.open(image_path)
            
            prompt = "Analyze this image. If it contains text, extract it verbatim. If it's a screenshot, describe the UI or error. If it's a diagram, explain it. Be concise."
            
            response = await self.client.aio.models.generate_content(
                model=self.vision_model,
                contents=[prompt, image]
            )
            
            return f"[System Note: User uploaded an IMAGE. Analysis Result:]\n{response.text}"
            
        except Exception as e:
            print(f"[Visual Cortex] Image analysis failed: {e}")
            return f"[System Note: Failed to analyze uploaded image. Error: {e}]"

    async def _extract_pdf_text(self, pdf_path):
        """
        Extracts text from PDF using pypdf.
        """
        try:
            print(f"[Visual Cortex] Reading PDF: {pdf_path}")
            text_content = ""
            reader = pypdf.PdfReader(pdf_path)
            for page in reader.pages:
                text_content += page.extract_text() + "\n"
            
            # Truncate if too huge? Gemini Flash has 1M token context, so we are likely fine.
            # But let's keep it reasonable for the "pending context" buffer.
            # If it's massive, we might want to just summarize it? 
            # For now, return raw text.
            return f"[System Note: User uploaded a PDF. Extracted Content:]\n{text_content.strip()}"
            
        except Exception as e:
            print(f"[Visual Cortex] PDF extraction failed: {e}")
            return f"[System Note: Failed to read uploaded PDF. Error: {e}]"

    async def _read_text_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return f"[System Note: User uploaded a Text Document. Content:]\n{content}"
        except Exception as e:
             return f"[System Note: Failed to read uploaded text file. Error: {e}]"
