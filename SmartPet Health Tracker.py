"""
SmartPet Health Tracker
Connor Warming

Features:
- User authentication with hashed passwords
- SQLite database
- Add / edit / delete pets
- Add / edit / delete health records
- Dashboard with summary stats
- Upcoming reminders
- CSV export
- Optional charts with matplotlib

Run:
    pip install matplotlib
    python SmartPet_Improved.py
"""

import csv
import hashlib
import sqlite3
import tkinter as tk
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None


DB_PATH = Path(__file__).with_name("smartpet_improved.db")


# =========================
# Database Helpers
# =========================

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def init_db():
    with get_conn() as conn:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS pets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                species TEXT,
                breed TEXT,
                birthdate TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS health_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pet_id INTEGER NOT NULL,
                record_type TEXT NOT NULL,
                description TEXT,
                record_date TEXT,
                vet TEXT,
                notes TEXT,
                FOREIGN KEY (pet_id) REFERENCES pets(id) ON DELETE CASCADE
            )
        """)

        conn.commit()


# =========================
# Auth Functions
# =========================

def create_user(username: str, password: str) -> bool:
    username = username.strip()
    if not username or not password:
        return False

    with get_conn() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, hash_password(password))
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def authenticate_user(username: str, password: str):
    username = username.strip()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,)
        )
        user = cur.fetchone()
        if user and user["password_hash"] == hash_password(password):
            return {"id": user["id"], "username": user["username"]}
    return None


# =========================
# Pet Functions
# =========================

def add_pet(user_id: int, name: str, species: str = "", breed: str = "", birthdate: str = ""):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO pets (user_id, name, species, breed, birthdate)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, name.strip(), species.strip(), breed.strip(), birthdate.strip()))
        conn.commit()
        return cur.lastrowid


def update_pet(pet_id: int, name: str, species: str = "", breed: str = "", birthdate: str = ""):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE pets
            SET name = ?, species = ?, breed = ?, birthdate = ?
            WHERE id = ?
        """, (name.strip(), species.strip(), breed.strip(), birthdate.strip(), pet_id))
        conn.commit()


def delete_pet(pet_id: int):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM pets WHERE id = ?", (pet_id,))
        conn.commit()


def list_pets(user_id: int):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, species, breed, birthdate
            FROM pets
            WHERE user_id = ?
            ORDER BY name ASC
        """, (user_id,))
        return [dict(row) for row in cur.fetchall()]


# =========================
# Health Record Functions
# =========================

def add_health_record(pet_id: int, record_type: str, description: str = "", record_date: str = "",
                      vet: str = "", notes: str = ""):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO health_records (pet_id, record_type, description, record_date, vet, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            pet_id,
            record_type.strip(),
            description.strip(),
            record_date.strip(),
            vet.strip(),
            notes.strip()
        ))
        conn.commit()
        return cur.lastrowid


def update_health_record(record_id: int, record_type: str, description: str = "", record_date: str = "",
                         vet: str = "", notes: str = ""):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE health_records
            SET record_type = ?, description = ?, record_date = ?, vet = ?, notes = ?
            WHERE id = ?
        """, (
            record_type.strip(),
            description.strip(),
            record_date.strip(),
            vet.strip(),
            notes.strip(),
            record_id
        ))
        conn.commit()


def delete_health_record(record_id: int):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM health_records WHERE id = ?", (record_id,))
        conn.commit()


def list_health_records_for_user(user_id: int):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT hr.id, hr.pet_id, p.name AS pet_name,
                   hr.record_type, hr.description, hr.record_date, hr.vet, hr.notes
            FROM health_records hr
            JOIN pets p ON p.id = hr.pet_id
            WHERE p.user_id = ?
            ORDER BY hr.record_date DESC, p.name ASC
        """, (user_id,))
        return [dict(row) for row in cur.fetchall()]


def list_health_records_for_pet(pet_id: int):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, pet_id, record_type, description, record_date, vet, notes
            FROM health_records
            WHERE pet_id = ?
            ORDER BY record_date DESC
        """, (pet_id,))
        return [dict(row) for row in cur.fetchall()]


