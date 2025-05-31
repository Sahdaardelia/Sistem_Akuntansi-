import streamlit as st
import sqlite3
import hashlib
from datetime import datetime

DB_PATH = "accounting_system.db"

# Fungsi untuk membuat koneksi ke database dengan timeout dan row factory
def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

# Fungsi inisialisasi database dan membuat tabel jika belum ada
def init_db():
    with get_db_connection() as conn:
        # Tabel users untuk menyimpan data pengguna
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabel transactions untuk menyimpan data transaksi jurnal umum
        conn.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
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

        # Tabel inventory untuk menyimpan data persediaan barang
        conn.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                nama TEXT NOT NULL,
                jumlah INTEGER NOT NULL,
                harga_satuan REAL NOT NULL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

# Fungsi untuk hash password menggunakan SHA256
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Fungsi untuk mendaftarkan pengguna baru
def register_user(username, password):
    with get_db_connection() as conn:
        try:
            conn.execute(
                'INSERT INTO users (username, password) VALUES (?, ?)',
                (username, hash_password(password))
            )
            return True, "Pendaftaran berhasil! Silakan login."
        except sqlite3.IntegrityError:
            return False, "Username sudah terdaftar."

# Fungsi verifikasi login pengguna
def login_user(username, password):
    with get_db_connection() as conn:
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    if user and user['password'] == hash_password(password):
        return True, user['id'], user['username']
    else:
        return False, None, None

