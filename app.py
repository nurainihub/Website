from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import mysql.connector
import face_recognition
import numpy as np
import pickle
import base64
import cv2
from datetime import datetime
from threading import Lock

app = Flask(__name__)
CORS(app)

# --- KONFIGURASI DATABASE ---
DB_CONFIG = {
    'user': 'root',
    'password': '',  # sesuaikan jika kamu pakai password MySQL
    'host': 'localhost',
    'database': 'psbr_tarunajaya2'
}

# --- GLOBAL VARIABLE UNTUK DATA WAJAH ---
data_lock = Lock()
KNOWN_ENCODINGS = []
WBS_LOOKUP = {}


def connect_db():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as err:
        print(f"❌ ERROR Database: {err}")
        return None


def load_known_faces():
    """Memuat semua wajah WBS dari database"""
    global KNOWN_ENCODINGS, WBS_LOOKUP
    db = connect_db()
    if not db:
        print("⚠️ Tidak bisa terhubung ke database.")
        return
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id_wbs, nama, face_encoding FROM wbs WHERE face_encoding IS NOT NULL")
        results = cursor.fetchall()

        encodings_temp = []
        lookup_temp = {}

        for i, row in enumerate(results):
            try:
                enc = pickle.loads(row['face_encoding'])
                encodings_temp.append(enc)
                lookup_temp[i] = {'id_wbs': row['id_wbs'], 'nama': row['nama']}
            except Exception as e:
                print(f"Error decoding WBS {row['id_wbs']}: {e}")

        with data_lock:
            KNOWN_ENCODINGS = encodings_temp
            WBS_LOOKUP = lookup_temp

        print(f"📦 {len(KNOWN_ENCODINGS)} wajah WBS dimuat untuk absensi.")
        cursor.close()
        db.close()
    except Exception as e:
        print(f"FATAL: {e}")
        if db:
            db.close()


# Muat saat startup
load_known_faces()


# --- ROUTE HALAMAN UTAMA ---
@app.route('/')
def home():
    return render_template('absensi.html')


# --- API ABSENSI ---
@app.route('/api/absensi', methods=['POST'])
def handle_absensi():
    data = request.json
    image_data_url = data.get('image')
    kegiatan_id = data.get('kegiatan_id')
    pptk_nama = data.get('pptk_nama', 'PPTK Tidak Diketahui')
    narasumber_nama = data.get('narasumber_nama', 'Narasumber Tidak Diketahui')

    if not image_data_url or not kegiatan_id:
        return jsonify({"status": "error", "message": "Data gambar atau ID kegiatan tidak lengkap."}), 400

    if not KNOWN_ENCODINGS:
        return jsonify({"status": "error", "message": "Database wajah kosong. Jalankan enrollment dulu."}), 500

    try:
        # Konversi base64 → numpy array
        encoded_data = image_data_url.split(',')[1]
        nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({"status": "error", "message": "Gagal membaca gambar webcam."}), 400

        # Konversi ke RGB
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Deteksi wajah
        face_locations = face_recognition.face_locations(rgb_img, model="hog")
        if not face_locations:
            return jsonify({"status": "failed", "message": "Tidak ada wajah terdeteksi."}), 200

        # Proses encoding wajah dengan proteksi error
        try:
            encodings = face_recognition.face_encodings(rgb_img, known_face_locations=face_locations)
            if not encodings:
                return jsonify({"status": "failed", "message": "Wajah tidak bisa di-encode."}), 200
            face_encoding_baru = encodings[0]
        except Exception as e:
            print("❌ Gagal melakukan encoding:", e)
            return jsonify({"status": "error", "message": f"Gagal memproses wajah: {e}"}), 500

        # Bandingkan dengan database
        matches = face_recognition.compare_faces(KNOWN_ENCODINGS, face_encoding_baru, tolerance=0.5)
        match_index = -1
        if True in matches:
            distances = face_recognition.face_distance(KNOWN_ENCODINGS, face_encoding_baru)
            best_match = np.argmin(distances)
            if matches[best_match]:
                match_index = best_match

        if match_index != -1:
            wbs_info = WBS_LOOKUP[match_index]
            id_wbs = wbs_info['id_wbs']
            nama_wbs = wbs_info['nama']

            db = connect_db()
            if not db:
                return jsonify({"status": "error", "message": "Koneksi database gagal."}), 500
            cursor = db.cursor()

            cursor.execute("SELECT nama_kegiatan FROM kegiatan WHERE id_kegiatan=%s", (kegiatan_id,))
            kegiatan = cursor.fetchone()
            kegiatan_name = kegiatan[0] if kegiatan else "(Tidak diketahui)"
            now = datetime.now()

            combined_executor = f"PPTK: {pptk_nama} | Narasumber: {narasumber_nama}"
            cursor.execute("""
                INSERT INTO absensi (id_wbs, id_kegiatan, tanggal, waktu_absensi, narasumber)
                VALUES (%s, %s, %s, %s, %s)
            """, (id_wbs, kegiatan_id, now.date(), now.time(), combined_executor))
            db.commit()
            cursor.close()
            db.close()

            return jsonify({
                "status": "success",
                "message": f"Absensi BERHASIL untuk {nama_wbs}.",
                "nama": nama_wbs,
                "kegiatan": kegiatan_name
            })
        else:
            return jsonify({"status": "failed", "message": "Wajah tidak dikenali atau belum terdaftar."}), 200

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"status": "error", "message": f"Kesalahan server: {e}"}), 500

