from PIL import Image
import os

input_dir = "wbs_photos"  # folder asal foto
output_dir = "wbs_photos_fixed"  # folder hasil konversi

os.makedirs(output_dir, exist_ok=True)

print("🔧 Konversi ulang semua foto agar 8-bit RGB...")

for file in os.listdir(input_dir):
    if file.lower().endswith((".jpg", ".jpeg", ".png")):
        try:
            img_path = os.path.join(input_dir, file)
            with Image.open(img_path) as img:
                # Pastikan jadi RGB 8-bit
                img = img.convert("RGB")

                # Simpan ulang ke format JPEG
                output_path = os.path.join(output_dir, os.path.splitext(file)[0] + ".jpg")
                img.save(output_path, "JPEG", quality=95)
                print(f"✅ {file} dikonversi → {output_path}")

        except Exception as e:
            print(f"❌ Gagal memproses {file}: {e}")

print("\n✅ Semua foto berhasil dikonversi! Gunakan folder 'wbs_photos_fixed' untuk enrollment.")
