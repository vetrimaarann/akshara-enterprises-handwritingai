"""
Direct function-level test of the 3-layer pipeline:
Layer 1: TrOCR line-wise + EasyOCR fallback
Layer 2: TextBlob post-correction
Layer 3: NLP analysis (sentiment, readability, keywords)

Tests on the actual user-uploaded handwriting image.
"""
import sys
import cv2
import numpy as np
from pathlib import Path

# Import the upgraded pipeline
from app.ocr import extract_handwritten_text_with_meta

async def test_pipeline_on_image(image_path: str):
    """Test full 3-layer pipeline on a handwriting image."""
    print(f"\n{'='*80}")
    print(f"Testing 3-Layer HandwriteAI Pipeline")
    print(f"{'='*80}\n")
    
    # Load image
    print(f"📸 Loading image: {image_path}")
    image = cv2.imread(image_path)
    if image is None:
        print(f"❌ Failed to load image")
        return
    
    h, w = image.shape[:2]
    print(f"   Dimensions: {w}x{h}")
    print(f"   File size: {Path(image_path).stat().st_size / 1024:.1f} KB\n")
    
    # Create mock UploadFile object for testing
    class MockFile:
        def __init__(self, image_array):
            self.content_type = "image/jpeg"
            self.filename = "test.jpg"
            self._array = image_array
            self._read_done = False
        
        async def read(self):
            if self._read_done:
                return b""
            self._read_done = True
            success, buf = cv2.imencode('.jpg', self._array)
            return buf.tobytes() if success else b""
        
        async def seek(self, offset):
            self._read_done = False
    
    mock_file = MockFile(image)
    
    # Test LAYER 1 + 2: OCR + Correction
    print("🧠 LAYER 1 + 2: OCR Engine Selection + Post-Correction")
    print("-" * 80)
    try:
        extracted_text, confidence_score, engine_used, analysis = await extract_handwritten_text_with_meta(mock_file)
        
        print(f"✅ OCR Engine Used: {engine_used}")
        print(f"   Confidence: {confidence_score:.3f}")
        print(f"   Text length: {len(extracted_text)} chars\n")
        
        if extracted_text:
            preview = extracted_text[:150].replace('\n', ' ')
            print(f"📝 Extracted Text Preview:")
            print(f"   {preview}...\n")
        else:
            print(f"⚠️ No text extracted\n")
            return
    
    except Exception as e:
        print(f"❌ OCR Pipeline Error: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return
    
    # Test LAYER 3: NLP Analysis (already included in the response)
    print("🧠 LAYER 3: NLP Analysis (Sentiment, Readability, Keywords)")
    print("-" * 80)
    if analysis:
        print(f"Sentiment: {analysis.get('sentiment', '-')} " +
              f"(polarity: {analysis.get('sentiment_polarity', 0):.3f})")
        print(f"Readability Score (Flesch): {analysis.get('readability_score', '-'):.1f}")
        print(f"Word Count: {analysis.get('word_count', '-')}")
        print(f"Sentence Count: {analysis.get('sentence_count', '-')}")
        print(f"Avg Word Length: {analysis.get('avg_word_length', '-'):.2f}")
        
        keywords = analysis.get('keywords', [])
        if keywords:
            print(f"Top Keywords: {', '.join(keywords[:5])}")
        print()
    else:
        print(f"⚠️ Analysis unavailable\n")
    
    # Full text output
    print("📄 Full Extracted Text:")
    print("-" * 80)
    print(extracted_text)
    print("-" * 80)
    print()
    
    # Summary
    print("✅ PIPELINE TEST COMPLETE")
    print(f"   Engine: {engine_used}")
    print(f"   Confidence: {confidence_score:.1%}")
    print(f"   Extracted: {len(extracted_text)} characters")
    print()


if __name__ == "__main__":
    import asyncio
    
    if len(sys.argv) < 2:
        print("Usage: python test_handwriting_pipeline.py <image_path>")
        print("Example: python test_handwriting_pipeline.py uploads/83e6bc6561c14f0fbe7c288b22d78336.jpeg")
        sys.exit(1)
    
    image_path = sys.argv[1]
    asyncio.run(test_pipeline_on_image(image_path))
