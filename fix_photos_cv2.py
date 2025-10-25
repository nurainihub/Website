import cv2
import os

# Folder input & output
input_dir = "wbs_photos"
output_dir = "wbs_photos_fixed"

os.makedirs(output_dir, exist_ok=True)

count_success = 0
count_fail = 0

print("🔧 Memulai perbaikan semua foto WBS...\n")

for file in os.listdir(input_dir):
    if file.lower().endswith((".jpg", ".jpeg", ".png")):
        input_path = os.path.join(input_dir, file)
        output_path = os.path.join(output_dir, os.path.splitext(file)[0] + ".jpg")

        try:
            # Baca gambar pakai OpenCV
            img = cv2.imread(input_path)

            if img is None:
                print(f"❌ Gagal membaca {file}. Lewati.")
                count_fail += 1
                continue

            # Ubah ke RGB 8-bit (jaga format)
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # Simpan ulang dengan kualitas tinggi
            cv2.imwrite(output_path, cv2.cvtColor(rgb_img, cv2.COLOR_RGB2BGR), [int(cv2.IMWRITE_JPEG_QUALITY), 95])

            print(f"✅ {file} → diperbaiki dan disimpan di {output_dir}")
            count_success += 1

        except Exception as e:
            print(f"⚠️ Error memproses {file}: {e}")
            count_fail += 1

print("\n✅ Selesai perbaikan foto!")
print(f"   Berhasil: {count_success} file")
print(f"   Gagal: {count_fail} file")
print(f"   Folder hasil: {output_dir}")
