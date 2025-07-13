#!/usr/bin/env python3
"""
Script to concatenate all markdown, text, and PDF files in the document directory
"""

import os
from pathlib import Path
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("Warning: PyPDF2 not installed. PDF support disabled.")
    print("Install with: pip install PyPDF2")

def read_pdf(file_path):
    """Read a PDF file and return its text content"""
    if not PDF_SUPPORT:
        print(f"Cannot read PDF {file_path}: PyPDF2 not installed")
        return ""
    
    try:
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            text_content = []
            
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                if text:
                    text_content.append(f"\n--- Page {page_num + 1} ---\n")
                    text_content.append(text)
            
            return ''.join(text_content)
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
        return ""

def read_file(file_path):
    """Read a file and return its content based on its extension"""
    try:
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.pdf':
            return read_pdf(file_path)
        else:
            # For .md, .txt, and other text files
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return ""

def concatenate_documents():
    """Concatenate all markdown, text, and PDF files in logical order"""
    
    # Base directory
    base_dir = Path("/Users/ozoraogino/dev/donut/docbot/document/ja")
    
    # Define the files in logical order
    files_to_concatenate = [
        # Main index
        "index.md",
        
        # Getting started section
        "getting_started/index.md",
        "getting_started/sdk_ability.md",
        "getting_started/sdk_usage.md",
        "getting_started/simulation.md",
        
        # Protocol documentation
        "protocol/index.md",
        "protocol/common/README.md",
        "protocol/mc/README.md",
        "protocol/mm/README.md",
        "protocol/pnc/README.md",
        "protocol/motion_player/README.md",
        "protocol/hal_sensor/README.md",
        "protocol/hds/README.md",
        "protocol/rc/README.md",
        "protocol/interaction/README.md",
        "protocol/task_engine/README.md",
        "protocol/other/README.md",
        
        # FAQ
        "faq/index.md",
        
        # External links
        "external/index.md",
        
        # Release notes
        "release_notes/index.md",
        "release_notes/V0.6.md",
        "release_notes/V0.7.md",
        
        # PDF files
        "A2 通用机器人用户手册-旗舰款（英文）.pdf"
    ]
    
    # Output file
    output_file = Path("/Users/ozoraogino/dev/donut/docbot/document/concatenated_documentation.md")
    
    # Also find all PDF files in the directory (optional)
    pdf_files = list(base_dir.glob("*.pdf"))
    for pdf_file in pdf_files:
        relative_path = pdf_file.relative_to(base_dir)
        if str(relative_path) not in files_to_concatenate:
            files_to_concatenate.append(str(relative_path))
            print(f"Found additional PDF: {relative_path}")
    
    # Concatenate all files
    all_content = []
    
    for file_path in files_to_concatenate:
        full_path = base_dir / file_path
        
        if full_path.exists():
            print(f"Reading: {file_path}")
            content = read_file(full_path)
            
            if content:
                # Add file separator
                all_content.append(f"\n\n{'='*80}\n")
                all_content.append(f"# File: {file_path}\n")
                all_content.append(f"{'='*80}\n\n")
                all_content.append(content)
        else:
            print(f"Warning: File not found: {full_path}")
    
    # Write concatenated content to output file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(''.join(all_content))
        print(f"\nSuccessfully concatenated {len(files_to_concatenate)} files")
        print(f"Output saved to: {output_file}")
    except Exception as e:
        print(f"Error writing output file: {e}")

if __name__ == "__main__":
    concatenate_documents()