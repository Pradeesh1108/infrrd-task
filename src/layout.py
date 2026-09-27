import logging
import threading
from paddleocr import PaddleOCR

logging.getLogger("ppocr").setLevel(logging.ERROR)

class DocumentParser:
    def __init__(self):
        self.ocr = PaddleOCR(use_angle_cls=True, lang='en')
        self.lock = threading.Lock()
        
    def parse(self, image_path: str) -> str:
        with self.lock:
            result = self.ocr.ocr(image_path)
            
        if not result or not result[0]:
            return ""
            
        boxes = result[0]
        parsed_items = []
        for line in boxes:
            box = line[0]
            text = line[1][0]
            
            y_coords = [point[1] for point in box]
            x_coords = [point[0] for point in box]
            center_y = sum(y_coords) / 4.0
            min_x = min(x_coords)
            
            height = max(y_coords) - min(y_coords)
            
            parsed_items.append({
                "text": text,
                "cy": center_y,
                "x": min_x,
                "h": height
            })
            
        parsed_items.sort(key=lambda item: item['cy'])
        
        lines = []
        current_line = []
        
        for item in parsed_items:
            if not current_line:
                current_line.append(item)
            else:
                prev_item = current_line[-1]
                if abs(item['cy'] - prev_item['cy']) < (max(item['h'], prev_item['h']) * 0.5):
                    current_line.append(item)
                else:
                    lines.append(current_line)
                    current_line = [item]
        if current_line:
            lines.append(current_line)
            
        layout_text = []
        for line in lines:
            line.sort(key=lambda item: item['x'])
            texts = [item['text'] for item in line]
            layout_text.append(" \t ".join(texts))
            
        return "\n".join(layout_text)

_parser_instance = None
def get_parser():
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = DocumentParser()
    return _parser_instance

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        parser = DocumentParser()
        print(parser.parse(sys.argv[1]))
