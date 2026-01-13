#!/usr/bin/env python3
"""
Phase 1: PDF Text Extraction to JSONL
Pure extraction - NO embedding model, NO chunking logic.
Memory-safe: processes one page at a time, writes immediately.

OCR support:
- Use --ocr to enable OCR when native text extraction is empty.
- Use --ocr-lang to select tesseract language(s), e.g. "eng" or "eng+san".
"""

import sys
import json
from pathlib import Path
from tqdm import tqdm
import fitz  # PyMuPDF
import argparse


def _extract_text_with_ocr(page: "fitz.Page", ocr_lang: str) -> str:
    """Render page to an image and OCR it with tesseract."""
    try:
        import pytesseract
        from PIL import Image
    except Exception as e:
        raise RuntimeError(
            "OCR requested but pytesseract/Pillow not available. Install them in the active venv."
        ) from e

    # Render with decent DPI for OCR
    zoom = 2.0  # ~144 DPI (72 * 2)
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)

    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    text = pytesseract.image_to_string(img, lang=ocr_lang)
    return text or ""


def extract_pdf_to_jsonl(pdf_path: Path, output_jsonl: Path, *, use_ocr: bool = False, ocr_lang: str = "eng"):
    """
    Extract PDF text page-by-page to JSONL format.
    Each line: {"page": N, "file": "...", "text": "..."}

    If use_ocr=True, OCR will be used when native extraction is empty.
    """
    print(f"📄 Phase 1: Extracting text from {pdf_path.name}")
    print(f"📁 Output: {output_jsonl}")
    print("=" * 60)
    
    # Open PDF
    doc = fitz.open(pdf_path)
    total_pages = doc.page_count
    
    print(f"✅ PDF has {total_pages} pages")
    print("🔄 Starting extraction...\n")
    
    # Open output file for writing (streaming mode)
    with open(output_jsonl, 'w', encoding='utf-8') as f:
        # Process with progress bar
        with tqdm(total=total_pages, desc="📄 Extracting pages", 
                 unit="page", colour="green", ncols=100) as pbar:
            
            for page_num in range(total_pages):
                try:
                    page = doc.load_page(page_num)

                    # 1) Try native text extraction first
                    text = page.get_text() or ""

                    # 2) OCR fallback when necessary
                    if use_ocr and not text.strip():
                        text = _extract_text_with_ocr(page, ocr_lang)

                    if text.strip():
                        line = json.dumps({
                            "page": page_num + 1,
                            "file": pdf_path.name,
                            "text": text
                        }, ensure_ascii=False)
                        f.write(line + '\n')

                    del page
                    del text

                    pbar.update(1)
                    pbar.set_postfix({
                        "page": f"{page_num + 1}/{total_pages}",
                        "written": "✓"
                    })

                except Exception as e:
                    print(f"\n⚠️  Error on page {page_num + 1}: {e}")
                    pbar.update(1)
                    continue

    # Close PDF (free all memory)
    doc.close()
    
    # Report results
    output_size = output_jsonl.stat().st_size / (1024 * 1024)
    print(f"\n{'=' * 60}")
    print(f"✅ Extraction complete!")
    print(f"📊 Pages processed: {total_pages}")
    print(f"💾 Output file: {output_jsonl}")
    print(f"📁 File size: {output_size:.1f} MB")
    print(f"{'=' * 60}\n")