def get_upcoming_records(user_id: int, days: int = 30):
    today = date.today()
    end_date = today + timedelta(days=days)

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT hr.id, p.name AS pet_name, hr.record_type, hr.description, hr.record_date, hr.vet
            FROM health_records hr
            JOIN pets p ON p.id = hr.pet_id
            WHERE p.user_id = ?
              AND hr.record_date IS NOT NULL
              AND hr.record_date >= ?
              AND hr.record_date <= ?
            ORDER BY hr.record_date ASC
        """, (user_id, today.isoformat(), end_date.isoformat()))
        return [dict(row) for row in cur.fetchall()]


def get_dashboard_stats(user_id: int):
    with get_conn() as conn:
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) AS total FROM pets WHERE user_id = ?", (user_id,))
        total_pets = cur.fetchone()["total"]

        cur.execute("""
            SELECT COUNT(*) AS total
            FROM health_records hr
            JOIN pets p ON p.id = hr.pet_id
            WHERE p.user_id = ?
        """, (user_id,))
        total_records = cur.fetchone()["total"]

        cur.execute("""
            SELECT hr.record_type, COUNT(*) AS count
            FROM health_records hr
            JOIN pets p ON p.id = hr.pet_id
            WHERE p.user_id = ?
            GROUP BY hr.record_type
            ORDER BY count DESC
            LIMIT 1
        """, (user_id,))
        row = cur.fetchone()
        most_common = row["record_type"] if row else "N/A"

    return {
        "total_pets": total_pets,
        "total_records": total_records,
        "most_common_record_type": most_common
    }


# =========================
# Utility
# =========================

def valid_date_string(text: str) -> bool:
    if not text.strip():
        return True
    try:
        datetime.strptime(text.strip(), "%Y-%m-%d")
        return True
    except ValueError:
        return False


# =========================
# Login Window
# =========================

class LoginWindow(tk.Frame):
    def __init__(self, master, on_login_success):
        super().__init__(master, bg="#f4f7fb")
        self.on_login_success = on_login_success
        self.pack(fill="both", expand=True)

        card = tk.Frame(self, bg="white", bd=1, relief="solid", padx=20, pady=20)
        card.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            card,
            text="SmartPet Health Tracker",
            font=("Segoe UI", 18, "bold"),
            bg="white"
        ).grid(row=0, column=0, columnspan=2, pady=(0, 16))

        tk.Label(card, text="Username", bg="white").grid(row=1, column=0, sticky="w", pady=6)
        self.username_var = tk.StringVar()
        tk.Entry(card, textvariable=self.username_var, width=28).grid(row=1, column=1, pady=6)

        tk.Label(card, text="Password", bg="white").grid(row=2, column=0, sticky="w", pady=6)
        self.password_var = tk.StringVar()
        tk.Entry(card, textvariable=self.password_var, show="*", width=28).grid(row=2, column=1, pady=6)

        tk.Button(card, text="Login", width=14, command=self.login).grid(row=3, column=0, pady=14)
        tk.Button(card, text="Create Account", width=14, command=self.register).grid(row=3, column=1, pady=14)

    def login(self):
        user = authenticate_user(self.username_var.get(), self.password_var.get())
        if user:
            self.on_login_success(user)
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.")

    def register(self):
        ok = create_user(self.username_var.get(), self.password_var.get())
        if ok:
            messagebox.showinfo("Account Created", "Account created successfully. You can now log in.")
        else:
            messagebox.showerror("Registration Failed", "Username may already exist, or fields are empty.")


# =========================
# Dashboard View
# =========================

class DashboardView(tk.Frame):
    def __init__(self, master, user):
        super().__init__(master, bg="#eef3f9")
        self.user = user
        self.build_ui()
        self.refresh()

    def build_ui(self):
        tk.Label(
            self,
            text=f"Welcome, {self.user['username']}",
            font=("Segoe UI", 18, "bold"),
            bg="#eef3f9"
        ).pack(pady=(16, 8))

        stats_frame = tk.Frame(self, bg="#eef3f9")
        stats_frame.pack(fill="x", padx=20, pady=10)

        self.total_pets_lbl = self._make_stat_card(stats_frame, "Total Pets", 0)
        self.total_records_lbl = self._make_stat_card(stats_frame, "Health Records", 1)
        self.common_type_lbl = self._make_stat_card(stats_frame, "Most Common Record", 2)

        reminders_box = tk.LabelFrame(self, text="Upcoming (next 30 days)", bg="white")
        reminders_box.pack(fill="both", expand=True, padx=20, pady=10)

        self.reminders_list = tk.Listbox(reminders_box, height=12)
        self.reminders_list.pack(fill="both", expand=True, padx=10, pady=10)

        button_row = tk.Frame(self, bg="#eef3f9")
        button_row.pack(pady=(0, 15))

        tk.Button(button_row, text="Refresh", width=16, command=self.refresh).pack(side="left", padx=5)
        tk.Button(button_row, text="Show Chart", width=16, command=self.show_chart).pack(side="left", padx=5)

    def _make_stat_card(self, parent, title, col):
        frame = tk.Frame(parent, bg="white", bd=1, relief="solid", padx=16, pady=16)
        frame.grid(row=0, column=col, padx=10, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)

        tk.Label(frame, text=title, font=("Segoe UI", 11, "bold"), bg="white").pack()
        value_lbl = tk.Label(frame, text="0", font=("Segoe UI", 16), bg="white")
        value_lbl.pack(pady=(8, 0))
        return value_lbl

    def refresh(self):
        stats = get_dashboard_stats(self.user["id"])
        self.total_pets_lbl.config(text=str(stats["total_pets"]))
        self.total_records_lbl.config(text=str(stats["total_records"]))
        self.common_type_lbl.config(text=stats["most_common_record_type"])

        self.reminders_list.delete(0, tk.END)
        upcoming = get_upcoming_records(self.user["id"], 30)
        if not upcoming:
            self.reminders_list.insert(tk.END, "No upcoming records.")
            return

        for row in upcoming:
            self.reminders_list.insert(
                tk.END,
                f"{row['record_date']} - {row['pet_name']} - {row['record_type']} - {row['description']}"
            )

    def show_chart(self):
        if plt is None:
            messagebox.showinfo("Unavailable", "matplotlib is not installed.\nRun: pip install matplotlib")
            return

        records = list_health_records_for_user(self.user["id"])
        if not records:
            messagebox.showinfo("No Data", "No records available for charting.")
            return

        counts = {}
        for record in records:
            record_type = record["record_type"] or "Unknown"
            counts[record_type] = counts.get(record_type, 0) + 1

        plt.figure(figsize=(7, 4))
        plt.bar(list(counts.keys()), list(counts.values()))
        plt.title("Health Records by Type")
        plt.xlabel("Record Type")
        plt.ylabel("Count")
        plt.tight_layout()
        plt.show()


# =========================
# Pets View
# =========================

class PetsView(tk.Frame):
    def __init__(self, master, user):
        super().__init__(master, bg="#eef3f9")
        self.user = user
        self.selected_pet_id = None
        self.build_ui()
        self.refresh()

    def build_ui(self):
        tk.Label(self, text="Pets", font=("Segoe UI", 16, "bold"), bg="#eef3f9").pack(pady=10)

        form = tk.LabelFrame(self, text="Pet Details", bg="white")
        form.pack(fill="x", padx=20, pady=10)

        self.name_var = tk.StringVar()
        self.species_var = tk.StringVar()
        self.breed_var = tk.StringVar()
        self.birthdate_var = tk.StringVar()

        fields = [
            ("Name*", self.name_var),
            ("Species", self.species_var),
            ("Breed", self.breed_var),
            ("Birthdate (YYYY-MM-DD)", self.birthdate_var),
        ]

        for i, (label, var) in enumerate(fields):
            tk.Label(form, text=label, bg="white").grid(row=i, column=0, sticky="w", padx=8, pady=6)
            tk.Entry(form, textvariable=var, width=40).grid(row=i, column=1, sticky="ew", padx=8, pady=6)

        form.grid_columnconfigure(1, weight=1)

        btns = tk.Frame(form, bg="white")
        btns.grid(row=4, column=1, sticky="e", padx=8, pady=10)

        tk.Button(btns, text="Add Pet", width=12, command=self.add_pet).pack(side="left", padx=4)
        tk.Button(btns, text="Update Pet", width=12, command=self.update_pet).pack(side="left", padx=4)
        tk.Button(btns, text="Delete Pet", width=12, command=self.delete_pet).pack(side="left", padx=4)
        tk.Button(btns, text="Clear", width=12, command=self.clear_form).pack(side="left", padx=4)
        tk.Button(btns, text="Export CSV", width=12, command=self.export_csv).pack(side="left", padx=4)

        table_frame = tk.Frame(self, bg="#eef3f9")
        table_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.tree = ttk.Treeview(
            table_frame,
            columns=("id", "name", "species", "breed", "birthdate"),
            show="headings"
        )
        for col, title, width in [
            ("id", "ID", 50),
            ("name", "Name", 160),
            ("species", "Species", 140),
            ("breed", "Breed", 140),
            ("birthdate", "Birthdate", 120),
        ]:
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="center")

        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for pet in list_pets(self.user["id"]):
            self.tree.insert(
                "",
                "end",
                values=(pet["id"], pet["name"], pet["species"], pet["breed"], pet["birthdate"])
            )

    def clear_form(self):
        self.selected_pet_id = None
        self.name_var.set("")
        self.species_var.set("")
        self.breed_var.set("")
        self.birthdate_var.set("")

    def on_select(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        row = self.tree.item(selected[0])["values"]
        self.selected_pet_id = row[0]
        self.name_var.set(row[1])
        self.species_var.set(row[2])
        self.breed_var.set(row[3])
        self.birthdate_var.set(row[4])

    def add_pet(self):
        if not self.name_var.get().strip():
            messagebox.showerror("Validation Error", "Pet name is required.")
            return
        if not valid_date_string(self.birthdate_var.get()):
            messagebox.showerror("Validation Error", "Birthdate must be YYYY-MM-DD.")
            return

        add_pet(
            self.user["id"],
            self.name_var.get(),
            self.species_var.get(),
            self.breed_var.get(),
            self.birthdate_var.get()
        )
        self.clear_form()
        self.refresh()

    def update_pet(self):
        if not self.selected_pet_id:
            messagebox.showinfo("Select Pet", "Select a pet to update.")
            return
        if not self.name_var.get().strip():
            messagebox.showerror("Validation Error", "Pet name is required.")
            return
        if not valid_date_string(self.birthdate_var.get()):
            messagebox.showerror("Validation Error", "Birthdate must be YYYY-MM-DD.")
            return

        update_pet(
            self.selected_pet_id,
            self.name_var.get(),
            self.species_var.get(),
            self.breed_var.get(),
            self.birthdate_var.get()
        )
        self.clear_form()
        self.refresh()

    def delete_pet(self):
        if not self.selected_pet_id:
            messagebox.showinfo("Select Pet", "Select a pet to delete.")
            return
        if messagebox.askyesno("Confirm Delete", "Delete selected pet and all related records?"):
            delete_pet(self.selected_pet_id)
            self.clear_form()
            self.refresh()

    def export_csv(self):
        path = filedialog.asksaveasfilename(
            title="Save Pets CSV",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")]
        )
        if not path:
            return

        rows = list_pets(self.user["id"])
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "name", "species", "breed", "birthdate"])
            writer.writeheader()
            writer.writerows(rows)

        messagebox.showinfo("Export Complete", f"Pets exported to:\n{path}")


# =========================
# Records View
# =========================

class RecordsView(tk.Frame):
    def __init__(self, master, user):
        super().__init__(master, bg="#eef3f9")
        self.user = user
        self.selected_record_id = None
        self.pet_id_by_label = {}
        self.build_ui()
        self.load_pet_options()
        self.refresh()

    def build_ui(self):
        tk.Label(self, text="Health Records", font=("Segoe UI", 16, "bold"), bg="#eef3f9").pack(pady=10)

        form = tk.LabelFrame(self, text="Record Details", bg="white")
        form.pack(fill="x", padx=20, pady=10)

        self.pet_var = tk.StringVar()
        self.type_var = tk.StringVar()
        self.date_var = tk.StringVar()
        self.desc_var = tk.StringVar()
        self.vet_var = tk.StringVar()

        tk.Label(form, text="Pet*", bg="white").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        self.pet_combo = ttk.Combobox(form, textvariable=self.pet_var, state="readonly", width=37)
        self.pet_combo.grid(row=0, column=1, sticky="ew", padx=8, pady=6)

        tk.Label(form, text="Type*", bg="white").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.type_combo = ttk.Combobox(
            form,
            textvariable=self.type_var,
            state="readonly",
            values=["Vaccination", "Medication", "Vet Visit", "Checkup", "Other"],
            width=37
        )
        self.type_combo.grid(row=1, column=1, sticky="ew", padx=8, pady=6)

        tk.Label(form, text="Date (YYYY-MM-DD)", bg="white").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        tk.Entry(form, textvariable=self.date_var, width=40).grid(row=2, column=1, sticky="ew", padx=8, pady=6)

        tk.Label(form, text="Description", bg="white").grid(row=3, column=0, sticky="w", padx=8, pady=6)
        tk.Entry(form, textvariable=self.desc_var, width=40).grid(row=3, column=1, sticky="ew", padx=8, pady=6)

        tk.Label(form, text="Vet / Clinic", bg="white").grid(row=4, column=0, sticky="w", padx=8, pady=6)
        tk.Entry(form, textvariable=self.vet_var, width=40).grid(row=4, column=1, sticky="ew", padx=8, pady=6)

        tk.Label(form, text="Notes", bg="white").grid(row=5, column=0, sticky="nw", padx=8, pady=6)
        self.notes_text = tk.Text(form, width=40, height=4)
        self.notes_text.grid(row=5, column=1, sticky="ew", padx=8, pady=6)

        form.grid_columnconfigure(1, weight=1)

        btns = tk.Frame(form, bg="white")
        btns.grid(row=6, column=1, sticky="e", padx=8, pady=10)

        tk.Button(btns, text="Add Record", width=12, command=self.add_record).pack(side="left", padx=4)
        tk.Button(btns, text="Update Record", width=12, command=self.update_record).pack(side="left", padx=4)
        tk.Button(btns, text="Delete Record", width=12, command=self.delete_record).pack(side="left", padx=4)
        tk.Button(btns, text="Clear", width=12, command=self.clear_form).pack(side="left", padx=4)
        tk.Button(btns, text="Export CSV", width=12, command=self.export_csv).pack(side="left", padx=4)

        table_frame = tk.Frame(self, bg="#eef3f9")
        table_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.tree = ttk.Treeview(
            table_frame,
            columns=("id", "pet_name", "record_type", "record_date", "description", "vet"),
            show="headings"
        )
        for col, title, width in [
            ("id", "ID", 50),
            ("pet_name", "Pet", 140),
            ("record_type", "Type", 120),
            ("record_date", "Date", 120),
            ("description", "Description", 220),
            ("vet", "Vet / Clinic", 160),
        ]:
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="center")

        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

    def load_pet_options(self):
        self.pet_id_by_label.clear()
        pets = list_pets(self.user["id"])
        labels = []

        for pet in pets:
            label = f"{pet['name']} (ID {pet['id']})"
            labels.append(label)
            self.pet_id_by_label[label] = pet["id"]

        self.pet_combo["values"] = labels
        if labels and not self.pet_var.get():
            self.pet_var.set(labels[0])

    def refresh(self):
        self.load_pet_options()
        for item in self.tree.get_children():
            self.tree.delete(item)

        for record in list_health_records_for_user(self.user["id"]):
            self.tree.insert(
                "",
                "end",
                values=(
                    record["id"],
                    record["pet_name"],
                    record["record_type"],
                    record["record_date"],
                    record["description"],
                    record["vet"]
                )
            )

    def clear_form(self):
        self.selected_record_id = None
        self.type_var.set("")
        self.date_var.set("")
        self.desc_var.set("")
        self.vet_var.set("")
        self.notes_text.delete("1.0", tk.END)
        self.load_pet_options()

    def on_select(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return

        row = self.tree.item(selected[0])["values"]
        self.selected_record_id = row[0]

        all_records = list_health_records_for_user(self.user["id"])
        match = next((r for r in all_records if r["id"] == self.selected_record_id), None)
        if not match:
            return

        pet_label = None
        for label, pet_id in self.pet_id_by_label.items():
            if pet_id == match["pet_id"]:
                pet_label = label
                break

        if pet_label:
            self.pet_var.set(pet_label)

        self.type_var.set(match["record_type"])
        self.date_var.set(match["record_date"] or "")
        self.desc_var.set(match["description"] or "")
        self.vet_var.set(match["vet"] or "")
        self.notes_text.delete("1.0", tk.END)
        self.notes_text.insert("1.0", match["notes"] or "")

    def add_record(self):
        pet_label = self.pet_var.get().strip()
        if pet_label not in self.pet_id_by_label:
            messagebox.showerror("Validation Error", "Select a valid pet.")
            return
        if not self.type_var.get().strip():
            messagebox.showerror("Validation Error", "Record type is required.")
            return
        if not valid_date_string(self.date_var.get()):
            messagebox.showerror("Validation Error", "Date must be YYYY-MM-DD.")
            return

        add_health_record(
            pet_id=self.pet_id_by_label[pet_label],
            record_type=self.type_var.get(),
            description=self.desc_var.get(),
            record_date=self.date_var.get(),
            vet=self.vet_var.get(),
            notes=self.notes_text.get("1.0", tk.END).strip()
        )
        self.clear_form()
        self.refresh()

    def update_record(self):
        if not self.selected_record_id:
            messagebox.showinfo("Select Record", "Select a record to update.")
            return

        pet_label = self.pet_var.get().strip()
        if pet_label not in self.pet_id_by_label:
            messagebox.showerror("Validation Error", "Select a valid pet.")
            return
        if not self.type_var.get().strip():
            messagebox.showerror("Validation Error", "Record type is required.")
            return
        if not valid_date_string(self.date_var.get()):
            messagebox.showerror("Validation Error", "Date must be YYYY-MM-DD.")
            return

        current_records = list_health_records_for_user(self.user["id"])
        target = next((r for r in current_records if r["id"] == self.selected_record_id), None)
        if not target:
            messagebox.showerror("Error", "Record not found.")
            return

        selected_pet_id = self.pet_id_by_label[pet_label]

        if selected_pet_id != target["pet_id"]:
            delete_health_record(self.selected_record_id)
            add_health_record(
                pet_id=selected_pet_id,
                record_type=self.type_var.get(),
                description=self.desc_var.get(),
                record_date=self.date_var.get(),
                vet=self.vet_var.get(),
                notes=self.notes_text.get("1.0", tk.END).strip()
            )
        else:
            update_health_record(
                self.selected_record_id,
                record_type=self.type_var.get(),
                description=self.desc_var.get(),
                record_date=self.date_var.get(),
                vet=self.vet_var.get(),
                notes=self.notes_text.get("1.0", tk.END).strip()
            )

        self.clear_form()
        self.refresh()

    def delete_record(self):
        if not self.selected_record_id:
            messagebox.showinfo("Select Record", "Select a record to delete.")
            return
        if messagebox.askyesno("Confirm Delete", "Delete selected record?"):
            delete_health_record(self.selected_record_id)
            self.clear_form()
            self.refresh()

    def export_csv(self):
        path = filedialog.asksaveasfilename(
            title="Save Records CSV",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")]
        )
        if not path:
            return

        rows = list_health_records_for_user(self.user["id"])
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["id", "pet_id", "pet_name", "record_type", "description", "record_date", "vet", "notes"]
            )
            writer.writeheader()
            writer.writerows(rows)

        messagebox.showinfo("Export Complete", f"Records exported to:\n{path}")


# =========================
# Main App
# =========================

class SmartPetApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SmartPet Health Tracker")
        self.geometry("1050x700")
        self.configure(bg="#eef3f9")

        self.user = None
        self.main_container = tk.Frame(self, bg="#eef3f9")
        self.main_container.pack(fill="both", expand=True)

        self.show_login()

    def clear_container(self):
        for child in self.main_container.winfo_children():
            child.destroy()

    def show_login(self):
        self.clear_container()
        LoginWindow(self.main_container, self.on_login_success)

    def on_login_success(self, user):
        self.user = user
        self.show_main_app()

    def show_main_app(self):
        self.clear_container()

        topbar = tk.Frame(self.main_container, bg="#1f4f82", height=50)
        topbar.pack(fill="x")

        tk.Label(
            topbar,
            text=f"SmartPet Health Tracker | Logged in as {self.user['username']}",
            fg="white",
            bg="#1f4f82",
            font=("Segoe UI", 12, "bold")
        ).pack(side="left", padx=16, pady=10)

        tk.Button(topbar, text="Logout", command=self.logout).pack(side="right", padx=12, pady=10)

        nav = tk.Frame(self.main_container, bg="#dbe6f3", height=40)
        nav.pack(fill="x")

        content = tk.Frame(self.main_container, bg="#eef3f9")
        content.pack(fill="both", expand=True)

        def load_view(name):
            for child in content.winfo_children():
                child.destroy()

            if name == "dashboard":
                view = DashboardView(content, self.user)
            elif name == "pets":
                view = PetsView(content, self.user)
            else:
                view = RecordsView(content, self.user)

            view.pack(fill="both", expand=True)

        tk.Button(nav, text="Dashboard", width=16, command=lambda: load_view("dashboard")).pack(side="left", padx=8, pady=6)
        tk.Button(nav, text="Pets", width=16, command=lambda: load_view("pets")).pack(side="left", padx=8, pady=6)
        tk.Button(nav, text="Health Records", width=16, command=lambda: load_view("records")).pack(side="left", padx=8, pady=6)

        load_view("dashboard")

    def logout(self):
        self.user = None
        self.show_login()


if __name__ == "__main__":
    init_db()
    SmartPetApp().mainloop()