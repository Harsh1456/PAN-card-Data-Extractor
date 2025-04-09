import cv2
import numpy as np
import pytesseract
from ultralytics import YOLO
import re
from datetime import datetime
import os
import glob
import json
import time

class PANProcessor:
    def __init__(self):
        self.class_map = {
            0: "dob",
            1: "father_name",
            2: "name",
            3: "pan_number"
        }
        self.date_formats = [
            (r'(\d{1,2})[/\-\.\s](\d{1,2})[/\-\.\s](\d{4})', 'dmy'),
            (r'(\d{4})[/\-\.\s](\d{1,2})[/\-\.\s](\d{1,2})', 'ymd'),
            (r'(\d{1,2})[/\-\.\s]([A-Za-z]{3,})[/\-\.\s](\d{4})', 'dby'),
        ]
        self.month_map = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        self.model = YOLO("best.pt")
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

    def preprocess(self, image):
        """Enhance text regions with safety checks"""
        if image is None or image.size == 0:
            return None
        try:
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            return cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        except cv2.error:
            return None

    def _validate_date(self, day, month, year):
        """Check if date components form valid date"""
        try:
            if 1900 <= year <= datetime.now().year + 10:
                datetime(year=year, month=month, day=day)
                return True
        except ValueError:
            return False
        return False

    def _process_dob(self, text):
        """Robust date parsing with multiple format support"""
        text = text.replace('O', '0').replace('o', '0').replace('l', '1')
        text = re.sub(r'[^0-9/\-\.\sA-Za-z]', '', text)
        
        # Handle 8-digit date format
        digits_only = re.sub(r'\D', '', text)
        if len(digits_only) == 8:
            day = int(digits_only[:2])
            month = int(digits_only[2:4])
            year = int(digits_only[4:8])
            if self._validate_date(day, month, year):
                return f"{day:02d}/{month:02d}/{year}"
            
            month = int(digits_only[:2])
            day = int(digits_only[2:4])
            if self._validate_date(day, month, year):
                return f"{day:02d}/{month:02d}/{year}"
        
        for pattern, fmt in self.date_formats:
            match = re.search(pattern, text)
            if match:
                try:
                    if fmt == 'dmy':
                        day, month, year = map(int, match.groups())
                    elif fmt == 'ymd':
                        year, month, day = map(int, match.groups())
                    elif fmt == 'dby':
                        day = int(match.group(1))
                        month_str = match.group(2)[:3].lower()
                        month = self.month_map.get(month_str, 0)
                        year = int(match.group(3))
                    
                    if self._validate_date(day, month, year):
                        return f"{day:02d}/{month:02d}/{year}"
                except (ValueError, KeyError):
                    continue
        
        return ""

    def _process_pan(self, text):
        """Robust PAN validation with OCR correction"""
        CHAR_MAP = {'0':'O','1':'I','2':'Z','4':'A','5':'S','8':'B',
                   'B':'8','D':'0','I':'1','O':'0','S':'5','Z':'2'}
        cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())
        if len(cleaned) != 10:
            return ""
        
        parts = [
            [c if c.isalpha() else CHAR_MAP.get(c, c) for c in cleaned[:5]],
            [c if c.isdigit() else CHAR_MAP.get(c, c) for c in cleaned[5:9]],
            [CHAR_MAP.get(cleaned[9], '') if not cleaned[9].isalpha() else cleaned[9]]
        ]
        
        pan = ''.join([''.join(p) for p in parts])
        if re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', pan):
            return pan
        return ""

    def _process_name(self, text):
        """Validate names with OCR correction"""
        text = re.sub(r'[^A-Za-z\s\']', '', text)
        if re.fullmatch(r'^[Oo]+$', text.strip()):
            return ""
        text = re.sub(r'\s+', ' ', text).strip().title()
        return text if len(text) >= 2 and not any(c.isdigit() for c in text) else ""

    def process_image(self, image_path):
        """Process single image and return extracted data with missing fields"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                print(f"Could not read image: {image_path}")
                return {}, list(self.class_map.values())
            
            results = self.model(img)[0]
            extracted = {v: "" for v in self.class_map.values()}
            pan_candidates = []

            for box, cls in zip(results.obb.xyxyxyxy, results.obb.cls):
                corners = box.cpu().numpy().reshape(4, 2).astype(np.float32)
                class_name = self.class_map[int(cls)]
                
                # Order points for perspective transform
                rect = np.zeros((4, 2), dtype="float32")
                s = corners.sum(axis=1)
                rect[0] = corners[np.argmin(s)]
                rect[2] = corners[np.argmax(s)]
                diff = np.diff(corners, axis=1)
                rect[1] = corners[np.argmin(diff)]
                rect[3] = corners[np.argmax(diff)]
                
                # Calculate new dimensions
                (tl, tr, br, bl) = rect
                width = max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl))
                height = max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr))
                
                dst = np.array([
                    [0, 0],
                    [width - 1, 0],
                    [width - 1, height - 1],
                    [0, height - 1]], dtype="float32")
                
                # Perspective transform
                M = cv2.getPerspectiveTransform(rect, dst)
                warped = cv2.warpPerspective(img, M, (int(width), int(height)))
                
                processed = self.preprocess(warped)
                if processed is None:
                    continue
                
                text = pytesseract.image_to_string(processed, config='--psm 6 --oem 3').strip()
                
                if class_name == "pan_number":
                    if pan := self._process_pan(text):
                        pan_candidates.append(pan)
                elif class_name == "dob":
                    extracted[class_name] = self._process_dob(text)
                else:
                    extracted[class_name] = self._process_name(text)

            valid_pans = [p for p in pan_candidates if p]
            if valid_pans:
                extracted["pan_number"] = max(set(valid_pans), key=valid_pans.count)
            elif pan_candidates:
                extracted["pan_number"] = pan_candidates[0]

            missing = [field for field, value in extracted.items() if not value]
            return extracted, missing
    
        except Exception as e:
            print(f"Error processing {image_path}: {str(e)}")
            return {}, list(self.class_map.values())

    def process_batch(self, image_paths):
        """Process multiple images and save to JSON files"""
        success_count = 0
        total_files = len(image_paths)
        
        print(f"\nStarting processing of {total_files} files...")
        
        for idx, img_path in enumerate(image_paths, 1):
            print(f"\nProcessing file {idx}/{total_files}")
            print(f"File: {os.path.basename(img_path)}")
            
            data, missing = self.process_image(img_path)
            
            if not data:
                print("🛑 Failed to process file")
                continue
                
            print("\nExtracted Data:")
            for field, value in data.items():
                print(f"{field.upper():<15}: {value if value else 'Not Detected'}")
            
            if missing:
                print(f"\n❌ Missing fields: {', '.join(missing)}")
                print("Try Again!!!")
                if len(missing) >= 2:
                    print("Please try again with a clearer image!")
                continue
                
            # Save to JSON
            filename = f"pan_{os.path.splitext(os.path.basename(img_path))[0]}_{int(time.time())}"
            saved_path = self.save_to_json(data, filename)
            
            if saved_path:
                success_count += 1
                print(f"\n✅ Successfully saved to: {saved_path}")
            else:
                print("🛑 Failed to save JSON file")

        print(f"\nProcessing complete! Successful: {success_count}/{total_files}")

        
    def save_to_json(self, data, filename):
        """Save extracted data to JSON file"""
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            filepath = os.path.join(output_dir, f"pan_{filename}.json")
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)
            return filepath
        except Exception as e:
            print(f"⚠️ Error saving JSON: {str(e)}")
            return None

if __name__ == "__main__":
    processor = PANProcessor()
    input_path = input("Enter image path or directory: ").strip('"')
    
    if os.path.isdir(input_path):
        image_paths = glob.glob(os.path.join(input_path, "*.[pj][np][gG]*")) + \
                     glob.glob(os.path.join(input_path, "*.[jJ][pP][eE][gG]*"))
    else:
        image_paths = [input_path]
    
    processor.process_batch(image_paths)
