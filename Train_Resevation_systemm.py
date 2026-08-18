

import sqlite3
import os
import random
import string
import datetime
from collections import deque
import heapq
import sys
from typing import Optional, List

DB_FILE = "train_reservation.db"

# DSA Simple Linked List 

class LinkedListNode:
    def __init__(self, data):
        self.data = data
        self.next = None

class LinkedList:
    """
    Simple singly linked list to store passenger names for demonstration.
    (DSA concept: usage of linked list to maintain variable-size list)
    """
    def __init__(self):
        self.head = None

    def append(self, data):
        if not self.head:
            self.head = LinkedListNode(data)
        else:
            cur = self.head
            while cur.next:
                cur = cur.next
            cur.next = LinkedListNode(data)

    def remove(self, data):
        prev = None
        cur = self.head
        while cur:
            if cur.data == data:
                if prev:
                    prev.next = cur.next
                else:
                    self.head = cur.next
                return True
            prev = cur
            cur = cur.next
        return False

    def to_list(self):
        res = []
        cur = self.head
        while cur:
            res.append(cur.data)
            cur = cur.next
        return res

# Utils

def ensure_db():
    first_time = not os.path.exists(DB_FILE)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Create tables
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        name TEXT,
        phone TEXT
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS trains (
        train_no INTEGER PRIMARY KEY,
        name TEXT,
        source TEXT,
        destination TEXT,
        total_seats INTEGER,
        available_seats INTEGER,
        fare REAL
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS bookings (
        pnr TEXT PRIMARY KEY,
        user_id INTEGER,
        train_no INTEGER,
        passenger_name TEXT,
        age INTEGER,
        gender TEXT,
        status TEXT,  -- 'CONFIRMED' or 'WAITING' or 'CANCELLED'
        booking_time TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(train_no) REFERENCES trains(train_no)
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS waiting_list (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        train_no INTEGER,
        pnr TEXT,
        time_added TEXT,
        FOREIGN KEY(pnr) REFERENCES bookings(pnr),
        FOREIGN KEY(train_no) REFERENCES trains(train_no)
    )
    ''')
    conn.commit()
    if first_time:
        # insert sample trains
        sample_trains = [
            (12001, 'Express A', 'Delhi', 'Mumbai', 100, 100, 750.0),
            (12002, 'Express B', 'Kolkata', 'Delhi', 80, 80, 900.0),
            (12003, 'Express C', 'Chennai', 'Bangalore', 60, 60, 450.0),
            (12004, 'Express D', 'Mumbai', 'Jaipur', 50, 50, 500.0),
        ]
        c.executemany('INSERT OR IGNORE INTO trains VALUES (?,?,?,?,?,?,?)', sample_trains)
        conn.commit()
    conn.close()

def generate_pnr():
    # PNR: 10-character unique alphanumeric based on timestamp + random
    ts = datetime.datetime.now().strftime("%y%m%d%H%M%S")
    rand = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
    return f"{ts}{rand}"

def get_connection():
    return sqlite3.connect(DB_FILE)

# -------------------------
# DSA: Binary search over trains by train_no
# -------------------------
def fetch_all_trains_sorted():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT train_no, name, source, destination, total_seats, available_seats, fare FROM trains ORDER BY train_no')
    rows = c.fetchall()
    conn.close()
    trains = [dict(train_no=r[0], name=r[1], source=r[2], destination=r[3], total_seats=r[4], available_seats=r[5], fare=r[6]) for r in rows]
    return trains

def binary_search_trains(trains_list, target_no) -> Optional[dict]:
    """
    DSA: binary search on a sorted list of trains by train_no.
    Returns train dict if found else None.
    """
    lo, hi = 0, len(trains_list) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if trains_list[mid]['train_no'] == target_no:
            return trains_list[mid]
        elif trains_list[mid]['train_no'] < target_no:
            lo = mid + 1
        else:
            hi = mid - 1
    return None

# -------------------------
# Booking System Core
# -------------------------
class TrainReservationSystem:
    def __init__(self):
        ensure_db()
        self.waiting_queues = {}  # in-memory cache: train_no -> deque of PNRs (to show DSA queue)
        self.train_passenger_lists = {}  # train_no -> LinkedList of passenger names (DSA demo)
        self.load_waiting_queues_from_db()

    def load_waiting_queues_from_db(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute('SELECT train_no, pnr FROM waiting_list ORDER BY id')
        for train_no, pnr in c.fetchall():
            if train_no not in self.waiting_queues:
                self.waiting_queues[train_no] = deque()
            self.waiting_queues[train_no].append(pnr)
        conn.close()

    # User functions
    def register_user(self, username, password, name, phone):
        conn = get_connection()
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (username, password, name, phone) VALUES (?,?,?,?)', (username, password, name, phone))
            conn.commit()
            print("Registration successful.")
        except sqlite3.IntegrityError:
            print("Username already exists. Try another username.")
        finally:
            conn.close()

    def login_user(self, username, password):
        conn = get_connection()
        c = conn.cursor()
        c.execute('SELECT id, name FROM users WHERE username=? AND password=?', (username, password))
        row = c.fetchone()
        conn.close()
        if row:
            print(f"Welcome {row[1]}!")
            return row[0]  # user_id
        else:
            print("Invalid credentials.")
            return None

    # Admin functions
    def admin_login(self, username, password):
        # For demo, hard-coded admin
        if username == 'admin' and password == 'admin123':
            print("Admin login successful.")
            return True
        print("Admin auth failed.")
        return False

    def add_train(self, train_no, name, source, destination, total_seats, fare):
        conn = get_connection()
        c = conn.cursor()
        try:
            c.execute('INSERT INTO trains VALUES (?,?,?,?,?,?,?)', (train_no, name, source, destination, total_seats, total_seats, fare))
            conn.commit()
            print("Train added successfully.")
        except sqlite3.IntegrityError:
            print("Train number already exists.")
        finally:
            conn.close()

    def update_train(self, train_no, **kwargs):
        # kwargs: name, source, destination, total_seats, fare
        conn = get_connection()
        c = conn.cursor()
        # fetch existing
        c.execute('SELECT total_seats, available_seats FROM trains WHERE train_no=?', (train_no,))
        row = c.fetchone()
        if not row:
            print("Train not found.")
            conn.close()
            return
        total, avail = row
        fields = []
        values = []
        for k, v in kwargs.items():
            if k in ('name', 'source', 'destination', 'total_seats', 'fare'):
                fields.append(f"{k}=?")
                values.append(v)
        if 'total_seats' in kwargs:
            # adjust available seats proportionally (simple logic)
            new_total = kwargs['total_seats']
            used = total - avail
            new_avail = max(0, new_total - used)
            fields.append("available_seats=?")
            values.append(new_avail)
        if not fields:
            print("No valid fields to update.")
            conn.close()
            return
        values.append(train_no)
        sql = f"UPDATE trains SET {', '.join(fields)} WHERE train_no=?"
        c.execute(sql, tuple(values))
        conn.commit()
        conn.close()
        print("Train updated.")

    def remove_train(self, train_no):
        conn = get_connection()
        c = conn.cursor()
        c.execute('DELETE FROM trains WHERE train_no=?', (train_no,))
        conn.commit()
        conn.close()
        print("Train removed (if existed).")

    # Search trains (supports binary search by sorted train_no)
    def search_trains(self, train_no=None, source=None, destination=None):
        trains = fetch_all_trains_sorted()
        results = []
        if train_no:
            t = binary_search_trains(trains, train_no)
            if t:
                results.append(t)
        else:
            for t in trains:
                if source and destination:
                    if t['source'].lower() == source.lower() and t['destination'].lower() == destination.lower():
                        results.append(t)
                elif source:
                    if t['source'].lower() == source.lower():
                        results.append(t)
                elif destination:
                    if t['destination'].lower() == destination.lower():
                        results.append(t)
                else:
                    results.append(t)
        return results

    # Booking flow
    def book_ticket(self, user_id, train_no, passenger_name, age, gender):
        conn = get_connection()
        c = conn.cursor()
        c.execute('SELECT available_seats FROM trains WHERE train_no=?', (train_no,))
        row = c.fetchone()
        if not row:
            print("Train not found.")
            conn.close()
            return None
        avail = row[0]
        pnr = generate_pnr()
        booking_time = datetime.datetime.now().isoformat()
        if avail > 0:
            # Confirmed booking
            c.execute('INSERT INTO bookings VALUES (?,?,?,?,?,?,?,?)',
                    (pnr, user_id, train_no, passenger_name, age, gender, 'CONFIRMED', booking_time))
            # reduce seat
            c.execute('UPDATE trains SET available_seats=available_seats-1 WHERE train_no=?', (train_no,))
            # add passenger to linked list DSA demo
            self.add_passenger_to_train_list(train_no, passenger_name)
            conn.commit()
            conn.close()
            print(f"Booking CONFIRMED. PNR: {pnr}")
            return pnr
        else:
            # Waiting list
            c.execute('INSERT INTO bookings VALUES (?,?,?,?,?,?,?,?)',
                    (pnr, user_id, train_no, passenger_name, age, gender, 'WAITING', booking_time))
            c.execute('INSERT INTO waiting_list (train_no, pnr, time_added) VALUES (?,?,?)', (train_no, pnr, booking_time))
            conn.commit()
            conn.close()
            # update in-memory queue
            if train_no not in self.waiting_queues:
                self.waiting_queues[train_no] = deque()
            self.waiting_queues[train_no].append(pnr)
            print(f"No seats available. Added to WAITING list. PNR: {pnr}")
            return pnr

    def add_passenger_to_train_list(self, train_no, passenger_name):
        # DSA: maintain linked list of passenger names per train
        if train_no not in self.train_passenger_lists:
            # initialize from existing CONFIRMED bookings if needed (optimization skipped)
            self.train_passenger_lists[train_no] = LinkedList()
        self.train_passenger_lists[train_no].append(passenger_name)

    # Cancel flow
    def cancel_ticket(self, pnr):
        conn = get_connection()
        c = conn.cursor()
        c.execute('SELECT status, train_no, passenger_name FROM bookings WHERE pnr=?', (pnr,))
        row = c.fetchone()
        if not row:
            print("PNR not found.")
            conn.close()
            return
        status, train_no, passenger_name = row
        if status == 'CANCELLED':
            print("Already cancelled.")
            conn.close()
            return
        # mark cancelled
        c.execute('UPDATE bookings SET status=? WHERE pnr=?', ('CANCELLED', pnr))
        # If confirmed, free a seat and promote first waiting
        if status == 'CONFIRMED':
            c.execute('UPDATE trains SET available_seats=available_seats+1 WHERE train_no=?', (train_no,))
            # remove passenger from linked list if present
            if train_no in self.train_passenger_lists:
                self.train_passenger_lists[train_no].remove(passenger_name)
            # promote waiting
            c.execute('SELECT id, pnr FROM waiting_list WHERE train_no=? ORDER BY id LIMIT 1', (train_no,))
            w = c.fetchone()
            if w:
                waiting_id, wait_pnr = w
                # update booking status
                c.execute('UPDATE bookings SET status=? WHERE pnr=?', ('CONFIRMED', wait_pnr))
                # remove from waiting_list table
                c.execute('DELETE FROM waiting_list WHERE id=?', (waiting_id,))
                # reduce seats (we just freed one and allocate to waiting)
                c.execute('UPDATE trains SET available_seats=available_seats-1 WHERE train_no=?', (train_no,))
                # update in-memory queue
                if train_no in self.waiting_queues and self.waiting_queues[train_no]:
                    self.waiting_queues[train_no].popleft()
                # add passenger to linked list (fetch passenger name)
                c.execute('SELECT passenger_name FROM bookings WHERE pnr=?', (wait_pnr,))
                pn = c.fetchone()
                if pn:
                    self.add_passenger_to_train_list(train_no, pn[0])
                print(f"Cancelled. Waiting passenger {wait_pnr} has been CONFIRMED.")
        elif status == 'WAITING':
            # remove from waiting_list table and in-memory queue
            c.execute('DELETE FROM waiting_list WHERE pnr=?', (pnr,))
            if train_no in self.waiting_queues:
                try:
                    self.waiting_queues[train_no].remove(pnr)
                except ValueError:
                    pass
            print("Cancelled from waiting list.")
        conn.commit()
        conn.close()

    # Check PNR
    def check_pnr(self, pnr):
        conn = get_connection()
        c = conn.cursor()
        c.execute('SELECT pnr, user_id, train_no, passenger_name, age, gender, status, booking_time FROM bookings WHERE pnr=?', (pnr,))
        row = c.fetchone()
        conn.close()
        if not row:
            print("PNR not found.")
            return
        print("PNR Details:")
        print("PNR:", row[0])
        print("Train No:", row[2])
        print("Passenger:", row[3], f"(Age: {row[4]}, Gender: {row[5]})")
        print("Status:", row[6])
        print("Booking Time:", row[7])

    # Reports
    def daily_report(self, date_str=None):
        """
        Simple report counting bookings on a given date (YYYY-MM-DD).
        """
        if date_str is None:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM bookings WHERE date(booking_time)=?", (date_str,))
        total = c.fetchone()[0]
        c.execute("SELECT status, COUNT(*) FROM bookings WHERE date(booking_time)=? GROUP BY status", (date_str,))
        rows = c.fetchall()
        conn.close()
        print(f"Bookings on {date_str}: Total = {total}")
        for status, cnt in rows:
            print(f"  {status}: {cnt}")

    def top_busy_trains(self, k=3):
        """
        Use heap to find top-k trains by number of total bookings ever.
        DSA: heapq for top-k.
        """
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT train_no, COUNT(*) as cnt FROM bookings GROUP BY train_no")
        rows = c.fetchall()
        conn.close()
        # build a heap of (-cnt, train_no) to get max counts
        heap = [(-cnt, train_no) for train_no, cnt in rows]
        heapq.heapify(heap)
        result = []
        for _ in range(min(k, len(heap))):
            neg_cnt, train_no = heapq.heappop(heap)
            result.append((train_no, -neg_cnt))
        print(f"Top {k} busy trains (train_no, bookings):")
        for tno, cnt in result:
            print(f"  {tno}: {cnt}")

    # Utility helper to list trains
    def list_trains(self):
        trains = fetch_all_trains_sorted()
        print("Available Trains:")
        for t in trains:
            print(f"  {t['train_no']} - {t['name']}: {t['source']} -> {t['destination']}, Seats: {t['available_seats']}/{t['total_seats']}, Fare: {t['fare']}")

# -------------------------
# CLI
# -------------------------
def main_cli():
    system = TrainReservationSystem()
    print("=== Train Reservation System ===")
    current_user_id = None

    while True:
        print("\nMain Menu:")
        print("1. Register")
        print("2. Login")
        print("3. Admin Login")
        print("4. Exit")
        choice = input("Choice: ").strip()
        if choice == '1':
            username = input("Username: ").strip()
            password = input("Password: ").strip()
            name = input("Full Name: ").strip()
            phone = input("Phone: ").strip()
            system.register_user(username, password, name, phone)
        elif choice == '2':
            username = input("Username: ").strip()
            password = input("Password: ").strip()
            uid = system.login_user(username, password)
            if uid:
                current_user_id = uid
                user_menu(system, current_user_id)
        elif choice == '3':
            username = input("Admin Username: ").strip()
            password = input("Admin Password: ").strip()
            if system.admin_login(username, password):
                admin_menu(system)
        elif choice == '4':
            print("Goodbye!")
            break
        else:
            print("Invalid choice.")

def user_menu(system: TrainReservationSystem, user_id):
    while True:
        print("\nUser Menu:")
        print("1. Search Trains")
        print("2. List All Trains")
        print("3. Book Ticket")
        print("4. Cancel Ticket")
        print("5. Check PNR")
        print("6. Logout")
        choice = input("Choice: ").strip()
        if choice == '1':
            sub = input("Search by (1)Train No (2)Source-Destination (3)All: ").strip()
            if sub == '1':
                tno = int(input("Train No: ").strip())
                res = system.search_trains(train_no=tno)
            elif sub == '2':
                src = input("Source: ").strip()
                dest = input("Destination: ").strip()
                res = system.search_trains(source=src, destination=dest)
            else:
                res = system.search_trains()
            if not res:
                print("No trains found.")
            else:
                for t in res:
                    print(f"{t['train_no']} - {t['name']}: {t['source']} -> {t['destination']}, Seats: {t['available_seats']}/{t['total_seats']}, Fare: {t['fare']}")
        elif choice == '2':
            system.list_trains()
        elif choice == '3':
            tno = int(input("Enter Train No to book: ").strip())
            pname = input("Passenger Name: ").strip()
            age = int(input("Age: ").strip())
            gender = input("Gender: ").strip()
            pnr = system.book_ticket(user_id, tno, pname, age, gender)
            if pnr:
                print("Note your PNR:", pnr)
        elif choice == '4':
            pnr = input("Enter PNR to cancel: ").strip()
            system.cancel_ticket(pnr)
        elif choice == '5':
            pnr = input("Enter PNR to check: ").strip()
            system.check_pnr(pnr)
        elif choice == '6':
            print("Logging out.")
            break
        else:
            print("Invalid choice.")

def admin_menu(system: TrainReservationSystem):
    while True:
        print("\nAdmin Menu:")
        print("1. Add Train")
        print("2. Update Train")
        print("3. Remove Train")
        print("4. View All Trains")
        print("5. Daily Report")
        print("6. Top Busy Trains")
        print("7. Back to Main")
        choice = input("Choice: ").strip()
        if choice == '1':
            try:
                tno = int(input("Train No: ").strip())
                name = input("Name: ").strip()
                src = input("Source: ").strip()
                dest = input("Destination: ").strip()
                seats = int(input("Total Seats: ").strip())
                fare = float(input("Fare: ").strip())
                system.add_train(tno, name, src, dest, seats, fare)
            except ValueError:
                print("Invalid input.")
        elif choice == '2':
            try:
                tno = int(input("Train No to update: ").strip())
                print("Leave field blank to skip.")
                name = input("Name: ").strip()
                src = input("Source: ").strip()
                dest = input("Destination: ").strip()
                seats = input("Total Seats: ").strip()
                fare = input("Fare: ").strip()
                kwargs = {}
                if name: kwargs['name'] = name
                if src: kwargs['source'] = src
                if dest: kwargs['destination'] = dest
                if seats: kwargs['total_seats'] = int(seats)
                if fare: kwargs['fare'] = float(fare)
                system.update_train(tno, **kwargs)
            except ValueError:
                print("Invalid input.")
        elif choice == '3':
            tno = int(input("Train No to remove: ").strip())
            system.remove_train(tno)
        elif choice == '4':
            system.list_trains()
        elif choice == '5':
            date_str = input("Date (YYYY-MM-DD) or leave blank for today: ").strip()
            if date_str == '':
                date_str = None
            system.daily_report(date_str)
        elif choice == '6':
            k = input("Top K (default 3): ").strip()
            if k.isdigit():
                k = int(k)
            else:
                k = 3
            system.top_busy_trains(k)
        elif choice == '7':
            break
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    try:
        main_cli()
    except KeyboardInterrupt:
        print("\nExiting. Goodbye!")
        sys.exit(0)