# --- API UNTUK MENAMPILKAN DAFTAR WBS (Dropdown di halaman pendaftaran wajah) ---
@app.route('/api/wbs_list', methods=['GET'])
def get_wbs_list():
    db = connect_db()
    if not db:
        return jsonify({"status": "error", "message": "Gagal koneksi ke database"}), 500

    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT id_wbs, nama, 
                   CASE WHEN face_encoding IS NOT NULL THEN 1 ELSE 0 END AS is_registered
            FROM wbs
            ORDER BY nama
        """)
        data = cursor.fetchall()
        cursor.close()
        db.close()
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        print("Error /api/wbs_list:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


# --- API LAPORAN ---
@app.route('/api/laporan', methods=['GET'])
def get_laporan():
    import datetime
    tgl_mulai = request.args.get('tgl_mulai', '').strip()
    print("🕓 [DEBUG] Tanggal diterima dari frontend:", repr(tgl_mulai))

    db = connect_db()
    if not db:
        print("❌ DB GAGAL TERHUBUNG")
        return jsonify({"status": "error", "message": "Gagal terhubung ke database"}), 500

    try:
        cursor = db.cursor(dictionary=True)

        # --- Jika tidak ada tanggal, ambil semua data absensi ---
        if not tgl_mulai:
            print("⚙️ [DEBUG] Tidak ada tanggal, ambil semua data absensi")
            cursor.execute("""
                SELECT a.tanggal, a.waktu_absensi, w.nama AS nama_wbs, 
                       k.nama_kegiatan, a.narasumber 
                FROM absensi a
                JOIN wbs w ON a.id_wbs = w.id_wbs
                JOIN kegiatan k ON a.id_kegiatan = k.id_kegiatan
                ORDER BY a.tanggal DESC, a.waktu_absensi DESC
            """)
        else:
            try:
                tanggal_obj = datetime.datetime.strptime(tgl_mulai, "%Y-%m-%d").date()
            except ValueError:
                print("⚠️ [DEBUG] Format tanggal tidak valid:", tgl_mulai)
                return jsonify({"status": "error", "message": "Format tanggal tidak valid"}), 400

            print("✅ [DEBUG] Query dengan tanggal:", tanggal_obj)

            cursor.execute("""
                SELECT a.tanggal, a.waktu_absensi, w.nama AS nama_wbs, 
                       k.nama_kegiatan, a.narasumber 
                FROM absensi a
                JOIN wbs w ON a.id_wbs = w.id_wbs
                JOIN kegiatan k ON a.id_kegiatan = k.id_kegiatan
                WHERE a.tanggal = %s
                ORDER BY a.waktu_absensi DESC
            """, (tanggal_obj,))

        hasil = cursor.fetchall()

        # 🔧 FIX: Konversi field waktu & tanggal jadi string agar bisa dikirim via JSON
        for item in hasil:
            if "waktu_absensi" in item and item["waktu_absensi"] is not None:
                item["waktu_absensi"] = str(item["waktu_absensi"])
            if "tanggal" in item and item["tanggal"] is not None:
                item["tanggal"] = str(item["tanggal"])

        print("📊 [DEBUG] Jumlah data ditemukan:", len(hasil))

        cursor.close()
        db.close()

        return jsonify({"status": "success", "data": hasil})

    except Exception as e:
        print("🔥 ERROR LAPORAN:", e)
        if db and db.is_connected():
            cursor.close()
            db.close()
        return jsonify({"status": "error", "message": f"Kesalahan server: {e}"}), 500

   

# --- API DAFTAR WAJAH ---
@app.route('/api/daftar_wajah', methods=['POST'])
def daftar_wajah():
    data = request.json
    id_wbs = data.get('id_wbs')
    image_data_url = data.get('image')
    if not id_wbs or not image_data_url:
        return jsonify({"status": "error", "message": "Data tidak lengkap."}), 400
    try:
        encoded_data = image_data_url.split(',')[1]
        nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        faces = face_recognition.face_locations(rgb)
        if not faces:
            return jsonify({"status": "failed", "message": "Tidak ada wajah terdeteksi."}), 200
        enc = face_recognition.face_encodings(rgb, faces)[0]
        binary = pickle.dumps(enc)
        db = connect_db()
        cursor = db.cursor()
        cursor.execute("UPDATE wbs SET face_encoding=%s WHERE id_wbs=%s", (binary, id_wbs))
        db.commit()
        cursor.close()
        db.close()
        return jsonify({"status": "success", "message": "Pendaftaran wajah berhasil. Restart server agar aktif."})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Kesalahan: {e}"}), 500


# --- ROUTE HALAMAN DAFTAR WAJAH ---
@app.route('/daftar_wajah')
def daftar_wajah_page():
    return render_template('daftar_wajah.html')

# --- ROUTE HALAMAN LAPORAN ---
@app.route('/laporan')
def laporan_page():
    return render_template('laporan.html')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
