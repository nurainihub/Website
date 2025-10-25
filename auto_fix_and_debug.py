# auto_fix_and_debug.py
import os
import cv2
import numpy as np
from PIL import Image, ImageFile
import face_recognition
import traceback

ImageFile.LOAD_TRUNCATED_IMAGES = True

INPUT_DIR = "wbs_photos"           # sumber awal (original)
CONVERTED_DIR = "wbs_photos_converted"  # hasil PIL (opsional)
FIXED_DIR = "wbs_photos_fixed"     # hasil final yang akan diuji

os.makedirs(CONVERTED_DIR, exist_ok=True)
os.makedirs(FIXED_DIR, exist_ok=True)

def pil_convert_all():
    print("1) Konversi awal via PIL ->", CONVERTED_DIR)
    count = 0
    for fn in os.listdir(INPUT_DIR):
        if not fn.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        in_path = os.path.join(INPUT_DIR, fn)
        out_path = os.path.join(CONVERTED_DIR, os.path.splitext(fn)[0] + ".jpg")
        try:
            with Image.open(in_path) as im:
                im = im.convert("RGB")
                im.save(out_path, "JPEG", quality=95)
            print("   ✅", fn, "→", out_path)
            count += 1
        except Exception as e:
            print("   ❌ PIL convert failed:", fn, "-", e)
    print(f"   {count} file dikonversi dengan PIL.\n")

def opencv_fix_all(source_dir):
    print("2) Perbaikan via OpenCV ->", FIXED_DIR)
    count_ok = 0
    count_fail = 0
    for fn in os.listdir(source_dir):
        if not fn.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        in_path = os.path.join(source_dir, fn)
        out_path = os.path.join(FIXED_DIR, os.path.splitext(fn)[0] + ".jpg")
        try:
            img = cv2.imdecode(np.fromfile(in_path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
            # fallback if imdecode returned None
            if img is None:
                img = cv2.imread(in_path, cv2.IMREAD_UNCHANGED)

            if img is None:
                print("   ❌ OpenCV gagal membaca:", fn)
                count_fail += 1
                continue

            # If image is grayscale -> convert to BGR
            if img.ndim == 2:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            # If image has 4 channels (e.g. RGBA) -> drop alpha or convert
            if img.shape[2] == 4:
                # convert possible BGRA -> BGR
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            # ensure dtype is uint8
            if img.dtype != np.uint8:
                img = img.astype(np.uint8)

            # ensure 3 channels
            if img.ndim == 3 and img.shape[2] >= 3:
                img = img[:, :, :3]

            # write with imwrite; use unicode-safe write via imencode+tofile on Windows
            success, encoded = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            if not success:
                print("   ⚠️ imencode gagal:", fn)
                count_fail += 1
                continue
            with open(out_path, 'wb') as f:
                f.write(encoded.tobytes())

            print("   ✅", fn, "→", out_path)
            count_ok += 1

        except Exception as e:
            print("   ❌ Exception saat perbaiki:", fn)
            traceback.print_exc()
            count_fail += 1

    print(f"   Selesai OpenCV fix. OK={count_ok}, FAIL={count_fail}\n")


def debug_test_face_recognition(source_dir):
    print("3) Uji tiap file dengan face_recognition (debug output)")
    for fn in os.listdir(source_dir):
        if not fn.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        path = os.path.join(source_dir, fn)
        print(f"\n--- {fn} ---")
        try:
            # read raw bytes head for quick check
            with open(path, "rb") as f:
                head = f.read(64)
            print("file bytes head:", head[:16].hex(), "... (len", len(head), ")")

            # Read via PIL to get mode info
            try:
                with Image.open(path) as im:
                    print("PIL mode:", im.mode, "size:", im.size)
            except Exception as e:
                print("PIL open error:", e)

            # Read via OpenCV using unicode-safe path
            img_bgr = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
            if img_bgr is None:
                print("OpenCV read: None")
                img_bgr = cv2.imread(path, cv2.IMREAD_UNCHANGED)
                print("OpenCV fallback imread:", "None" if img_bgr is None else "OK")

            if img_bgr is None:
                print("❌ Tidak bisa dibaca oleh OpenCV. Lewati uji face_recognition.")
                continue

            print("OpenCV shape:", img_bgr.shape, "dtype:", img_bgr.dtype)

            # Convert to RGB, force uint8 and 3 channels
            if img_bgr.ndim == 2:
                img_bgr = cv2.cvtColor(img_bgr, cv2.COLOR_GRAY2BGR)
            if img_bgr.shape[2] == 4:
                img_bgr = cv2.cvtColor(img_bgr, cv2.COLOR_BGRA2BGR)
            if img_bgr.dtype != np.uint8:
                img_bgr = img_bgr.astype(np.uint8)

            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            print("Converted (RGB) shape:", img_rgb.shape, "dtype:", img_rgb.dtype)

            # Try face_recognition operations (face_locations + encodings) with try/except
            try:
                locs = face_recognition.face_locations(img_rgb)
                print("face_locations count:", len(locs))
                if len(locs) > 0:
                    encs = face_recognition.face_encodings(img_rgb, locs)
                    print("face_encodings count:", len(encs))
                    if len(encs) > 0:
                        e0 = encs[0]
                        print("encoding[0] shape:", np.array(e0).shape, "dtype:", np.array(e0).dtype)
                    else:
                        print("⚠️ Tidak ada encoding walau lokasi wajah ada.")
                else:
                    print("⚠️ face_locations kosong — mungkin wajah tidak jelas.")
            except Exception as e:
                print("‼️ face_recognition error:", repr(e))
                traceback.print_exc()

        except Exception as top_e:
            print("ERROR unexpected for", fn, top_e)
            traceback.print_exc()

def main():
    if not os.path.isdir(INPUT_DIR):
        print("ERROR: folder sumber tidak ditemukan:", INPUT_DIR)
        return

    pil_convert_all()
    opencv_fix_all(CONVERTED_DIR)
    debug_test_face_recognition(FIXED_DIR)
    print("\nSelesai seluruh langkah. Periksa output di atas untuk file mana yang gagal.")

if __name__ == "__main__":
    main()
