from PIL import Image
import os

input_dir = "wbs_photos_fixed"
output_dir = "wbs_photos_ready"

os.makedirs(output_dir, exist_ok=True)

print("🔁 Konversi ulang semua foto jadi format RGB 8-bit...\n")

for file in os.listdir(input_dir):
    if file.lower().endswith((".jpg", ".jpeg", ".png")):
        input_path = os.path.join(input_dir, file)
        output_path = os.path.join(output_dir, os.path.splitext(file)[0] + ".jpg")
        try:
            img = Image.open(input_path).convert("RGB")
            img.save(output_path, "JPEG", quality=95)
            print(f"✅ {file} → disimpan ulang sebagai RGB 8-bit")
        except Exception as e:
            print(f"❌ {file}: {e}")

print("\nSelesai! Semua gambar tersimpan di folder 'wbs_photos_ready'")
