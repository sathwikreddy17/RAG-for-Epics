#!/usr/bin/env python3
"""
Document Watcher Service
Monitors documents/ folder and auto-processes new PDFs.
"""

import os
import sys
import time
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('watcher.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
DOCUMENTS_DIR = Path("documents")
EXTRACTED_DIR = DOCUMENTS_DIR / "extracted_text"
PROCESSED_MARKER = ".processed"
PROCESSING_MARKER = ".processing"
SUPPORTED_EXTENSIONS = {'.pdf', '.txt', '.docx'}

class DocumentHandler(FileSystemEventHandler):
    """Handles document file events."""
    
    def __init__(self):
        self.processing = set()
        
    def on_created(self, event):
        """Called when a file is created."""
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        
        # Only process supported file types
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return
            
        # Ignore files in extracted_text directory
        if "extracted_text" in str(file_path):
            return
            
        logger.info(f"📄 New document detected: {file_path.name}")
        
        # Wait a bit for file to be fully written
        time.sleep(2)
        
        self.process_document(file_path)
    
    def on_modified(self, event):
        """Called when a file is modified."""
        # We handle this in on_created, but could add logic here
        # to reprocess if a document is updated
        pass
    
    def process_document(self, file_path: Path):
        """Process a document through the full pipeline."""
        
        if file_path in self.processing:
            logger.info(f"⏭️  Already processing {file_path.name}, skipping...")
            return
            
        # Check if already processed
        marker_file = file_path.with_suffix(file_path.suffix + PROCESSED_MARKER)
        if marker_file.exists():
            logger.info(f"✅ {file_path.name} already processed, skipping...")
            return
        
        try:
            self.processing.add(file_path)
            processing_marker = file_path.with_suffix(file_path.suffix + PROCESSING_MARKER)
            processing_marker.touch()
            
            logger.info(f"🚀 Starting pipeline for: {file_path.name}")
            logger.info("=" * 60)
            
            # Phase 1: Extract text
            logger.info("📝 Phase 1: Extracting text...")
            result = subprocess.run(
                [sys.executable, "phase1_extract.py", "--file", str(file_path)],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode != 0:
                logger.error(f"❌ Phase 1 failed: {result.stderr}")
                return
            
            logger.info("✅ Phase 1 complete: Text extracted")
            
            # Find the generated JSONL file
            jsonl_file = EXTRACTED_DIR / f"{file_path.stem}_pages.jsonl"
            if not jsonl_file.exists():
                logger.error(f"❌ JSONL file not found: {jsonl_file}")
                return
            
            # Phase 2: Create embeddings
            logger.info("🧩 Phase 2: Creating embeddings...")
            result = subprocess.run(
                [sys.executable, "phase2_embed.py", "--file", str(jsonl_file)],
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout
            )
            
            if result.returncode != 0:
                logger.error(f"❌ Phase 2 failed: {result.stderr}")
                return
            
            logger.info("✅ Phase 2 complete: Embeddings created")
            
            # Mark as processed
            marker_file.touch()
            processing_marker.unlink()
            
            logger.info("=" * 60)
            logger.info(f"🎉 SUCCESS! {file_path.name} is ready for querying!")
            logger.info("=" * 60)
            
            # Trigger backend reload if server is running
            self.trigger_reload()
            
        except subprocess.TimeoutExpired:
            logger.error(f"⏱️  Processing timed out for {file_path.name}")
        except Exception as e:
            logger.error(f"❌ Error processing {file_path.name}: {e}")
        finally:
            self.processing.discard(file_path)
            if processing_marker.exists():
                processing_marker.unlink()
    
    def trigger_reload(self):
        """Trigger backend reload by touching a reload marker."""
        reload_marker = Path("data/.reload_trigger")
        reload_marker.parent.mkdir(exist_ok=True)
        reload_marker.touch()
        logger.info("🔄 Triggered backend reload")

def check_existing_documents():
    """Process any existing unprocessed documents."""
    logger.info("🔍 Checking for existing unprocessed documents...")
    
    handler = DocumentHandler()
    found_any = False
    
    for file_path in DOCUMENTS_DIR.glob("*"):
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            marker_file = file_path.with_suffix(file_path.suffix + PROCESSED_MARKER)
            if not marker_file.exists():
                found_any = True
                logger.info(f"📄 Found unprocessed document: {file_path.name}")
                handler.process_document(file_path)
    
    if not found_any:
        logger.info("✅ No unprocessed documents found")

def main():
    """Main entry point."""
    print("=" * 60)
    print("🔭 Document Watcher Service")
    print("=" * 60)
    print(f"📁 Watching: {DOCUMENTS_DIR.absolute()}")
    print(f"📝 Supported: {', '.join(SUPPORTED_EXTENSIONS)}")
    print("=" * 60)
    print("📌 Instructions:")
    print("   1. Drop PDF/TXT/DOCX files into documents/ folder")
    print("   2. Watcher will auto-process them")
    print("   3. Wait for 'SUCCESS!' message")
    print("   4. Files are immediately queryable in chatbot")
    print("=" * 60)
    print("🛑 Press Ctrl+C to stop")
    print("=" * 60)
    print()
    
    # Create directories if needed
    DOCUMENTS_DIR.mkdir(exist_ok=True)
    EXTRACTED_DIR.mkdir(exist_ok=True)
    
    # Process any existing unprocessed documents
    check_existing_documents()
    
    # Start watching
    event_handler = DocumentHandler()
    observer = Observer()
    observer.schedule(event_handler, str(DOCUMENTS_DIR), recursive=False)
    observer.start()
    
    logger.info("👁️  Watcher active - monitoring for new documents...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopping watcher...")
        observer.stop()
    
    observer.join()
    logger.info("✅ Watcher stopped")

if __name__ == "__main__":
    main()