# Fungsi untuk memasukkan transaksi baru ke database
def insert_transaction(user_id, tanggal, bulan, tahun,
                       akun_debit, jenis_debit, nominal_debit,
                       akun_kredit, jenis_kredit, nominal_kredit):
    with get_db_connection() as conn:
        conn.execute('''
            INSERT INTO transactions 
            (user_id, tanggal, bulan, tahun,
             akun_debit, jenis_debit, nominal_debit,
             akun_kredit, jenis_kredit, nominal_kredit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, tanggal, bulan, tahun,
              akun_debit, jenis_debit, nominal_debit,
              akun_kredit, jenis_kredit, nominal_kredit)
        )

# Fungsi untuk mengambil data transaksi pengguna
def get_transactions(user_id):
    with get_db_connection() as conn:
        transactions = conn.execute('''
            SELECT tanggal, bulan, tahun, akun_debit, jenis_debit, nominal_debit,
                   akun_kredit, jenis_kredit, nominal_kredit
            FROM transactions
            WHERE user_id = ?
            ORDER BY tahun DESC, bulan DESC, tanggal DESC
        ''', (user_id,)).fetchall()
    return transactions

# Fungsi untuk menambahkan data persediaan baru
def insert_inventory(user_id, nama, jumlah, harga_satuan):
    with get_db_connection() as conn:
        conn.execute('''
            INSERT INTO inventory (user_id, nama, jumlah, harga_satuan)
            VALUES (?, ?, ?, ?)
        ''', (user_id, nama, jumlah, harga_satuan))

# Fungsi untuk mengambil daftar persediaan pengguna
def get_inventory(user_id):
    with get_db_connection() as conn:
        items = conn.execute('''
            SELECT id, nama, jumlah, harga_satuan
            FROM inventory
            WHERE user_id = ?
            ORDER BY nama ASC
        ''', (user_id,)).fetchall()
    return items

# Fungsi untuk memperbarui data persediaan
def update_inventory_item(item_id, jumlah, harga_satuan):
    with get_db_connection() as conn:
        conn.execute('''
            UPDATE inventory SET jumlah = ?, harga_satuan = ? WHERE id = ?
        ''', (jumlah, harga_satuan, item_id))

# Fungsi utama aplikasi Streamlit
def main():
    st.set_page_config(page_title="Sistem Akuntansi", page_icon="logo_aplikasi.jpg", layout="centered")
    st.title("Sistem Akuntansi")

    # Inisialisasi variabel session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'username' not in st.session_state:
        st.session_state.username = ""

    JENIS_AKUN = ["Aktiva", "Utang", "Modal", "Pendapatan", "Beban", "Prive"]

    # Jika belum login, tampilkan form Login dan Daftar
    if not st.session_state.logged_in:
        menu = st.selectbox("Menu", options=["Login", "Daftar Akun Baru"])

        if menu == "Login":
            st.subheader("🔐 Login")
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login"):
                success, user_id, username_ = login_user(username.strip(), password)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_id
                    st.session_state.username = username_
                    st.success(f"Selamat datang, {username_}!")
                    st.rerun()
                else:
                    st.error("Username atau password salah.")
        else:
            st.subheader("📝 Daftar Akun Baru")
            new_username = st.text_input("Username Baru", key="reg_username")
            new_password = st.text_input("Password Baru", type="password", key="reg_password")
            confirm_password = st.text_input("Konfirmasi Password", type="password", key="reg_confirm_password")
            if st.button("Daftar"):
                if not new_username.strip():
                    st.error("Username tidak boleh kosong.")
                elif len(new_password) < 6:
                    st.error("Password minimal 6 karakter.")
                elif new_password != confirm_password:
                    st.error("Password dan konfirmasi tidak cocok.")
                else:
                    success, message = register_user(new_username.strip(), new_password)
                    if success:
                        st.success(message)
                        st.info("Silakan login menggunakan akun baru Anda.")
                    else:
                        st.error(message)

    else:
        # setelah login berhasil
        st.sidebar.write(f"👤 Logged in sebagai: **{st.session_state.username}**")
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.username = ""
            st.rerun()

        menu_options = [
            "Input Transaksi", "Persediaan", "Riwayat Transaksi", "Buku Besar", 
            "Neraca Saldo", "Laporan Laba Rugi", 
            "Laporan Perubahan Modal", "Neraca", "Informasi"
        ]
        selected_menu = st.sidebar.selectbox("Menu", menu_options)

        # memilih input transaksi
        if selected_menu == "Input Transaksi":
            st.header("🧾 Input Transaksi Jurnal Umum")
            with st.form("form_input_transaksi", clear_on_submit=True):
                col1, col2, col3 = st.columns(3)
                tanggal = col1.number_input("Tanggal", min_value=1, max_value=31, value=1)
                bulan = col2.number_input("Bulan", min_value=1, max_value=12, value=1)
                tahun = col3.number_input("Tahun", min_value=2000, max_value=2100, value=2024)

                st.subheader("Akun Debit")
                akun_debit = st.text_input("Nama Akun Debit")
                jenis_debit = st.selectbox("Jenis Akun Debit", JENIS_AKUN, key="jenis_debit_input")
                nominal_debit = st.number_input("Nominal Debit", min_value=0.0, format="%.2f")

                st.subheader("Akun Kredit")
                akun_kredit = st.text_input("Nama Akun Kredit")
                jenis_kredit = st.selectbox("Jenis Akun Kredit", JENIS_AKUN, key="jenis_kredit_input")
                nominal_kredit = st.number_input("Nominal Kredit", min_value=0.0, format="%.2f")

                submitted = st.form_submit_button("Simpan Transaksi")
                if submitted:
                    if nominal_debit != nominal_kredit:
                        st.error("Nominal debit dan kredit harus sama.")
                    elif not akun_debit.strip() or not akun_kredit.strip():
                        st.error("Nama akun debit dan kredit harus diisi.")
                    else:
                        insert_transaction(st.session_state.user_id, tanggal, bulan, tahun,
                                           akun_debit.strip(), jenis_debit, nominal_debit,
                                           akun_kredit.strip(), jenis_kredit, nominal_kredit)
                        st.success("Transaksi berhasil disimpan.")

        # memilih menu riwayat transaksi
        elif selected_menu == "Riwayat Transaksi":
            st.header("📜 Riwayat Transaksi")
            transactions = get_transactions(st.session_state.user_id)
            if not transactions:
                st.info("Belum ada transaksi.")
            else:
                for t in transactions:
                    st.write(
                        f"{t['tanggal']:02d}-{t['bulan']:02d}-{t['tahun']} | "
                        f"Debit: {t['akun_debit']} ({t['jenis_debit']}) Rp{t['nominal_debit']:,.2f} | "
                        f"Kredit: {t['akun_kredit']} ({t['jenis_kredit']}) Rp{t['nominal_kredit']:,.2f}"
                    )
        #memilih manajemen persediaan
#memilih manajemen persediaan
        elif selected_menu == "Persediaan":
            st.header("📦 Manajemen Persediaan")
            
            # Tab untuk berbagai fungsi
            tab1, tab2, tab3 = st.tabs(["Stok Akhir", "Operasi", "Detail & Rata-rata"])
            
            with tab1:
                st.subheader("Stok Akhir Persediaan")
                inventory_items = get_inventory(st.session_state.user_id)
                
                if not inventory_items:
                    st.info("Belum ada data persediaan.")
                else:
                    # Tampilkan hanya 1 barang jika semua barang sama (berdasarkan nama)
                    unique_items = set(item['nama'] for item in inventory_items)
                    
                    if len(unique_items) == 1:
                        item = inventory_items[0]
                        st.markdown(f"""
                        - *Nama Barang:* {item['nama']}
                        - *Stok Akhir:* {item['jumlah']} unit
                        - *Harga Satuan:* Rp{item['harga_satuan']:,.2f}
                        - *Total Nilai:* Rp{item['jumlah'] * item['harga_satuan']:,.2f}
                        """)
                    else:
                        # Jika ada multiple items, tampilkan semua
                        data = []
                        for item in inventory_items:
                            data.append([
                                item['nama'],
                                item['jumlah'],
                                f"Rp{item['harga_satuan']:,.2f}",
                                f"Rp{item['jumlah'] * item['harga_satuan']:,.2f}"
                            ])
                        
                        import pandas as pd
                        df = pd.DataFrame(data, columns=["Nama Barang", "Stok Akhir", "Harga Satuan", "Total Nilai"])
                        st.dataframe(df, hide_index=True, use_container_width=True)
            
            with tab2:
                st.subheader("Operasi Persediaan")
                operation = st.radio("Pilih Operasi:", ["Tambah Barang", "Tambah Stok", "Kurangi Stok"], horizontal=True)
                
                if operation == "Tambah Barang":
                    with st.form("form_add_item", clear_on_submit=True):
                        nama = st.text_input("Nama Barang Baru")
                        jumlah = st.number_input("Jumlah Awal", min_value=0, step=1, value=0)
                        harga_satuan = st.number_input("Harga Satuan (Rp)", min_value=0.0, step=1000.0, format="%.2f", value=0.0)

                        if st.form_submit_button("Simpan Barang Baru"):
                            if not nama.strip():
                                st.error("Nama barang wajib diisi!")
                            elif harga_satuan <= 0:
                                st.error("Harga satuan harus lebih dari 0")
                            else:
                                insert_inventory(st.session_state.user_id, nama.strip(), jumlah, harga_satuan)
                                st.success("Barang baru berhasil ditambahkan!")
                                st.rerun()
                
                elif operation == "Tambah Stok":
                    inventory_items = get_inventory(st.session_state.user_id)
                    if not inventory_items:
                        st.info("Belum ada data persediaan.")
                    else:
                        with st.form("form_add_stock"):
                            selected_item = st.selectbox(
                                "Pilih Barang",
                                options=[item['nama'] for item in inventory_items],
                                key="add_stock_select"
                            )
                            add_amount = st.number_input("Jumlah yang Ditambahkan", min_value=1, step=1)
                            new_price = st.number_input("Harga Satuan Baru (kosongi jika tidak berubah)", 
                                                    min_value=0.0, format="%.2f", value=0.0)
                            
                            if st.form_submit_button("Tambah Stok"):
                                selected_item_data = next((item for item in inventory_items if item['nama'] == selected_item), None)
                                if selected_item_data:
                                    # Jika harga baru tidak diisi, gunakan harga lama
                                    updated_price = new_price if new_price > 0 else selected_item_data['harga_satuan']
                                    new_amount = selected_item_data['jumlah'] + add_amount
                                    update_inventory_item(selected_item_data['id'], new_amount, updated_price)
                                    
                                    # Catat transaksi penambahan stok
                                    tanggal_now = datetime.now().day
                                    bulan_now = datetime.now().month
                                    tahun_now = datetime.now().year
                                    
                                    insert_transaction(
                                        st.session_state.user_id,
                                        tanggal_now, bulan_now, tahun_now,
                                        "Persediaan Barang", "Aktiva", add_amount * updated_price,
                                        "Kas", "Aktiva", add_amount * updated_price
                                    )
                                    
                                    st.success(f"Berhasil menambah {add_amount} {selected_item} ke persediaan.")
                                    st.rerun()
                
                else:  # Kurangi Stok
                    inventory_items = get_inventory(st.session_state.user_id)
                    if not inventory_items:
                        st.info("Belum ada data persediaan.")
                    else:
                        with st.form("form_reduce_stock"):
                            selected_item = st.selectbox(
                                "Pilih Barang",
                                options=[item['nama'] for item in inventory_items],
                                key="reduce_stock_select"
                            )
                            reduce_amount = st.number_input("Jumlah yang Dikurangi", min_value=1, step=1)
                            reason = st.text_input("Alasan Pengurangan")
                            
                            if st.form_submit_button("Kurangi Stok"):
                                selected_item_data = next((item for item in inventory_items if item['nama'] == selected_item), None)
                                if selected_item_data:
                                    if reduce_amount > selected_item_data['jumlah']:
                                        st.error(f"Jumlah melebihi stok! Stok tersedia: {selected_item_data['jumlah']}")
                                    else:
                                        new_amount = selected_item_data['jumlah'] - reduce_amount
                                        update_inventory_item(selected_item_data['id'], new_amount, selected_item_data['harga_satuan'])
                                        
                                        # Catat transaksi pengurangan stok
                                        tanggal_now = datetime.now().day
                                        bulan_now = datetime.now().month
                                        tahun_now = datetime.now().year
                                        
                                        insert_transaction(
                                            st.session_state.user_id,
                                            tanggal_now, bulan_now, tahun_now,
                                            "Beban Persediaan", "Beban", reduce_amount * selected_item_data['harga_satuan'],
                                            "Persediaan Barang", "Aktiva", reduce_amount * selected_item_data['harga_satuan']
                                        )
                                        
                                        st.success(f"Berhasil mengurangi {reduce_amount} {selected_item} dari persediaan.")
                                        st.info(f"Alasan: {reason}")
                                        st.rerun()
            
            with tab3:
                st.subheader("Detail & Perhitungan Rata-rata")
                inventory_items = get_inventory(st.session_state.user_id)
                
                if not inventory_items:
                    st.info("Belum ada data persediaan.")
                else:
                    selected_item = st.selectbox(
                        "Pilih Barang untuk Detail",
                        options=[item['nama'] for item in inventory_items],
                        key="detail_item_select"
                    )
                    
                    selected_item_data = next((item for item in inventory_items if item['nama'] == selected_item), None)
                    
                    if selected_item_data:
                        # Informasi dasar
                        st.markdown(f"""
                        ### Informasi Barang
                        - *Nama Barang:* {selected_item_data['nama']}
                        - *Stok Akhir:* {selected_item_data['jumlah']} unit
                        - *Harga Satuan Terakhir:* Rp{selected_item_data['harga_satuan']:,.2f}
                        - *Nilai Persediaan:* Rp{selected_item_data['jumlah'] * selected_item_data['harga_satuan']:,.2f}
                        """)
                        
                        # Perhitungan rata-rata sederhana (persediaan awal + persediaan akhir dibagi 2)
                        st.markdown("""
                        ### Perhitungan Rata-rata Sederhana
                        (Persediaan Awal + Persediaan Akhir) / 2
                        """)
                        
                        # Asumsikan persediaan awal adalah data pertama yang dimasukkan
                        # Dalam implementasi nyata, Anda perlu menyimpan persediaan awal
                        persediaan_awal = {
                            'jumlah': 0,  # Default 0 jika tidak ada data awal
                            'harga': selected_item_data['harga_satuan']  # Gunakan harga saat ini sebagai default
                        }
                        
                        # Hitung rata-rata
                        total_jumlah = persediaan_awal['jumlah'] + selected_item_data['jumlah']
                        total_nilai = (persediaan_awal['jumlah'] * persediaan_awal['harga']) + (selected_item_data['jumlah'] * selected_item_data['harga_satuan'])
                        
                        if total_jumlah > 0:
                            rata_rata = total_nilai / total_jumlah
                            st.write(f"- *Persediaan Awal:* {persediaan_awal['jumlah']} unit @ Rp{persediaan_awal['harga']:,.2f}")
                            st.write(f"- *Persediaan Akhir:* {selected_item_data['jumlah']} unit @ Rp{selected_item_data['harga_satuan']:,.2f}")
                            st.write(f"- *Rata-rata:* Rp{rata_rata:,.2f} per unit")
                            st.write(f"- *Total Unit:* {total_jumlah} unit")
                            st.write(f"- *Total Nilai:* Rp{total_nilai:,.2f}")
                        else:
                            st.warning("Tidak ada data persediaan untuk menghitung rata-rata")

        # === BUKU BESAR ===
        elif selected_menu == "Buku Besar":
            st.header("Buku Besar")
            
            conn = get_db_connection()
            
            # Ambil semua akun dengan jenisnya
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

        # === LAPORAN LABA RUGI ===
        elif selected_menu == "Laporan Laba Rugi":
            st.header("📈 Laporan Laba Rugi")
            
            conn = get_db_connection()
            
            # 1. Hitung Total Pendapatan (semua akun jenis Pendapatan)
            st.subheader("Pendapatan")
            
            # Pendapatan di kredit (normal) dan pendapatan di debit (pengurangan)
            pendapatan_kredit = conn.execute(
                '''
                SELECT akun_kredit as nama_akun, SUM(nominal_kredit) as total 
                FROM transactions 
                WHERE user_id = ? AND jenis_kredit = 'Pendapatan'
                GROUP BY akun_kredit
                ''',
                (st.session_state.user_id,)
            ).fetchall()
            
            pendapatan_debit = conn.execute(
                '''
                SELECT akun_debit as nama_akun, SUM(nominal_debit) as total 
                FROM transactions 
                WHERE user_id = ? AND jenis_debit = 'Pendapatan'
                GROUP BY akun_debit
                ''',
                (st.session_state.user_id,)
            ).fetchall()
            
            # Gabungkan semua pendapatan
            pendapatan_dict = {}
            for item in pendapatan_kredit:
                pendapatan_dict[item['nama_akun']] = pendapatan_dict.get(item['nama_akun'], 0) + item['total']
            
            for item in pendapatan_debit:
                pendapatan_dict[item['nama_akun']] = pendapatan_dict.get(item['nama_akun'], 0) - item['total']
            
            # Tampilkan detail pendapatan
            total_pendapatan = 0
            for akun, nominal in pendapatan_dict.items():
                if nominal != 0:
                    st.write(f"- {akun}: Rp{nominal:,.2f}" if nominal > 0 else f"- {akun}: (Rp{abs(nominal):,.2f})")
                    total_pendapatan += nominal
            
            st.write(f"Total Pendapatan: Rp{total_pendapatan:,.2f}" if total_pendapatan >= 0 
                    else f"Total Pendapatan: (Rp{abs(total_pendapatan):,.2f})")
            
            # 2. Hitung Total Beban (semua akun jenis Beban)
            st.subheader("\nBeban")
            
            # Beban di debit (normal) dan beban di kredit (pengurangan)
            beban_debit = conn.execute(
                '''
                SELECT akun_debit as nama_akun, SUM(nominal_debit) as total 
                FROM transactions 
                WHERE user_id = ? AND jenis_debit = 'Beban'
                GROUP BY akun_debit
                ''',
                (st.session_state.user_id,)
            ).fetchall()
            
            beban_kredit = conn.execute(
                '''
                SELECT akun_kredit as nama_akun, SUM(nominal_kredit) as total 
                FROM transactions 
                WHERE user_id = ? AND jenis_kredit = 'Beban'
                GROUP BY akun_kredit
                ''',
                (st.session_state.user_id,)
            ).fetchall()
            
            # Gabungkan semua beban
            beban_dict = {}
            for item in beban_debit:
                beban_dict[item['nama_akun']] = beban_dict.get(item['nama_akun'], 0) + item['total']
            
            for item in beban_kredit:
                beban_dict[item['nama_akun']] = beban_dict.get(item['nama_akun'], 0) - item['total']
            
            # Tampilkan detail beban
            total_beban = 0
            for akun, nominal in beban_dict.items():
                if nominal != 0:
                    st.write(f"- {akun}: Rp{nominal:,.2f}" if nominal > 0 else f"- {akun}: (Rp{abs(nominal):,.2f})")
                    total_beban += nominal
            
            st.write(f"Total Beban: Rp{total_beban:,.2f}" if total_beban >= 0 
                    else f"Total Beban: (Rp{abs(total_beban):,.2f})")
            
            # 3. Hitung Laba/Rugi
            st.divider()
            laba_rugi = total_pendapatan - total_beban
            
            if laba_rugi >= 0:
                st.success(f"Laba Bersih: Rp{laba_rugi:,.2f}")
            else:
                st.error(f"Rugi Bersih: (Rp{abs(laba_rugi):,.2f})")
            
            # 4. Tampilkan Logika Perhitungan
            with st.expander("🔍 Detail Perhitungan"):
                st.write("Logika Perhitungan:")
                st.write("- Pendapatan di Kredit (+) dan Pendapatan di Debit (-)")
                st.write("- Beban di Debit (+) dan Beban di Kredit (-)")
                st.write("")
                st.write("Rumus: Laba/Rugi = Total Pendapatan - Total Beban")
            
            conn.close()

        # === LAPORAN PERUBAHAN MODAL ===
        elif selected_menu == "Laporan Perubahan Modal":
            st.header("📊 Laporan Perubahan Modal")
            
            conn = get_db_connection()
            
            # 1. Hitung Modal Awal dari transaksi akun Modal
            st.subheader("Modal Awal")
            
            # Modal di kredit (normal) dan modal di debit (pengurangan)
            modal_kredit = conn.execute(
                '''
                SELECT COALESCE(SUM(nominal_kredit), 0) 
                FROM transactions 
                WHERE user_id = ? AND jenis_kredit = 'Modal' 
                AND akun_kredit NOT LIKE '%prive%' 
                AND akun_kredit NOT LIKE '%tambahan modal%'
                ''',
                (st.session_state.user_id,)
            ).fetchone()[0]
            
            modal_debit = conn.execute(
                '''
                SELECT COALESCE(SUM(nominal_debit), 0) 
                FROM transactions 
                WHERE user_id = ? AND jenis_debit = 'Modal' 
                AND akun_debit NOT LIKE '%prive%' 
                AND akun_debit NOT LIKE '%tambahan modal%'
                ''',
                (st.session_state.user_id,)
            ).fetchone()[0]
            
            modal_awal = modal_kredit - modal_debit
            
            st.write(f"Total Modal Awal: Rp{modal_awal:,.2f}" if modal_awal >= 0 
                    else f"Total Modal Awal: (Rp{abs(modal_awal):,.2f})")
            
            # 2. Hitung Laba/Rugi Berjalan (dari Laporan Laba Rugi)
            st.subheader("\nLaba/Rugi Berjalan")
            
            # Hitung total pendapatan
            pendapatan_kredit = conn.execute(
                'SELECT COALESCE(SUM(nominal_kredit), 0) FROM transactions WHERE user_id = ? AND jenis_kredit = "Pendapatan"',
                (st.session_state.user_id,)
            ).fetchone()[0]
            
            pendapatan_debit = conn.execute(
                'SELECT COALESCE(SUM(nominal_debit), 0) FROM transactions WHERE user_id = ? AND jenis_debit = "Pendapatan"',
                (st.session_state.user_id,)
            ).fetchone()[0]
            total_pendapatan = pendapatan_kredit - pendapatan_debit
            
            # Hitung total beban
            beban_debit = conn.execute(
                'SELECT COALESCE(SUM(nominal_debit), 0) FROM transactions WHERE user_id = ? AND jenis_debit = "Beban"',
                (st.session_state.user_id,)
            ).fetchone()[0]
            
            beban_kredit = conn.execute(
                'SELECT COALESCE(SUM(nominal_kredit), 0) FROM transactions WHERE user_id = ? AND jenis_kredit = "Beban"',
                (st.session_state.user_id,)
            ).fetchone()[0]
            total_beban = beban_debit - beban_kredit
            
            laba_rugi = total_pendapatan - total_beban
            
            st.write(f"Total Laba/Rugi: Rp{laba_rugi:,.2f}" if laba_rugi >= 0 
                    else f"Total Laba/Rugi: (Rp{abs(laba_rugi):,.2f})")
            
            # 3. Hitung Prive (Pengambilan Pribadi)
            st.subheader("\nPrive (Pengambilan Pribadi)")
            prive = conn.execute(
                '''
                SELECT COALESCE(SUM(nominal_debit), 0) 
                FROM transactions 
                WHERE user_id = ? AND jenis_debit = "Modal" 
                AND (akun_debit LIKE "%prive%" OR akun_debit LIKE "%pengambilan pribadi%")
                ''',
                (st.session_state.user_id,)
            ).fetchone()[0]
            
            st.write(f"Total Prive: Rp{prive:,.2f}")
            
            
            
            # 5. Hitung Modal Akhir
            st.divider()
            modal_akhir = modal_awal + laba_rugi - prive
            
            # Tampilkan dalam bentuk tabel
            data = [
                {"Keterangan": "Modal Awal", "Nominal": f"Rp{modal_awal:,.2f}"},
                {"Keterangan": "Laba/Rugi Berjalan", "Nominal": f"Rp{laba_rugi:,.2f}" if laba_rugi >= 0 else f"(Rp{abs(laba_rugi):,.2f})"},
                {"Keterangan": "Prive", "Nominal": f"(Rp{prive:,.2f})"},
                {"Keterangan": "Modal Akhir", "Nominal": f"Rp{modal_akhir:,.2f}"}
            ]
            
            st.dataframe(
                data,
                column_config={
                    "Keterangan": st.column_config.TextColumn("Keterangan", width="medium"),
                    "Nominal": st.column_config.TextColumn("Nominal", width="medium")
                },
                hide_index=True,
                width=600
            )
            
            conn.close()

        # === NERACA ===
        elif selected_menu == "Neraca":
            st.header("📋 Neraca")
            st.write(f"Per {datetime.now().strftime('%d/%m/%Y')}")
            
            conn = get_db_connection()
            
            # ===== ASET =====
            st.subheader("Aktiva (Aset)")
            
            # 1. Aset Lancar
            st.markdown("Aset Lancar")
            
            # Kas
            kas_kredit = conn.execute(
                'SELECT COALESCE(SUM(nominal_kredit), 0) FROM transactions WHERE user_id = ? AND jenis_kredit = "Aktiva" AND akun_kredit LIKE "%kas%"',
                (st.session_state.user_id,)
            ).fetchone()[0]
            
            kas_debit = conn.execute(
                'SELECT COALESCE(SUM(nominal_debit), 0) FROM transactions WHERE user_id = ? AND jenis_debit = "Aktiva" AND akun_debit LIKE "%kas%"',
                (st.session_state.user_id,)
            ).fetchone()[0]
            saldo_kas = kas_debit - kas_kredit
            st.write(f"- Kas: Rp{saldo_kas:,.2f}")
            
            # Piutang Usaha
            piutang_kredit = conn.execute(
                'SELECT COALESCE(SUM(nominal_kredit), 0) FROM transactions WHERE user_id = ? AND jenis_kredit = "Aktiva" AND akun_kredit LIKE "%piutang%"',
                (st.session_state.user_id,)
            ).fetchone()[0]
            
            piutang_debit = conn.execute(
                'SELECT COALESCE(SUM(nominal_debit), 0) FROM transactions WHERE user_id = ? AND jenis_debit = "Aktiva" AND akun_debit LIKE "%piutang%"',
                (st.session_state.user_id,)
            ).fetchone()[0]
            saldo_piutang = piutang_debit - piutang_kredit
            st.write(f"- Piutang Usaha: Rp{saldo_piutang:,.2f}")
            
            # Persediaan
            persediaan_kredit = conn.execute(
                'SELECT COALESCE(SUM(nominal_kredit), 0) FROM transactions WHERE user_id = ? AND jenis_kredit = "Aktiva" AND akun_kredit LIKE "%persediaan%"',
                (st.session_state.user_id,)
            ).fetchone()[0]
            
            persediaan_debit = conn.execute(
                'SELECT COALESCE(SUM(nominal_debit), 0) FROM transactions WHERE user_id = ? AND jenis_debit = "Aktiva" AND akun_debit LIKE "%persediaan%"',
                (st.session_state.user_id,)
            ).fetchone()[0]
            saldo_persediaan = persediaan_debit - persediaan_kredit
            st.write(f"- Persediaan: Rp{saldo_persediaan:,.2f}")
            
            # Aset Lancar Lainnya
            aset_lancar_lain = conn.execute(
                '''
                SELECT 
                    COALESCE(SUM(CASE WHEN jenis_debit = 'Aktiva' AND (akun_debit LIKE "%aset lancar%" OR akun_debit LIKE "%biaya dibayar di muka%") THEN nominal_debit ELSE 0 END), 0) -
                    COALESCE(SUM(CASE WHEN jenis_kredit = 'Aktiva' AND (akun_kredit LIKE "%aset lancar%" OR akun_kredit LIKE "%biaya dibayar di muka%") THEN nominal_kredit ELSE 0 END), 0) as saldo
                FROM transactions
                WHERE user_id = ?
                AND (akun_debit NOT LIKE "%kas%" AND akun_debit NOT LIKE "%piutang%" AND akun_debit NOT LIKE "%persediaan%")
                AND (akun_kredit NOT LIKE "%kas%" AND akun_kredit NOT LIKE "%piutang%" AND akun_kredit NOT LIKE "%persediaan%")
                ''',
                (st.session_state.user_id,)
            ).fetchone()[0]
            if aset_lancar_lain != 0:
                st.write(f"- Aset Lancar Lainnya: Rp{aset_lancar_lain:,.2f}")
            
            total_aset_lancar = saldo_kas + saldo_piutang + saldo_persediaan + (aset_lancar_lain if aset_lancar_lain else 0)
            st.write(f"Total Aset Lancar: Rp{total_aset_lancar:,.2f}")
            
            # 2. Aset Tetap
            st.markdown("\n*Aset Tetap*")
            
            # Peralatan
            peralatan_debit = conn.execute(
                'SELECT COALESCE(SUM(nominal_debit), 0) FROM transactions WHERE user_id = ? AND jenis_debit = "Aktiva" AND akun_debit LIKE "%peralatan%"',
                (st.session_state.user_id,)
            ).fetchone()[0]
            
            peralatan_kredit = conn.execute(
                'SELECT COALESCE(SUM(nominal_kredit), 0) FROM transactions WHERE user_id = ? AND jenis_kredit = "Aktiva" AND akun_kredit LIKE "%peralatan%"',
                (st.session_state.user_id,)
            ).fetchone()[0]
            saldo_peralatan = peralatan_debit - peralatan_kredit
            st.write(f"- Peralatan: Rp{saldo_peralatan:,.2f}")
            
            # Akumulasi Penyusutan
            penyusutan_debit = conn.execute(
                'SELECT COALESCE(SUM(nominal_debit), 0) FROM transactions WHERE user_id = ? AND jenis_debit = "Aktiva" AND akun_debit LIKE "%penyusutan%"',
                (st.session_state.user_id,)
            ).fetchone()[0]
            
            penyusutan_kredit = conn.execute(
                'SELECT COALESCE(SUM(nominal_kredit), 0) FROM transactions WHERE user_id = ? AND jenis_kredit = "Aktiva" AND akun_kredit LIKE "%penyusutan%"',
                (st.session_state.user_id,)
            ).fetchone()[0]
            saldo_penyusutan = penyusutan_kredit - penyusutan_debit
            
            st.write(f"- Akumulasi Penyusutan: (Rp{saldo_penyusutan:,.2f})")
            
            # Kendaraan
            kendaraan_debit = conn.execute(
                'SELECT COALESCE(SUM(nominal_debit), 0) FROM transactions WHERE user_id = ? AND jenis_debit = "Aktiva" AND akun_debit LIKE "%kendaraan%"',
                (st.session_state.user_id,)
            ).fetchone()[0]
            
            kendaraan_kredit = conn.execute(
                'SELECT COALESCE(SUM(nominal_kredit), 0) FROM transactions WHERE user_id = ? AND jenis_kredit = "Aktiva" AND akun_kredit LIKE "%kendaraan%"',
                (st.session_state.user_id,)
            ).fetchone()[0]
            saldo_kendaraan = kendaraan_debit - kendaraan_kredit
            st.write(f"- Kendaraan: Rp{saldo_kendaraan:,.2f}")
            
            # Bangunan
            bangunan_debit = conn.execute(
                'SELECT COALESCE(SUM(nominal_debit), 0) FROM transactions WHERE user_id = ? AND jenis_debit = "Aktiva" AND akun_debit LIKE "%bangunan%"',
                (st.session_state.user_id,)
            ).fetchone()[0]
            
            bangunan_kredit = conn.execute(
                'SELECT COALESCE(SUM(nominal_kredit), 0) FROM transactions WHERE user_id = ? AND jenis_kredit = "Aktiva" AND akun_kredit LIKE "%bangunan%"',
                (st.session_state.user_id,)
            ).fetchone()[0]
            saldo_bangunan = bangunan_debit - bangunan_kredit
            st.write(f"- Bangunan: Rp{saldo_bangunan:,.2f}")
            
            total_aset_tetap = saldo_peralatan - saldo_penyusutan + saldo_kendaraan + saldo_bangunan
            st.write(f"Total Aset Tetap: Rp{total_aset_tetap:,.2f}")
            
            # Total Aset
            total_aset = total_aset_lancar + total_aset_tetap
            st.write(f"TOTAL AKTIVA: Rp{total_aset:,.2f}")
            
            # ===== KEWAJIBAN =====
            # Total Utang (mengambil semua transaksi dengan jenis 'Utang')
            utang_kredit = conn.execute(
                    'SELECT COALESCE(SUM(nominal_kredit), 0) FROM transactions WHERE user_id = ? AND jenis_kredit = "Utang"',
                    (st.session_state.user_id,)
                ).fetchone()[0]

            utang_debit = conn.execute(
                    'SELECT COALESCE(SUM(nominal_debit), 0) FROM transactions WHERE user_id = ? AND jenis_debit = "Utang"',
                    (st.session_state.user_id,)
                ).fetchone()[0]

            saldo_utang = utang_kredit - utang_debit

            #===== UTANG ====
            st.subheader ("Utang")
            st.write(f"- Total Utang: Rp{saldo_utang:,.2f}")
            
            # ===== EKUITAS =====
            st.subheader("\nEkuitas")
            
            # Modal Awal
            modal_kredit = conn.execute(
                '''
                SELECT COALESCE(SUM(nominal_kredit), 0) 
                FROM transactions 
                WHERE user_id = ? AND jenis_kredit = 'Modal' 
                AND akun_kredit NOT LIKE '%prive%' 
                AND akun_kredit NOT LIKE '%tambahan modal%'
                ''',
                (st.session_state.user_id,)
            ).fetchone()[0]
            
            modal_debit = conn.execute(
                '''
                SELECT COALESCE(SUM(nominal_debit), 0) 
                FROM transactions 
                WHERE user_id = ? AND jenis_debit = 'Modal' 
                AND akun_debit NOT LIKE '%prive%' 
                AND akun_debit NOT LIKE '%tambahan modal%'
                ''',
                (st.session_state.user_id,)
            ).fetchone()[0]
            modal_awal = modal_kredit - modal_debit
            
            st.write(f"- Modal Awal: Rp{modal_awal:,.2f}")
            
            # Laba Ditahan (Laba/Rugi Berjalan)
            pendapatan_kredit = conn.execute(
                'SELECT COALESCE(SUM(nominal_kredit), 0) FROM transactions WHERE user_id = ? AND jenis_kredit = "Pendapatan"',
                (st.session_state.user_id,)
            ).fetchone()[0]
            
            pendapatan_debit = conn.execute(
                'SELECT COALESCE(SUM(nominal_debit), 0) FROM transactions WHERE user_id = ? AND jenis_debit = "Pendapatan"',
                (st.session_state.user_id,)
            ).fetchone()[0]
            total_pendapatan = pendapatan_kredit - pendapatan_debit
            
            beban_debit = conn.execute(
                'SELECT COALESCE(SUM(nominal_debit), 0) FROM transactions WHERE user_id = ? AND jenis_debit = "Beban"',
                (st.session_state.user_id,)
            ).fetchone()[0]
            
            beban_kredit = conn.execute(
                'SELECT COALESCE(SUM(nominal_kredit), 0) FROM transactions WHERE user_id = ? AND jenis_kredit = "Beban"',
                (st.session_state.user_id,)
            ).fetchone()[0]
            total_beban = beban_debit - beban_kredit
            
            laba_rugi = total_pendapatan - total_beban
            
            st.write(f"- Laba/Rugi Berjalan: Rp{laba_rugi:,.2f}" if laba_rugi >= 0 
                    else f"- Laba/Rugi Berjalan: (Rp{abs(laba_rugi):,.2f})")
            
            # Prive
            prive = conn.execute(
                '''
                SELECT COALESCE(SUM(nominal_debit), 0) 
                FROM transactions 
                WHERE user_id = ? AND jenis_debit = "Modal" 
                AND (akun_debit LIKE "%prive%" OR akun_debit LIKE "%pengambilan pribadi%")
                ''',
                (st.session_state.user_id,)
            ).fetchone()[0]
            
            if prive != 0:
                st.write(f"- Prive: (Rp{prive:,.2f})")
            
            # Tambahan Modal
            tambahan_modal = conn.execute(
                '''
                SELECT COALESCE(SUM(nominal_kredit), 0) 
                FROM transactions 
                WHERE user_id = ? AND jenis_kredit = "Modal" 
                AND (akun_kredit LIKE "%tambahan modal%" OR akun_kredit LIKE "%investasi%")
                ''',
                (st.session_state.user_id,)
            ).fetchone()[0]
            
            if tambahan_modal != 0:
                st.write(f"- Tambahan Modal: Rp{tambahan_modal:,.2f}")
            
            # Total Ekuitas
            total_ekuitas = modal_awal + laba_rugi - (prive if prive else 0) + (tambahan_modal if tambahan_modal else 0)
            st.write(f"TOTAL EKUITAS: Rp{total_ekuitas:,.2f}")
            
             # ===== TOTAL KEWAJIBAN DAN EKUITAS =====
            st.write(f"TOTAL KEWAJIBAN DAN EKUITAS: Rp{saldo_utang + total_ekuitas:,.2f}")

            
            # Validasi keseimbangan neraca
            st.divider()
            if abs(total_aset - (saldo_utang + total_ekuitas)) < 0.01:
                st.success("✅ Neraca seimbang (Total Aset = Total Kewajiban + Ekuitas)")
            else:
                st.error(f"❌ Neraca tidak seimbang! Selisih: Rp{abs(total_aset - (saldo_utang + total_ekuitas)):,.2f}")

        # === INFORMASI ===
        elif selected_menu == "Informasi":
            st.header("ℹ Informasi Aplikasi")
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
            st.subheader("📅 Data Survey Petani Terong")
            st.write("Narasumber: Bapak Tito Tarwoco")
            st.write("Lokasi: Desa Sarwogadung, Mirit, Kebumen")
            st.write("Jenis Terong: M72 (panen 2x/minggu)")
            st.write("Harga: Rp4.500/kg")
            st.write("Pupuk yang Digunakan:")
            st.write("- Pupuk ZA")
            st.write("- Mutiara 1616")
            st.write("- Mutiara Grower")
            st.write("- Mertiur")
            st.write("- Demolist")
                        
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
                        st.image(member["foto"], width=150,)
                    except FileNotFoundError:
                        st.error(f"File '{member['foto']}' tidak ditemukan")
                    st.write(f"{member['nama']}")
            
            st.divider()
            
            # 4. Panduan Singkat
            st.subheader("📚 Cara Penggunaan")
            st.write("""
            1. Input Transaksi:  
            - Isi tanggal, akun debit/kredit, dan nominal
            - Pastikan debit = kredit
            2. Buku Besar:
            - Otomatis terupdate setelah input transaksi
            3. Neraca Saldo:  
            - Cek keseimbangan debit-kredit
            """)
            
            # Footer
            st.caption("© 2025 Purple Book - Versi 1.0")

if __name__ == "__main__":
    init_db()
    main()
