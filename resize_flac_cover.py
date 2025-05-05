import io
import sys
import os
import base64
from pathlib import Path
from PIL import Image
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, APIC
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggvorbis import OggVorbis
from mutagen.wave import WAVE

SUPPORTED_FORMATS = ['.flac', '.mp3', '.m4a', '.ogg', '.wav']

def resize_image(img_data):
    """Force-resize to 500x500 (stretch if needed)"""
    try:
        img = Image.open(io.BytesIO(img_data))
        
        # Remove alpha channel if present
        if img.mode in ('RGBA', 'LA'):
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

def process_flac(flac_path):
    """Process FLAC files"""
    try:
        audio = FLAC(flac_path)
        modified = False
        
        for picture in audio.pictures:
            if picture.type == 3:  # Front cover
                if resized := resize_image(picture.data):
                    picture.data = resized
                    picture.width = 500
                    picture.height = 500
                    modified = True
        
        if modified:
            audio.save()
            return True
        return False
            
    except Exception as e:
        print(f"✖ FLAC error: {e}")
        return False

def process_mp3(mp3_path):
    """Process MP3 files"""
    try:
        audio = ID3(mp3_path)
        modified = False
        
        for apic in audio.getall('APIC'):
            if resized := resize_image(apic.data):
                audio.delall('APIC')
                audio.add(APIC(
                    encoding=3,
                    mime='image/jpeg',
                    type=3,
                    desc='Cover',
                    data=resized
                ))
                modified = True
                break  # Only process first cover
        
        if modified:
            audio.save()
            return True
        return False
            
    except Exception as e:
        print(f"✖ MP3 error: {e}")
        return False

def process_m4a(m4a_path):
    """Process M4A/AAC files"""
    try:
        audio = MP4(m4a_path)
        modified = False
        
        if 'covr' in audio:
            cover = audio['covr'][0]
            if resized := resize_image(cover):
                audio['covr'] = [MP4Cover(resized, imageformat=MP4Cover.FORMAT_JPEG)]
                modified = True
        
        if modified:
            audio.save()
            return True
        return False
            
    except Exception as e:
        print(f"✖ M4A error: {e}")
        return False

def process_ogg(ogg_path):
    """Process OGG files"""
    try:
        audio = OggVorbis(ogg_path)
        modified = False
        
        if 'metadata_block_picture' in audio:
            picture_data = audio['metadata_block_picture'][0]
            picture = Picture(base64.b64decode(picture_data))
            
            if resized := resize_image(picture.data):
                new_pic = Picture()
                new_pic.type = 3
                new_pic.mime = 'image/jpeg'
                new_pic.data = resized
                audio['metadata_block_picture'] = [base64.b64encode(new_pic.write()).decode()]
                modified = True
        
        if modified:
            audio.save()
            return True
        return False
            
    except Exception as e:
        print(f"✖ OGG error: {e}")
        return False

def process_wav(wav_path):
    """Process WAV files (ID3v2 tags)"""
    try:
        audio = WAVE(wav_path)
        
        # WAV files use ID3 tags like MP3
        if not audio.tags:
            audio.add_tags()
            
        modified = False
        
        for apic in audio.tags.getall('APIC'):
            if resized := resize_image(apic.data):
                audio.tags.delall('APIC')
                audio.tags.add(APIC(
                    encoding=3,
                    mime='image/jpeg',
                    type=3,
                    desc='Cover',
                    data=resized
                ))
                modified = True
                break  # Only process first cover
        
        if modified:
            audio.save()
            return True
        return False
            
    except Exception as e:
        print(f"✖ WAV error: {e}")
        return False

def process_file(file_path):
    """Route files to appropriate processor"""
    ext = Path(file_path).suffix.lower()
    
    processors = {
        '.flac': process_flac,
        '.mp3': process_mp3,
        '.m4a': process_m4a,
        '.ogg': process_ogg,
        '.wav': process_wav
    }
    
    if ext in processors:
        return processors[ext](file_path)
    else:
        print(f"⚠ Unsupported format: {ext}")
        return False

def process_files(file_paths):
    """Handle multiple files/folders"""
    valid_files = set()
    
    # Collect all supported files
    for path in file_paths:
        path = Path(path.strip('"'))
        if path.is_file() and path.suffix.lower() in SUPPORTED_FORMATS:
            valid_files.add(path)
        elif path.is_dir():
            for root, _, files in os.walk(path):
                for file in files:
                    if Path(file).suffix.lower() in SUPPORTED_FORMATS:
                        valid_files.add(Path(root) / file)
    
    if not valid_files:
        print("❌ No supported files found")
        return
    
    print(f"Found {len(valid_files)} files to process...")
    success_count = 0
    
    for file_path in valid_files:
        try:
            if process_file(file_path):
                print(f"✓ Success: {file_path.name}")
                success_count += 1
            else:
                print(f"⚠ No cover art: {file_path.name}")
        except Exception as e:
            print(f"✖ Failed {file_path.name}: {str(e)}")
    
    print(f"\nResults: {success_count} successful, {len(valid_files) - success_count} failed")

def main():
    if len(sys.argv) > 1:
        process_files(sys.argv[1:])
    else:
        print("Drag and drop audio files/folders onto this script")
        print("Supported formats: MP3, FLAC, M4A, OGG, WAV")
        print("OR use command line: python script.py file1.mp3 file2.wav ...")
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
