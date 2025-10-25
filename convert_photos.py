from PIL import Image
import os

input_dir = "wbs_photos"
output_dir = "wbs_photos_converted"

os.makedirs(output_dir, exist_ok=True)

for file in os.listdir(input_dir):
    if file.lower().endswith((".jpg", ".jpeg", ".png")):
        img = Image.open(os.path.join(input_dir, file)).convert("RGB")
        img.save(os.path.join(output_dir, os.path.splitext(file)[0] + ".jpg"), format="JPEG")
        print(f"✅ {file} dikonversi → {output_dir}")

print("\nSelesai! Semua file dikonversi ke folder:", output_dir)
