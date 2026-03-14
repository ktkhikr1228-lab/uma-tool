import cv2
import pytesseract
import json
import sys
from pathlib import Path

# Windows環境でTesseract本体のPathを指定するんだよ！
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def process_directory(race_id: str) -> None:
    # フォルダのパスを構築
    race_folder = Path("race") / race_id
    
    if not race_folder.exists() or not race_folder.is_dir():
        print(f"エラー: フォルダが見つかりません: {race_folder.resolve()}")
        sys.exit(1)
        
    all_skills = set()
    
    # フォルダ内のpngとjpgをすべて探すんだよ！
    image_files = list(race_folder.glob("*.png")) + list(race_folder.glob("*.jpg"))
    
    if not image_files:
        print(f"画像が見つからないんだよ…: {race_folder.resolve()}")
        return
        
    print(f"{len(image_files)} 枚の画像を処理するんだよ！")
    
    for img_path in image_files:
        print(f"処理中: {img_path.name} ...", end=" ")
        image = cv2.imread(str(img_path))
        if image is None:
            print("Failed to load!")
            continue
            
        height, width, _ = image.shape
        
        # Image Cropping (画像の切り抜き)
        start_x = int(width * 0.15)
        end_x = int(width * 0.85)
        start_y = int(height * 0.20)
        end_y = int(height * 0.85)
        
        cropped_image = image[start_y:end_y, start_x:end_x]

        # Preprocessing (前処理)
        gray_image = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2GRAY)
        binary_image = cv2.adaptiveThreshold(
            gray_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 5
        )

        # OCR Execution
        custom_config = r'--oem 3 --psm 6 -l jpn'
        raw_text = pytesseract.image_to_string(binary_image, config=custom_config)

        # Formatting
        count = 0
        for line in raw_text.split('\n'):
            clean_line = line.strip()
            if not clean_line:
                continue
            
            # 誤認識しやすい文字の補正
            clean_line = clean_line.replace('◯', '○').replace('〇', '○').replace('O', '○').replace('0', '○')
            
            # ゴミデータを弾くため、3文字以上を採用
            if len(clean_line) >= 3:
                all_skills.add(clean_line)
                count += 1
        print(f"{count} 個のスキルを抽出！")

    # JSON出力 (重複を排除してあいうえお順にソート)
    skill_list = [{"name": skill, "tier": "おすすめ"} for skill in sorted(list(all_skills))]
    output_file = race_folder / "skills.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(skill_list, f, ensure_ascii=False, indent=2)
    
    print(f"\n大成功なんだよ！合計 {len(skill_list)} 個のユニークスキルを {output_file.resolve()} に保存したでしょ！")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python race/extract_race_skills.py <race_id>")
        print("Example: python race/extract_race_skills.py 202602_LOH")
        sys.exit(1)
        
    target_race_id = sys.argv[1]
    process_directory(target_race_id)