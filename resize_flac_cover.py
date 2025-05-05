import io
import sys
import os
from pathlib import Path
from PIL import Image
from mutagen.flac import FLAC, Picture

def resize_image(img_data):
    """Force-resize to 500x500 (stretch if needed)"""
    try:
        img = Image.open(io.BytesIO(img_data))
        
        # Remove alpha channel if present
        if img.mode == 'RGBA':
            img = img.convert('RGB')
            
        # Force resize to 500x500 with high-quality scaling
        img = img.resize((500, 500), Image.Resampling.LANCZOS)
        
        # Save as JPEG
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG', quality=95)
        return img_bytes.getvalue()
    
    except Exception as e:
        print(f"✖ Image processing failed: {e}")
        return None

def process_single_flac(flac_path):
    """Process one FLAC file's embedded art"""
    try:
        flac = FLAC(flac_path)
        modified = False
        
        for picture in flac.pictures:
            if picture.type == 3:  # Front cover
                if resized := resize_image(picture.data):
                    picture.data = resized
                    picture.width = 500
                    picture.height = 500
                    modified = True
        
        if modified:
            flac.save()
            print(f"✓ Success: {os.path.basename(flac_path)}")
            return True
        else:
            print(f"⚠ No cover art found in: {os.path.basename(flac_path)}")
            return False
            
    except Exception as e:
        print(f"✖ Failed {os.path.basename(flac_path)}: {str(e)}")
        return False

def process_files(file_paths):
    """Handle multiple files/folders"""
    flac_files = set()
    
    # Collect all FLAC files
    for path in file_paths:
        path = Path(path.strip('"'))
        if path.is_file() and path.suffix.lower() == '.flac':
            flac_files.add(path)
        elif path.is_dir():
            for root, _, files in os.walk(path):
                for file in files:
                    if file.lower().endswith('.flac'):
                        flac_files.add(Path(root) / file)
    
    # Process all found files
    if not flac_files:
        print("❌ No FLAC files found")
        return
    
    print(f"Found {len(flac_files)} FLAC files to process...")
    success_count = 0
    
    for flac_path in flac_files:
        if process_single_flac(flac_path):
            success_count += 1
    
    print(f"\nResults: {success_count} successful, {len(flac_files) - success_count} failed")

def main():
    if len(sys.argv) > 1:
        process_files(sys.argv[1:])
    else:
        print("Drag and drop FLAC files or folders onto this script")
        print("OR use command line: python script.py file1.flac file2.flac ...")
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