def extract_txt_to_jsonl(txt_path: Path, output_jsonl: Path):
    """Extract text from TXT file to JSONL format."""
    print(f"📄 Phase 1: Extracting text from {txt_path.name}")
    print(f"📁 Output: {output_jsonl}")
    print("=" * 60)
    
    with open(txt_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Write as single page
    with open(output_jsonl, 'w', encoding='utf-8') as f:
        line = json.dumps({
            "page": 1,
            "file": txt_path.name,
            "text": text
        }, ensure_ascii=False)
        f.write(line + '\n')
    
    output_size = output_jsonl.stat().st_size / (1024 * 1024)
    print(f"\n{'=' * 60}")
    print(f"✅ Extraction complete!")
    print(f"💾 Output file: {output_jsonl}")
    print(f"📁 File size: {output_size:.1f} MB")
    print(f"{'=' * 60}\n")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Extract text from documents to JSONL format")
    parser.add_argument("--file", type=str, help="Specific file to process")
    parser.add_argument("--all", action="store_true", help="Process all files in documents/")
    parser.add_argument("--ocr", action="store_true", help="Enable OCR fallback for scanned PDFs")
    parser.add_argument(
        "--ocr-lang",
        type=str,
        default="eng",
        help="Tesseract language(s), e.g. 'eng' or 'eng+san' (must be installed in tesseract)",
    )
    args = parser.parse_args()
    
    documents_path = Path("documents")
    output_dir = Path("documents/extracted_text")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if args.file:
        # Process specific file
        file_path = Path(args.file)
        if not file_path.exists():
            file_path = documents_path / args.file
        
        if not file_path.exists():
            print(f"❌ Error: File not found: {args.file}")
            sys.exit(1)
        
        output_jsonl = output_dir / f"{file_path.stem}_pages.jsonl"
        
        if file_path.suffix.lower() == '.pdf':
            extract_pdf_to_jsonl(file_path, output_jsonl, use_ocr=args.ocr, ocr_lang=args.ocr_lang)
        elif file_path.suffix.lower() == '.txt':
            extract_txt_to_jsonl(file_path, output_jsonl)
        else:
            print(f"❌ Unsupported file type: {file_path.suffix}")
            sys.exit(1)
    
    elif args.all:
        # Process all files
        supported_extensions = ['.pdf', '.txt']
        files = []
        
        for ext in supported_extensions:
            files.extend(documents_path.glob(f"*{ext}"))
        
        if not files:
            print(f"❌ No supported files found in {documents_path}")
            print(f"   Supported: {', '.join(supported_extensions)}")
            sys.exit(1)
        
        print(f"Found {len(files)} files to process\n")
        
        for file_path in files:
            output_jsonl = output_dir / f"{file_path.stem}_pages.jsonl"
            
            if output_jsonl.exists():
                response = input(f"⚠️  Output file exists: {output_jsonl.name}\nOverwrite? (y/N): ")
                if response.lower() != 'y':
                    print("Skipping...\n")
                    continue
            
            try:
                if file_path.suffix.lower() == '.pdf':
                    extract_pdf_to_jsonl(file_path, output_jsonl, use_ocr=args.ocr, ocr_lang=args.ocr_lang)
                elif file_path.suffix.lower() == '.txt':
                    extract_txt_to_jsonl(file_path, output_jsonl)
                print()
            except Exception as e:
                print(f"❌ Error processing {file_path.name}: {e}\n")
                continue
    
    else:
        # Interactive mode - default behavior
        supported_extensions = ['.pdf', '.txt']
        files = []
        
        for ext in supported_extensions:
            files.extend(documents_path.glob(f"*{ext}"))
        
        if not files:
            print(f"❌ No supported files found in {documents_path}")
            print(f"   Supported: {', '.join(supported_extensions)}")
            print(f"\nPlace your documents in the '{documents_path}' folder and try again.")
            sys.exit(1)
        
        print("Available files:")
        for i, f in enumerate(files, 1):
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"  {i}. {f.name} ({size_mb:.1f} MB)")
        
        choice = input(f"\nSelect file number (1-{len(files)}) or 'all': ")
        
        if choice.lower() == 'all':
            for file_path in files:
                output_jsonl = output_dir / f"{file_path.stem}_pages.jsonl"
                
                if output_jsonl.exists():
                    response = input(f"⚠️  Output file exists: {output_jsonl.name}\nOverwrite? (y/N): ")
                    if response.lower() != 'y':
                        print("Skipping...\n")
                        continue
                
                try:
                    if file_path.suffix.lower() == '.pdf':
                        extract_pdf_to_jsonl(file_path, output_jsonl, use_ocr=args.ocr, ocr_lang=args.ocr_lang)
                    elif file_path.suffix.lower() == '.txt':
                        extract_txt_to_jsonl(file_path, output_jsonl)
                    print()
                except Exception as e:
                    print(f"❌ Error processing {file_path.name}: {e}\n")
                    continue
        else:
            try:
                idx = int(choice) - 1
                if idx < 0 or idx >= len(files):
                    print("❌ Invalid selection")
                    sys.exit(1)
                
                file_path = files[idx]
                output_jsonl = output_dir / f"{file_path.stem}_pages.jsonl"
                
                if output_jsonl.exists():
                    response = input(f"⚠️  Output file exists: {output_jsonl.name}\nOverwrite? (y/N): ")
                    if response.lower() != 'y':
                        print("Cancelled.")
                        sys.exit(0)
                
                if file_path.suffix.lower() == '.pdf':
                    extract_pdf_to_jsonl(file_path, output_jsonl, use_ocr=args.ocr, ocr_lang=args.ocr_lang)
                elif file_path.suffix.lower() == '.txt':
                    extract_txt_to_jsonl(file_path, output_jsonl)
                    
            except ValueError:
                print("❌ Invalid selection")
                sys.exit(1)
    
    print("🎉 Phase 1 complete! Ready for Phase 2 (chunking & embedding)")
    print(f"   Run: python phase2_embed.py")

if __name__ == "__main__":
    main()
