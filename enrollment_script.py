import face_recognition
import numpy as np
import os
import pickle
import mysql.connector
import cv2

# --- KONFIGURASI DATABASE ---
DB_CONFIG = {
    'user': 'root',
    'password': '',
    'host': 'localhost',
    'database': 'psbr_tarunajaya2'
}

# --- FUNGSI KONEKSI DATABASE ---
def connect_db():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as err:
        print(f"❌ Gagal konek ke database: {err}")
        return None

# --- FUNGSI ENROLL ---
def enroll_wbs_face(photo_path):
    filename = os.path.basename(photo_path)
    try:
        name_part, id_part = filename.split('_')
        wbs_id = int(id_part.split('.')[0])
        wbs_name = name_part.replace('-', ' ')
    except Exception as e:
        print(f"⚠️ Format salah pada {filename}: {e}")
        return

    print(f"Memproses WBS ID: {wbs_id} ({wbs_name})...")

    try:
        img = cv2.imread(photo_path, cv2.IMREAD_UNCHANGED)

        if img is None:
            print(f"   ❌ Tidak bisa membaca gambar {photo_path}")
            return

        # Pastikan gambar hanya 3 channel (hapus alpha channel)
        if img.shape[-1] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        # Konversi ke RGB 8-bit
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_rgb = np.ascontiguousarray(img_rgb, dtype=np.uint8)

        # Verifikasi dimensi
        if len(img_rgb.shape) != 3 or img_rgb.shape[2] != 3:
            print(f"   ❌ Format gambar tidak valid (bukan RGB 3 channel).")
            return

        # Deteksi wajah
        face_locations = face_recognition.face_locations(img_rgb)
        if not face_locations:
            print(f"   ⚠️ Tidak ada wajah di {photo_path}")
            return

        encodings = face_recognition.face_encodings(img_rgb, face_locations)
        if not encodings:
            print(f"   ⚠️ Gagal membuat encoding {photo_path}")
            return

        face_encoding = encodings[0]

    except Exception as e:
        print(f"   ❌ Error memproses {photo_path}: {e}")
        return

    # Simpan ke DB
    db = connect_db()
    if not db:
        print("   ❌ Tidak bisa konek ke DB.")
        return

    cursor = db.cursor()
    query = "UPDATE wbs SET face_encoding = %s WHERE id_wbs = %s AND nama = %s"
    try:
        cursor.execute(query, (pickle.dumps(face_encoding), wbs_id, wbs_name))
        db.commit()
        print(f"   ✅ {wbs_name} (ID {wbs_id}) berhasil disimpan.")
    except Exception as e:
        print(f"   ❌ Gagal simpan ke DB: {e}")
        db.rollback()
    finally:
        cursor.close()
        db.close()

# --- LOOP SEMUA FOTO ---
def run_enrollment():
    photo_dir = "wbs_photos_ready"

    if not os.path.exists(photo_dir):
        print(f"❌ Folder '{photo_dir}' tidak ditemukan.")
        return

    files = [f for f in os.listdir(photo_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if not files:
        print(f"⚠️ Tidak ada file di folder '{photo_dir}'.")
        return

    print(f"📸 Ditemukan {len(files)} file wajah. Mulai proses...\n")
    for f in files:
        enroll_wbs_face(os.path.join(photo_dir, f))
    print("\n✅ Enrollment selesai!")

if __name__ == "__main__":
    run_enrollment()
