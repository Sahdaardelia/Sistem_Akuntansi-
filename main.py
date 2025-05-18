import streamlit as st
import sqlite3
import hashlib
from datetime import datetime

# Fungsi untuk membuat koneksi database
def get_db_connection():
    conn = sqlite3.connect('jurnal_umum.db')
    conn.row_factory = sqlite3.Row
    return conn

# Fungsi untuk inisialisasi database dengan mengecek kolom
def init_db():
    conn = get_db_connection()
    
    # Buat tabel users
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Cek apakah tabel transactions sudah ada
    cursor = conn.execute("PRAGMA table_info(transactions)")
    columns = [column[1] for column in cursor.fetchall()]
    
    # Jika tabel belum ada, buat dengan struktur baru
    if 'transactions' not in [table[0] for table in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
        conn.execute('''
            CREATE TABLE transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tanggal INTEGER NOT NULL,
                bulan INTEGER NOT NULL,
                tahun INTEGER NOT NULL,
                akun_debit TEXT NOT NULL,
                jenis_debit TEXT NOT NULL,
                nominal_debit REAL NOT NULL,
                akun_kredit TEXT NOT NULL,
                jenis_kredit TEXT NOT NULL,
                nominal_kredit REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
    else:
        # Jika tabel sudah ada, tambahkan kolom yang belum ada
        if 'jenis_debit' not in columns:
            conn.execute("ALTER TABLE transactions ADD COLUMN jenis_debit TEXT NOT NULL DEFAULT 'Aktiva'")
        if 'jenis_kredit' not in columns:
            conn.execute("ALTER TABLE transactions ADD COLUMN jenis_kredit TEXT NOT NULL DEFAULT 'Utang'")
    
    conn.commit()
    conn.close()

# Fungsi untuk hash password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Inisialisasi database saat aplikasi dimulai
init_db()

def main():
    st.title("Sistem Akuntansi")

    # Inisialisasi session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None

    # Daftar jenis akun
    JENIS_AKUN = ["Aktiva", "Utang", "Modal", "Pendapatan", "Beban"]

    # Belum login
    if not st.session_state.logged_in:
        menu = st.selectbox("Menu", ["Login", "Daftar"])

        if menu == "Login":
            st.subheader("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")

            if st.button("Login"):
                conn = get_db_connection()
                user = conn.execute(
                    'SELECT * FROM users WHERE username = ?', 
                    (username,)
                ).fetchone()
                conn.close()

                if user and user['password'] == hash_password(password):
                    st.session_state.logged_in = True
                    st.session_state.user_id = user['id']
                    st.session_state.username = user['username']
                    st.success("Login berhasil!")
                    st.rerun()
                else:
                    st.error("Username atau password salah")

        else:  # Daftar
            st.subheader("Daftar Akun Baru")
            new_username = st.text_input("Username Baru")
            new_password = st.text_input("Password Baru", type="password")
            confirm_password = st.text_input("Konfirmasi Password", type="password")

            if st.button("Daftar"):
                if new_password != confirm_password:
                    st.error("Password tidak cocok")
                elif len(new_password) < 6:
                    st.error("Password minimal 6 karakter")
                else:
                    conn = get_db_connection()
                    try:
                        conn.execute(
                            'INSERT INTO users (username, password) VALUES (?, ?)',
                            (new_username, hash_password(new_password))
                        )
                        conn.commit()
                        st.success("Pendaftaran berhasil! Silakan login")
                    except sqlite3.IntegrityError:
                        st.error("Username sudah terdaftar")
                    finally:
                        conn.close()
    else:
        # Sudah login
        st.subheader(f"Selamat datang, {st.session_state.username}!")

        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.rerun()

        # Menu navigasi setelah login
        menu_options = ["Riwayat Transaksi", "Buku Besar", "Neraca Saldo", "Informasi"]
        selected_menu = st.selectbox("Pilih Menu", menu_options)

        # === INPUT TRANSAKSI ===
        st.write("### Input Transaksi Jurnal Umum")
        with st.form("input_transaksi", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                tanggal = st.number_input("Tanggal", min_value=1, max_value=31, step=1)
            with col2:
                bulan = st.number_input("Bulan", min_value=1, max_value=12, step=1)
            with col3:
                tahun = st.number_input("Tahun", min_value=2000, max_value=2100, step=1)

            st.subheader("Akun Debit")
            col1, col2 = st.columns(2)
            with col1:
                akun_debit = st.text_input("Nama Akun Debit")
            with col2:
                jenis_debit = st.selectbox("Jenis Akun Debit", JENIS_AKUN, key="jenis_debit")
            nominal_debit = st.number_input("Nominal Debit", min_value=0.0, format="%.2f")

            st.subheader("Akun Kredit")
            col1, col2 = st.columns(2)
            with col1:
                akun_kredit = st.text_input("Nama Akun Kredit")
            with col2:
                jenis_kredit = st.selectbox("Jenis Akun Kredit", JENIS_AKUN, key="jenis_kredit")
            nominal_kredit = st.number_input("Nominal Kredit", min_value=0.0, format="%.2f")

            submitted = st.form_submit_button("Simpan Transaksi")
            if submitted:
                if nominal_debit != nominal_kredit:
                    st.error("Nominal debit dan kredit harus sama")
                else:
                    conn = get_db_connection()
                    conn.execute(
                        '''
                        INSERT INTO transactions 
                        (user_id, tanggal, bulan, tahun, 
                         akun_debit, jenis_debit, nominal_debit, 
                         akun_kredit, jenis_kredit, nominal_kredit)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''',
                        (st.session_state.user_id, tanggal, bulan, tahun, 
                         akun_debit, jenis_debit, nominal_debit, 
                         akun_kredit, jenis_kredit, nominal_kredit)
                    )
                    conn.commit()
                    conn.close()
                    st.success("Transaksi berhasil disimpan.")

        # === RIWAYAT TRANSAKSI ===
        if selected_menu == "Riwayat Transaksi":
            st.header("Riwayat Transaksi")
            conn = get_db_connection()
            transactions = conn.execute(
                '''
                SELECT tanggal, bulan, tahun, 
                       akun_debit, jenis_debit, nominal_debit, 
                       akun_kredit, jenis_kredit, nominal_kredit 
                FROM transactions 
                WHERE user_id = ?
                ORDER BY tahun DESC, bulan DESC, tanggal DESC
                ''',
                (st.session_state.user_id,)
            ).fetchall()
            conn.close()

            if transactions:
                for t in transactions:
                    st.write(f"{t['tanggal']:02d}-{t['bulan']:02d}-{t['tahun']} | "
                             f"Debit: {t['akun_debit']} ({t['jenis_debit']}) {t['nominal_debit']:.2f} | "
                             f"Kredit: {t['akun_kredit']} ({t['jenis_kredit']}) {t['nominal_kredit']:.2f}")
            else:
                st.info("Belum ada transaksi.")

        # === BUKU BESAR ===
        elif selected_menu == "Buku Besar":
            st.header("Buku Besar")
            
            conn = get_db_connection()
            
            # Ambil semua akun unik dengan jenisnya
            akun_data = conn.execute(
                '''
                SELECT akun_debit as akun, jenis_debit as jenis FROM transactions WHERE user_id = ?
                UNION
                SELECT akun_kredit as akun, jenis_kredit as jenis FROM transactions WHERE user_id = ?
                ''',
                (st.session_state.user_id, st.session_state.user_id)
            ).fetchall()
            
            # Buat dictionary untuk menyimpan jenis akun
            akun_jenis = {a['akun']: a['jenis'] for a in akun_data}
            
            if not akun_jenis:
                st.warning("Belum ada transaksi yang dicatat.")
                conn.close()
                return
                
            # Tampilkan buku besar untuk semua akun
            for akun, jenis in akun_jenis.items():
                st.subheader(f"Akun: {akun} ({jenis})")
                
                # Tentukan saldo normal dengan benar
                if jenis in ["Aktiva", "Beban"]:
                    saldo_normal = "Debit"
                elif jenis in  ["Utang", "Modal", "Pendapatan"]:
                    saldo_normal = "Kredit"
                    
                st.caption(f"Saldo Normal: {saldo_normal}")
                
                # Ambil transaksi untuk akun ini
                transactions = conn.execute(
                    '''
                    SELECT tanggal, bulan, tahun, 
                        akun_debit, nominal_debit, 
                        akun_kredit, nominal_kredit 
                    FROM transactions 
                    WHERE user_id = ? AND (akun_debit = ? OR akun_kredit = ?)
                    ORDER BY tahun, bulan, tanggal
                    ''',
                    (st.session_state.user_id, akun, akun)
                ).fetchall()
                
                if not transactions:
                    st.write("Tidak ada transaksi untuk akun ini.")
                    continue
                
                # Hitung saldo
                saldo = 0.0
                
                # Header tabel
                cols = st.columns([1, 2, 2, 2, 2])
                with cols[0]: st.write("Tanggal")
                with cols[1]: st.write("Keterangan")
                with cols[2]: st.write("Debit")
                with cols[3]: st.write("Kredit")
                with cols[4]: st.write("Saldo")
                
                for t in transactions:
                    tanggal_str = f"{t['tanggal']:02d}/{t['bulan']:02d}/{t['tahun']}"
                    
                    if t['akun_debit'] == akun:
                        # Transaksi debit ke akun ini
                        jumlah = t['nominal_debit']
                        posisi = "Debit"
                        keterangan = f"Dari {t['akun_kredit']}"
                        
                        # Update saldo berdasarkan saldo normal
                        if saldo_normal == "Debit":
                            saldo += jumlah
                        else:
                            saldo -= jumlah
                    else:
                        # Transaksi kredit dari akun ini
                        jumlah = t['nominal_kredit']
                        posisi = "Kredit"
                        keterangan = f"Ke {t['akun_debit']}"
                        
                        # Update saldo berdasarkan saldo normal
                        if saldo_normal == "Kredit":
                            saldo += jumlah
                        else:
                            saldo -= jumlah
                    
                    # Tampilkan baris transaksi
                    cols = st.columns([1, 2, 2, 2, 2])
                    with cols[0]: st.write(tanggal_str)
                    with cols[1]: st.write(keterangan)
                    with cols[2]: st.write(f"{jumlah:.2f}" if posisi == "Debit" else "-")
                    with cols[3]: st.write(f"{jumlah:.2f}" if posisi == "Kredit" else "-")
                    with cols[4]: st.write(f"{saldo:.2f}")

                    # biar ada tabelnya
                    saldo_str = f"{abs(saldo):.2f}"
                    st.write("---")
            
            conn.close()
        
        # === NERACA SALDO ===
        elif selected_menu == "Neraca Saldo":
            st.header("📊 Neraca Saldo")
            
            conn = get_db_connection()
            
            # Ambil semua akun unik dengan jenisnya
            akun_data = conn.execute(
                '''
                SELECT akun_debit as akun, jenis_debit as jenis FROM transactions WHERE user_id = ?
                UNION
                SELECT akun_kredit as akun, jenis_kredit as jenis FROM transactions WHERE user_id = ?
                ''',
                (st.session_state.user_id, st.session_state.user_id)
            ).fetchall()
            
            if not akun_data:
                st.warning("Belum ada transaksi yang dicatat.")
                conn.close()
                return
            
            # Hitung saldo setiap akun
            data = []
            total_debit = 0
            total_kredit = 0
            
            for akun in akun_data:
                akun_name = akun['akun']
                jenis = akun['jenis']
                
                # Hitung total debit
                debit = conn.execute(
                    'SELECT COALESCE(SUM(nominal_debit), 0) FROM transactions WHERE user_id = ? AND akun_debit = ?',
                    (st.session_state.user_id, akun_name)
                ).fetchone()[0]
                
                # Hitung total kredit
                kredit = conn.execute(
                    'SELECT COALESCE(SUM(nominal_kredit), 0) FROM transactions WHERE user_id = ? AND akun_kredit = ?',
                    (st.session_state.user_id, akun_name)
                ).fetchone()[0]
                
                # Tentukan saldo normal
                if jenis in ["Aktiva", "Beban"]:
                    saldo = debit - kredit
                    saldo_normal = "Debit"
                else:  # Utang, Modal, Pendapatan
                    saldo = kredit - debit
                    saldo_normal = "Kredit"
                
                # Format untuk tabel
                if saldo >= 0:
                    if saldo_normal == "Debit":
                        row = {
                            "Akun": f"{akun_name} ({jenis})",
                            "Debit": f"{saldo:,.2f}",
                            "Kredit": "0.00"
                        }
                        total_debit += saldo
                    else:
                        row = {
                            "Akun": f"{akun_name} ({jenis})",
                            "Debit": "0.00",
                            "Kredit": f"{saldo:,.2f}"
                        }
                        total_kredit += saldo
                else:
                    if saldo_normal == "Debit":
                        row = {
                            "Akun": f"{akun_name} ({jenis})",
                            "Debit": "0.00",
                            "Kredit": f"{-saldo:,.2f}"
                        }
                        total_kredit += -saldo
                    else:
                        row = {
                            "Akun": f"{akun_name} ({jenis})",
                            "Debit": f"{-saldo:,.2f}",
                            "Kredit": "0.00"
                        }
                        total_debit += -saldo
                
                data.append(row)
            
            # Tambahkan baris total 
            data.append({
                "Akun": "TOTAL",
                "Debit": f"{total_debit:,.2f}",
                "Kredit": f"{total_kredit:,.2f}"
            })
            
            # Tampilkan tabel
            st.dataframe(
                data,
                column_config={
                    "Akun": st.column_config.TextColumn("Akun", width="medium"),
                    "Debit": st.column_config.NumberColumn("Debit", format="%.2f"),
                    "Kredit": st.column_config.NumberColumn("Kredit", format="%.2f")
                },
                hide_index=True,
                width=700
            )
            
            # Validasi keseimbangan
            if abs(total_debit - total_kredit) < 0.01:
                st.success("✅ Neraca seimbang (Total Debit = Total Kredit)")
            else:
                st.error(f"❌ Neraca tidak seimbang! Selisih: {abs(total_debit - total_kredit):.2f}")
            
            conn.close()

        # === INFORMASI ===
        elif selected_menu == "Informasi":
            st.header("ℹ️ Informasi Aplikasi")
            conn = get_db_connection()
            
            # 1. Logo dan Deskripsi Aplikasi
            with st.container():
                col1, col2 = st.columns([1, 3])
                with col1:
                    try:
                        st.image("logo_aplikasi.jpg", width=150, caption="Purple Book")
                    except FileNotFoundError:
                        st.error("File 'logo_aplikasi.jpg' tidak ditemukan. Pastikan file ada di folder yang sama dengan script ini.")
                with col2:
                    st.subheader("Purple Book")
                    st.write("Aplikasi akuntansi berbasis web untuk UKM")
                    st.write("""
                    - Sistem ini dibuat untuk tugas mata kuliah SIM
                    - Fokus pada transaksi pertanian (petani terong)
                    - Buku besar dan neraca dibuat otomatis
                    """)
            
            st.divider()
            
            # 2. Hasil Survey
            st.subheader("📊 Data Petani Terong")
            st.write("**Narasumber**: Bapak Tito Tarwoco")
            st.write("**Lokasi**: Desa Sarwogadung, Mirit, Kebumen")
            st.write("**Jenis Terong**: M72 (panen 2x/minggu)")
            st.write("**Harga**: Rp4.500/kg")
            
            st.divider()
         
            # 3. Tim Pengembang
            st.subheader("👩‍💻 Tim Pengembang")
            
            # Data tim (pastikan file gambar ada)
            team_data = [
                {"nama": "Sahda Ardelia Artanti", "foto": "team1.jpg"},
                {"nama": "Haura Hana K. M.", "foto": "team2.jpg"},
                {"nama": "Khansa Raudatul H.", "foto": "team3.jpg"}
            ]
            
            cols = st.columns(3)
            for i, member in enumerate(team_data):
                with cols[i]:
                    try:
                        st.image(member["foto"], width=150, caption=member["nama"])
                    except FileNotFoundError:
                        st.error(f"File '{member['foto']}' tidak ditemukan")
                    st.write(f"**{member['nama']}**")
            
            st.divider()
            
            # 4. Panduan Singkat
            st.subheader("📚 Cara Penggunaan")
            st.write("""
            1. **Input Transaksi**:  
            - Isi tanggal, akun debit/kredit, dan nominal
            - Pastikan debit = kredit
            2. **Buku Besar**:  
            - Otomatis terupdate setelah input transaksi
            3. **Neraca Saldo**:  
            - Cek keseimbangan debit-kredit
            """)
            
            # Footer
            st.caption("© 2024 Purple Book - Versi 1.0")

if __name__ == "__main__":
    main()
