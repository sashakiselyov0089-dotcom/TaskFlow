# TaskFlow
приложение для составления расписания дня, работает на Ollama (бесплатная версия)
import customtkinter as ctk
import sqlite3
import os
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from plyer import notification
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import sys
import winsound
import requests
import json as json_lib
import random
import speech_recognition as sr
import pyttsx3
import threading
import sounddevice as sd
import numpy as np
import io
import wave

# ===== ЦВЕТОВАЯ СХЕМА =====
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

app = ctk.CTk()
app.geometry("1600x900")
app.title("TaskFlow Pro")

BG_PRIMARY = "#0a0a0f"
BG_SECONDARY = "#16161f"
BG_TERTIARY = "#1f1f2e"
ACCENT = "#8b5cf6"
ACCENT_HOVER = "#7c3aed"
TEXT_PRIMARY = "#e0e0e8"
TEXT_SECONDARY = "#9ca3af"
TEXT_MUTED = "#6b7280"
BORDER = "#2d2d3d"
SUCCESS = "#10b981"
WARNING = "#f59e0b"
DANGER = "#ef4444"

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_FILE = os.path.join(BASE_DIR, "taskflow.db")
SCHEDULE_FILE = os.path.join(BASE_DIR, "Расписание.xlsx")

OLLAMA_MODEL = "qwen2.5:7b"
OLLAMA_API_URL = "http://localhost:11434/api/generate"

timer_running = False
timer_remaining = 0
timer_job = None
current_theme = "dark"
auto_update_interval = 300000
dragged_item = None
dragged_index = None
current_filter = None
tasks_cache = None

task_input = None
search_input = None
priority_menu = None
category_menu = None
deadline_input = None
tasks_box = None
stats_label = None
progress = None
motivation_label = None
greeting_label = None
status_bar_label = None
content_frame = None
weather_label = None
focus_task_label = None
focus_time_label = None
focus_frame = None

MOTIVATION_QUOTES = [
    "💪 Каждый час кодинга — шаг к мечте",
    "🔥 Дисциплина — это свобода",
    "🚀 Маленькие шаги каждый день = большие результаты",
    "⚡ Ты сильнее, чем думаешь",
    "🎯 Фокус на цели, а не на препятствиях",
    "💎 Упорство побеждает талант",
    "🌟 Сегодня ты ближе к цели, чем вчера",
    "🔥 Боль дисциплины < боль сожаления",
    "🚀 Код не пишет сам себя — пиши!",
    "💪 Твоё будущее зависит от того, что ты делаешь сегодня",
]

# ===== АНИМАЦИИ =====
def fade_in_window(window, duration=300):
    window.attributes('-alpha', 0)
    window.update()
    def animate(alpha=0):
        if alpha < 1.0:
            window.attributes('-alpha', alpha)
            window.after(duration // 10, lambda: animate(alpha + 0.1))
    animate()

def hover_effect(widget, normal_color, hover_color):
    def on_enter(e):
        widget.configure(fg_color=hover_color)
    def on_leave(e):
        widget.configure(fg_color=normal_color)
    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)

def pulse_animation(widget, color1, color2, duration=1000):
    def animate(state=0):
        if state == 0:
            widget.configure(fg_color=color1)
            widget.after(duration, lambda: animate(1))
        else:
            widget.configure(fg_color=color2)
            widget.after(duration, lambda: animate(0))
    animate()
    
    # ===== ПЛАВНЫЕ АНИМАЦИИ =====
def animate_color(widget, start_color, end_color, duration=300, callback=None):
    """Плавное изменение цвета виджета"""
    steps = 20
    step_duration = duration // steps
    
    # Парсим цвета
    start_rgb = tuple(int(start_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    end_rgb = tuple(int(end_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    
    def step(current_step):
        if current_step >= steps:
            widget.configure(fg_color=end_color)
            if callback:
                callback()
            return
        
        # Интерполяция цвета
        ratio = current_step / steps
        r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * ratio)
        g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * ratio)
        b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * ratio)
        current_color = f"#{r:02x}{g:02x}{b:02x}"
        
        try:
            widget.configure(fg_color=current_color)
            widget.after(step_duration, lambda: step(current_step + 1))
        except:
            pass
    
    step(0)

def fade_in_card(card, duration=200):
    """Плавное появление карточки"""
    # Начинаем с прозрачного цвета
    card.configure(fg_color=BG_PRIMARY)
    
    # Анимируем к целевому цвету
    target_color = card.cget("fg_color") if hasattr(card, "_fg_color") else BG_SECONDARY
    animate_color(card, BG_PRIMARY, target_color, duration)

def smooth_screen_transition(old_content_func, new_content_func, duration=300):
    """Плавный переход между экранами"""
    # Fade out старого контента
    for widget in content_frame.winfo_children():
        animate_color(widget, widget.cget("fg_color") if hasattr(widget, "_fg_color") else BG_PRIMARY, BG_PRIMARY, duration, 
                     lambda w=widget: w.destroy())
    
    # Fade in нового контента после завершения fade out
    content_frame.after(duration + 50, new_content_func)

def animate_progress_bar(target_value, duration=500):
    """Плавная анимация прогресс-бара"""
    current_value = progress.get()
    steps = 30
    step_duration = duration // steps
    
    def step(current_step):
        if current_step >= steps:
            progress.set(target_value)
            return
        
        ratio = current_step / steps
        current = current_value + (target_value - current_value) * ratio
        progress.set(current)
        progress.after(step_duration, lambda: step(current_step + 1))
    
    step(0)

# ===== БАЗА ДАННЫХ =====
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY, name TEXT, goal TEXT, coding_hours REAL, sport_hours REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL, done INTEGER DEFAULT 0, priority TEXT, category TEXT, deadline TEXT, display_order INTEGER DEFAULT 0)''')
    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN display_order INTEGER DEFAULT 0")
    except:
        pass
    cursor.execute('''CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT UNIQUE, completed_count INTEGER, total_count INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS habits (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, emoji TEXT DEFAULT "🎯", current_streak INTEGER DEFAULT 0, longest_streak INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS habit_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, habit_id INTEGER, date TEXT NOT NULL, completed INTEGER DEFAULT 1)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS achievements (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT, unlocked INTEGER DEFAULT 0, date_unlocked TEXT)''')
    
    cursor.execute("SELECT COUNT(*) FROM habits")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO habits (name, emoji) VALUES ('Кодинг', '💻')")
        cursor.execute("INSERT INTO habits (name, emoji) VALUES ('Спорт', '💪')")
        cursor.execute("INSERT INTO habits (name, emoji) VALUES ('Чтение', '📚')")
        
    cursor.execute("SELECT COUNT(*) FROM achievements")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO achievements (name, description) VALUES ('Первые шаги', 'Выполни первую задачу')")
        cursor.execute("INSERT INTO achievements (name, description) VALUES ('Неделя силы', 'Держи стрик 7 дней')")
        cursor.execute("INSERT INTO achievements (name, description) VALUES ('Легенда', 'Выполни 50 задач')")
    
    conn.commit()
    conn.close()

def get_profile():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profile LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    if result:
        return {"id": result[0], "name": result[1], "goal": result[2], "coding_hours": result[3], "sport_hours": result[4]}
    return None

def save_profile(name, goal, coding_hours, sport_hours):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM profile")
    cursor.execute("INSERT INTO profile VALUES (NULL, ?, ?, ?, ?)", (name, goal, coding_hours, sport_hours))
    conn.commit()
    conn.close()

def get_all_tasks(force_refresh=False):
    global tasks_cache
    if tasks_cache is not None and not force_refresh:
        return tasks_cache
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, text, done, priority, category, deadline FROM tasks ORDER BY display_order, deadline")
    rows = cursor.fetchall()
    conn.close()
    tasks_cache = [{"id": r[0], "text": r[1], "done": bool(r[2]), "priority": r[3], "category": r[4], "deadline": r[5]} for r in rows]
    return tasks_cache

def invalidate_tasks_cache():
    """Сбрасывает кэш задач — вызывать после ЛЮБОГО изменения в БД задач"""
    global tasks_cache
    tasks_cache = None

def add_task_to_db(text, priority, category, deadline):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tasks")
    count = cursor.fetchone()[0]
    cursor.execute("INSERT INTO tasks (text, done, priority, category, deadline, display_order) VALUES (?, 0, ?, ?, ?, ?)", (text, priority, category, deadline, count))
    conn.commit()
    conn.close()
    invalidate_tasks_cache()

def update_task_in_db(task_id, text, priority, category, deadline):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET text=?, priority=?, category=?, deadline=? WHERE id=?", (text, priority, category, deadline, task_id))
    conn.commit()
    conn.close()
    invalidate_tasks_cache()

def update_task_order(task_ids):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    for idx, tid in enumerate(task_ids):
        cursor.execute("UPDATE tasks SET display_order=? WHERE id=?", (idx, tid))
    conn.commit()
    conn.close()
    invalidate_tasks_cache()

def toggle_task_done_in_db(task_id, done):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET done=? WHERE id=?", (int(done), task_id))
    conn.commit()
    conn.close()
    invalidate_tasks_cache()

def delete_task_from_db(task_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    invalidate_tasks_cache()

def delete_old_tasks_from_db():
    today = datetime.datetime.now().date()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, deadline FROM tasks")
    changed = False
    for row in cursor.fetchall():
        tid, dl = row
        if dl:
            try:
                d = datetime.datetime.strptime(dl.split(" ")[0], "%d.%m.%Y").date()
                if d < today:
                    cursor.execute("DELETE FROM tasks WHERE id=?", (tid,))
                    changed = True
            except:
                pass
    conn.commit()
    conn.close()
    if changed:
        invalidate_tasks_cache()

def save_history_to_db(date, completed, total):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM history WHERE date=?", (date,))
    if cursor.fetchone():
        cursor.execute("UPDATE history SET completed_count=?, total_count=? WHERE date=?", (completed, total, date))
    else:
        cursor.execute("INSERT INTO history (date, completed_count, total_count) VALUES (?, ?, ?)", (date, completed, total))
    conn.commit()
    conn.close()

def get_weekly_history():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    stats = {}
    for i in range(7):
        d = datetime.datetime.now() - datetime.timedelta(days=i)
        ds = d.strftime("%d.%m.%Y")
        cursor.execute("SELECT completed_count FROM history WHERE date=?", (ds,))
        r = cursor.fetchone()
        stats[d.strftime("%d.%m")] = r[0] if r else 0
    conn.close()
    return stats

# ===== ПРИВЫЧКИ =====
def get_all_habits():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, emoji, current_streak, longest_streak FROM habits")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "emoji": r[2], "current_streak": r[3], "longest_streak": r[4]} for r in rows]

def get_habit_log(habit_id, date):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT completed FROM habit_logs WHERE habit_id=? AND date=?", (habit_id, date))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def log_habit_completion(habit_id, date):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM habit_logs WHERE habit_id=? AND date=?", (habit_id, date))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO habit_logs (habit_id, date, completed) VALUES (?, ?, 1)", (habit_id, date))
    conn.commit()
    conn.close()

def update_habit_streaks():
    today = datetime.datetime.now().strftime("%d.%m.%Y")
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%d.%m.%Y")
    habits = get_all_habits()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    for habit in habits:
        today_done = get_habit_log(habit["id"], today)
        yesterday_done = get_habit_log(habit["id"], yesterday)
        if today_done:
            new_streak = habit["current_streak"] + 1
            longest = max(habit["longest_streak"], new_streak)
            cursor.execute("UPDATE habits SET current_streak=?, longest_streak=? WHERE id=?", (new_streak, longest, habit["id"]))
        elif not yesterday_done and habit["current_streak"] > 0:
            cursor.execute("UPDATE habits SET current_streak=0 WHERE id=?", (habit["id"],))
    conn.commit()
    conn.close()

def add_habit(name, emoji):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO habits (name, emoji) VALUES (?, ?)", (name, emoji))
    conn.commit()
    conn.close()

def delete_habit(habit_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM habits WHERE id=?", (habit_id,))
    cursor.execute("DELETE FROM habit_logs WHERE habit_id=?", (habit_id,))
    conn.commit()
    conn.close()

# ===== АЧИВКИ =====
def check_and_unlock_achievements():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE done=1")
    total_done = cursor.fetchone()[0]
    cursor.execute("SELECT MAX(longest_streak) FROM habits")
    max_streak = cursor.fetchone()[0] or 0
    cursor.execute("SELECT id, name, description, unlocked FROM achievements")
    achievements = cursor.fetchall()
    new_unlocks = []
    for ach_id, name, desc, unlocked in achievements:
        if unlocked:
            continue
        should_unlock = False
        if name == "Первые шаги" and total_done >= 1:
            should_unlock = True
        elif name == "Неделя силы" and max_streak >= 7:
            should_unlock = True
        elif name == "Легенда" and total_done >= 50:
            should_unlock = True
        if should_unlock:
            today = datetime.datetime.now().strftime("%d.%m.%Y")
            cursor.execute("UPDATE achievements SET unlocked=1, date_unlocked=? WHERE id=?", (today, ach_id))
            new_unlocks.append((name, desc))
    conn.commit()
    conn.close()
    if new_unlocks:
        for name, desc in new_unlocks:
            show_achievement_popup(name, desc)

def show_achievement_popup(name, description):
    popup = ctk.CTkToplevel(app)
    popup.title("🏆 Достижение!")
    popup.geometry("450x250")
    popup.configure(fg_color=BG_SECONDARY)
    popup.attributes('-topmost', True)
    fade_in_window(popup)
    header = ctk.CTkFrame(popup, fg_color=ACCENT, height=60, corner_radius=0)
    header.pack(fill="x")
    ctk.CTkLabel(header, text="🏆 НОВОЕ ДОСТИЖЕНИЕ!", font=("Segoe UI", 22, "bold"), text_color="#ffffff").pack(pady=15)
    content = ctk.CTkFrame(popup, fg_color="transparent")
    content.pack(pady=30, padx=30)
    ctk.CTkLabel(content, text=name, font=("Segoe UI", 20, "bold"), text_color=TEXT_PRIMARY).pack()
    ctk.CTkLabel(content, text=description, font=("Segoe UI", 14), text_color=TEXT_SECONDARY).pack(pady=10)
    play_sound(1500, 200)
    play_sound(2000, 300)
    popup.after(5000, popup.destroy)

# ===== ГОЛОСОВОЕ УПРАВЛЕНИЕ =====
def listen_voice():
    def _listen():
        r = sr.Recognizer()
        try:
            status_bar_label.configure(text="🎤 Слушаю...")
            app.update()
            sample_rate = 16000
            duration = 5
            audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
            sd.wait()
            status_bar_label.configure(text="🔍 Распознаю...")
            app.update()
            with io.BytesIO() as buffer:
                with wave.open(buffer, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    wf.writeframes(audio_data.tobytes())
                buffer.seek(0)
                with sr.AudioFile(buffer) as source:
                    audio = r.record(source)
                try:
                    text = r.recognize_google(audio, language="ru-RU")
                except sr.UnknownValueError:
                    try:
                        text = r.recognize_google(audio, language="en-US")
                    except:
                        text = None
                if text:
                    add_task_to_db(text, "Средний", "Важное", "")
                    global tasks
                    tasks = get_all_tasks()
                    refresh_tasks()
                    update_status_bar()
                    speak("Добавлено: " + text)
                    status_bar_label.configure(text="✅ " + text)
                else:
                    status_bar_label.configure(text="❌ Не распознал")
                    speak("Не понял")
        except Exception as e:
            status_bar_label.configure(text="❌ Ошибка")
            print("Ошибка: " + str(e))
    threading.Thread(target=_listen, daemon=True).start()

def speak(text):
    def _speak():
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 150)
            engine.say(text)
            engine.runAndWait()
        except:
            pass
    threading.Thread(target=_speak, daemon=True).start()

# ===== ПОГОДА =====
def update_weather():
    global weather_label
    if weather_label is None:
        return
    def _update():
        try:
            url = "https://api.open-meteo.com/v1/forecast?latitude=55.3833&longitude=39.0667&current_weather=true&timezone=Europe%2FMoscow"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                current = data['current_weather']
                temp = current['temperature']
                weather_code = current['weathercode']
                if weather_code == 0:
                    desc = "Ясно ☀️"
                elif weather_code in [1, 2, 3]:
                    desc = "Облачно "
                elif weather_code in [61, 63, 65]:
                    desc = "Дождь 🌧️"
                elif weather_code in [71, 73, 75]:
                    desc = "Снег ❄️"
                else:
                    desc = "🌤️"
                app.after(0, lambda: weather_label.configure(text=str(temp) + "°C " + desc))
            else:
                app.after(0, lambda: weather_label.configure(text="🌤 Недоступно"))
        except:
            app.after(0, lambda: weather_label.configure(text="🌤 Недоступно"))
    threading.Thread(target=_update, daemon=True).start()

# ===== ОСНОВНЫЕ ФУНКЦИИ =====
def play_sound(freq=1000, dur=500):
    try:
        winsound.Beep(freq, dur)
    except:
        pass

def send_notification(title, message, sound=True):
    try:
        notification.notify(title=title, message=message, app_name="TaskFlow", timeout=10)
        if sound:
            play_sound()
    except:
        pass

def start_focus_mode(txt, mins=25):
    global timer_running, timer_remaining, timer_job
    if timer_running:
        stop_focus_mode()
    timer_running = True
    timer_remaining = mins * 60
    focus_task_label.configure(text="🎯 " + txt[:25] + "...", text_color=SUCCESS)
    update_timer_display()
    timer_job = app.after(1000, tick_timer)
    focus_frame.configure(border_color=SUCCESS, border_width=2)

def tick_timer():
    global timer_running, timer_remaining, timer_job
    if timer_running and timer_remaining > 0:
        timer_remaining -= 1
        update_timer_display()
        timer_job = app.after(1000, tick_timer)
    elif timer_running:
        stop_focus_mode()
        play_sound(1500, 1000)
        send_notification("Фокус завершен!", "Отличная работа!", False)

def stop_focus_mode():
    global timer_running, timer_job
    timer_running = False
    if timer_job:
        app.after_cancel(timer_job)
    focus_task_label.configure(text="Готов к фокусу?", text_color=TEXT_SECONDARY)
    focus_time_label.configure(text="00:00", text_color=TEXT_PRIMARY)
    focus_frame.configure(border_color=BORDER, border_width=1)

def update_timer_display():
    m = timer_remaining // 60
    s = timer_remaining % 60
    focus_time_label.configure(text="{:02d}:{:02d}".format(m, s))

def smart_schedule():
    today = datetime.datetime.now().strftime("%d.%m.%Y")
    if not os.path.exists(SCHEDULE_FILE):
        return [{"time": "09:00", "task": "💪 СПОРТ", "category": "Тренировки"}, {"time": "14:00", "task": "💻 КОДИНГ", "category": "Учёба"}]
    try:
        df = pd.read_excel(SCHEDULE_FILE)
        today_df = df[df["Дата"].astype(str).str.strip() == today]
    except:
        return []
    if today_df.empty:
        return [{"time": "09:00", "task": "💪 СПОРТ", "category": "Тренировки"}, {"time": "14:00", "task": "💻 КОДИНГ", "category": "Учёба"}]
    schedule = [(str(row["Время с"]).strip(), str(row["Время по"]).strip()) for _, row in today_df.iterrows()]
    free = []
    schedule.sort()
    if schedule[0][0] > "09:00":
        free.append(("06:00", schedule[0][0]))
    for i in range(len(schedule)-1):
        if schedule[i+1][0] > schedule[i][1]:
            free.append((schedule[i][1], schedule[i+1][0]))
    if schedule[-1][1] < "20:00":
        free.append((schedule[-1][1], "22:00"))
    planned = []
    cp = sp = False
    for s, e in free:
        try:
            dur = (datetime.datetime.strptime(e, "%H:%M") - datetime.datetime.strptime(s, "%H:%M")).total_seconds() / 3600
        except:
            continue
        if dur >= 2 and not cp:
            planned.append({"time": s, "task": "💻 КОДИНГ", "category": "Учёба"})
            cp = True
        elif dur >= 1.5 and not sp:
            planned.append({"time": s, "task": "💪 СПОРТ", "category": "Тренировки"})
            sp = True
    if not cp:
        planned.append({"time": "20:00", "task": "💻 КОДИНГ", "category": "Учёба"})
    if not sp:
        planned.append({"time": "19:00", "task": "💪 СПОРТ", "category": "Тренировки"})
    return planned

def clean_and_sync_daily(show=True):
    global tasks
    delete_old_tasks_from_db()
    tasks = get_all_tasks(force_refresh=True)
    today = datetime.datetime.now().strftime("%d.%m.%Y")
    bc = 0
    if os.path.exists(SCHEDULE_FILE):
        try:
            df = pd.read_excel(SCHEDULE_FILE)
            today_df = df[df["Дата"].astype(str).str.strip() == today]
            for _, row in today_df.iterrows():
                subj = str(row['Дисциплина']).strip()
                teach = str(row['Преподаватель']).strip()
                room = str(row['Аудитория']).strip()
                date = str(row['Дата']).strip()
                st = str(row['Время с']).strip()
                ct = "🎓 " + subj + " | " + teach + " | ауд. " + room
                cd = date + " " + st
                if not any(t["text"] == ct and t.get("deadline") == cd for t in tasks):
                    add_task_to_db(ct, "Высокий", "Пары", cd)
                    bc += 1
        except Exception as e:
            print("Ошибка Excel: " + str(e))
    tasks = get_all_tasks(force_refresh=True)
    for item in smart_schedule():
        tt = today + " " + item['time']
        if not any(t["text"] == item["task"] and t.get("deadline") == tt for t in tasks):
            add_task_to_db(item["task"], "Высокий", item["category"], tt)
    tasks = get_all_tasks(force_refresh=True)
    today_tasks = [t for t in tasks if today in str(t.get("deadline", ""))]
    comp = sum(1 for t in today_tasks if t.get("done", False))
    save_history_to_db(today, comp, len(today_tasks))
    update_motivation()
    update_status_bar()
    check_and_unlock_achievements()

def export_to_pdf():
    fn = os.path.join(BASE_DIR, "TaskFlow_" + datetime.datetime.now().strftime('%d.%m.%Y') + ".pdf")
    doc = SimpleDocTemplate(fn, pagesize=A4)
    styles = getSampleStyleSheet()
    el = [Paragraph("TaskFlow - " + user_name, styles['Title']), Spacer(10, 10)]
    today = datetime.datetime.now().strftime("%d.%m.%Y")
    tt = [t for t in tasks if today in str(t.get("deadline", ""))]
    comp = sum(1 for t in tt if t.get("done", False))
    el.append(Paragraph("Выполнено: " + str(comp) + "/" + str(len(tt)), styles['Heading2']))
    el.append(Spacer(20, 20))
    data = [["Время", "Задача", "Категория", "Статус"]]
    for t in sorted(tt, key=lambda x: x.get("deadline", "")):
        data.append([t.get("deadline", ""), t.get("text", "")[:30], t.get("category", ""), "✓" if t.get("done", False) else "○"])
    tbl = Table(data, colWidths=[100, 250, 100, 50])
    tbl.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.grey), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
    el.append(tbl)
    doc.build(el)
    send_notification("Экспорт готов!", "Отчет: " + fn)

def edit_task(tid):
    t = next((x for x in tasks if x["id"] == tid), None)
    if not t:
        return
    w = ctk.CTkToplevel(app)
    w.title("Редактировать")
    w.geometry("500x400")
    w.configure(fg_color=BG_SECONDARY)
    fade_in_window(w)
    ctk.CTkLabel(w, text="Редактирование", font=("Segoe UI", 20, "bold"), text_color=TEXT_PRIMARY).pack(pady=20)
    te = ctk.CTkEntry(w, width=400, font=("Segoe UI", 14), fg_color=BG_TERTIARY, text_color=TEXT_PRIMARY)
    te.pack(pady=10)
    te.insert(0, t.get("text", ""))
    pm = ctk.CTkOptionMenu(w, values=["Высокий", "Средний", "Низкий"], width=200, fg_color=BG_TERTIARY, button_color=ACCENT)
    pm.pack(pady=10)
    pm.set(t.get("priority", "Средний"))
    cm = ctk.CTkOptionMenu(w, values=["Учёба", "Тренировки", "Важное", "Бизнес"], width=200, fg_color=BG_TERTIARY, button_color=ACCENT)
    cm.pack(pady=10)
    cm.set(t.get("category", "Учёба"))
    de = ctk.CTkEntry(w, width=400, font=("Segoe UI", 14), fg_color=BG_TERTIARY, text_color=TEXT_PRIMARY)
    de.pack(pady=10)
    de.insert(0, t.get("deadline", ""))
    def save():
        update_task_in_db(tid, te.get().strip(), pm.get(), cm.get(), de.get().strip())
        global tasks
        tasks = get_all_tasks(force_refresh=True)
        refresh_tasks()
        w.destroy()
    ctk.CTkButton(w, text="Сохранить", command=save, fg_color=ACCENT, hover_color=ACCENT_HOVER, width=200).pack(pady=20)

def set_filter(cat):
    global current_filter
    current_filter = None if cat == "Все" else cat
    refresh_tasks()

def update_search(e=None):
    refresh_tasks()

def add_task_ui():
    global tasks
    txt = task_input.get().strip()
    if not txt:
        return
    add_task_to_db(txt, priority_menu.get(), category_menu.get(), deadline_input.get().strip())
    tasks = get_all_tasks(force_refresh=True)
    task_input.delete(0, "end")
    deadline_input.delete(0, "end")
    refresh_tasks()
    update_status_bar()
    update_motivation()
    check_and_unlock_achievements()

def toggle_task_ui(tid):
    global tasks
    t = next((x for x in tasks if x["id"] == tid), None)
    if t:
        was_done = t["done"]
        new_state = not was_done
        toggle_task_done_in_db(tid, new_state)
        tasks = get_all_tasks(force_refresh=True)
        refresh_tasks()
        update_status_bar()
        update_motivation()
        check_and_unlock_achievements()
        if new_state:
            play_sound(2000, 300)

def delete_task_ui(tid):
    global tasks
    delete_task_from_db(tid)
    tasks = get_all_tasks(force_refresh=True)
    refresh_tasks()
    update_status_bar()
    update_motivation()

def safe_destroy(c):
    for w in c.winfo_children():
        try:
            w.destroy()
        except:
            pass

def on_drag_start(event, tid, widget):
    global dragged_item, dragged_index
    dragged_item = widget
    dragged_index = next((i for i, t in enumerate(tasks) if t["id"] == tid), None)
    widget.configure(fg_color=BG_TERTIARY)

def on_drag_motion(event, tid, widget):
    global dragged_item, dragged_index
    if dragged_item is None or dragged_index is None:
        return
    target = next((i for i, t in enumerate(tasks) if t["id"] == tid), None)
    if target is None or target == dragged_index:
        return
    tasks[dragged_index], tasks[target] = tasks[target], tasks[dragged_index]
    dragged_index = target
    update_task_order([t["id"] for t in tasks])
    refresh_tasks()

def on_drag_release(event):
    global dragged_item
    if dragged_item:
        dragged_item.configure(fg_color=BG_SECONDARY)
        dragged_item = None

def refresh_tasks():
    if tasks_box is None:
        return
    comp = sum(1 for t in tasks if t.get("done", False))
    tot = len(tasks)
    progress_value = comp / tot if tot > 0 else 0
    
    # Плавная анимация прогресс-бара
    animate_progress_bar(progress_value, duration=400)
    
    if progress_value == 0:
        status_msg = "😴 Только начинаем..."
    elif progress_value < 0.25:
        status_msg = "🚀 Набираем обороты!"
    elif progress_value < 0.50:
        status_msg = "🔥 Ты в потоке!"
    elif progress_value < 0.75:
        status_msg = "⚡ Почти у цели!"
    elif progress_value < 1.0:
        status_msg = "💎 Осталось чуть-чуть!"
    else:
        status_msg = "🏆 ЛЕГЕНДА ДНЯ!"
    
    stats_label.configure(text="✓ " + str(comp) + "/" + str(tot) + "  " + status_msg)
    
    # Плавное удаление старых карточек
    old_cards = tasks_box.winfo_children()
    for i, card in enumerate(old_cards):
        card.after(i * 10, lambda c=card: animate_color(c, c.cget("fg_color") if hasattr(c, "_fg_color") else BG_SECONDARY, BG_PRIMARY, 150, lambda w=c: w.destroy()))
    
    # Плавное появление новых карточек с задержкой
    srch = search_input.get().lower()
    card_index = 0
    for t in tasks:
        if current_filter and t.get("category") != current_filter:
            continue
        if srch and srch not in t.get("text", "").lower():
            continue
        
        # Задержка для плавного появления
        delay = len(old_cards) * 10 + 150 + card_index * 30
        tasks_box.after(delay, lambda task=t: create_card_animated(task))
        card_index += 1

def create_card_animated(t):
    """Создаёт карточку с плавной анимацией появления"""
    is_class = t.get("category") == "Пары" or "🎓" in t.get("text", "")
    if is_class:
        card = ctk.CTkFrame(tasks_box, fg_color=BG_PRIMARY, corner_radius=12, border_width=1, border_color=ACCENT)
        card.pack(fill="x", padx=10, pady=8)
        
        # Плавное появление
        fade_in_card(card, duration=250)
        
        parts = t.get("text", "").split(" | ")
        subj = parts[0].replace("🎓 ", "") if parts else ""
        det = " | ".join(parts[1:]) if len(parts) > 1 else ""
        ctk.CTkLabel(card, text="⏰ " + str(t.get('deadline', '')), font=("Segoe UI", 12, "bold"), text_color=ACCENT).pack(anchor="w", padx=15, pady=(10, 5))
        ctk.CTkLabel(card, text=subj, font=("Segoe UI", 15, "bold"), text_color=TEXT_PRIMARY, anchor="w").pack(fill="x", padx=15, pady=(0, 5))
        if det:
            ctk.CTkLabel(card, text=det, font=("Segoe UI", 12), text_color=TEXT_SECONDARY, anchor="w").pack(fill="x", padx=15, pady=(0, 10))
    else:
        card = ctk.CTkFrame(tasks_box, fg_color=BG_PRIMARY, corner_radius=12, border_width=1, border_color=BORDER)
        card.pack(fill="x", padx=10, pady=6)
        
        # Плавное появление
        fade_in_card(card, duration=250)
        
        card.bind("<Button-1>", lambda e, tid=t["id"], w=card: on_drag_start(e, tid, w))
        card.bind("<B1-Motion>", lambda e, tid=t["id"], w=card: on_drag_motion(e, tid, w))
        card.bind("<ButtonRelease-1>", lambda e: on_drag_release(e))
        tf = ctk.CTkFrame(card, fg_color="transparent")
        tf.pack(side="left", fill="both", expand=True, padx=15, pady=10)
        task_id = t["id"]
        is_done = t.get("done", False)
        cb = ctk.CTkCheckBox(tf, text=t.get("text", ""), font=("Segoe UI", 13), text_color=TEXT_PRIMARY, command=lambda tid=task_id: toggle_task_ui(tid))
        if is_done:
            cb.select()
        else:
            cb.deselect()
        cb.pack(side="left")
        ctk.CTkLabel(tf, text="[" + str(t.get('category', '')) + "]", font=("Segoe UI", 10), text_color=TEXT_MUTED).pack(side="left", padx=10)
        ctk.CTkButton(card, text="✏️", width=40, height=30, fg_color=BG_TERTIARY, hover_color=ACCENT, text_color=TEXT_PRIMARY, command=lambda tid=task_id: edit_task(tid)).pack(side="right", padx=4)
        ctk.CTkButton(card, text="🎯", width=40, height=30, fg_color=BG_TERTIARY, hover_color=SUCCESS, text_color=TEXT_PRIMARY, command=lambda txt=t.get("text", ""): start_focus_mode(txt, 25)).pack(side="right", padx=4)
        ctk.CTkButton(card, text="🗑", width=40, height=30, fg_color=BG_TERTIARY, hover_color=DANGER, text_color=TEXT_PRIMARY, command=lambda tid=task_id: delete_task_ui(tid)).pack(side="right", padx=4)
        
def clear_content_animated():
    """Плавное удаление контента"""
    widgets = content_frame.winfo_children()
    for i, widget in enumerate(widgets):
        widget.after(i * 20, lambda w=widget: animate_color(w, w.cget("fg_color") if hasattr(w, "_fg_color") else BG_PRIMARY, BG_PRIMARY, 200, lambda wdg=w: wdg.destroy()))
    
    # Ждём завершения анимации
    content_frame.after(len(widgets) * 20 + 250, lambda: None)

def show_tasks_view():
    clear_content_animated()
    sf = ctk.CTkFrame(content_frame, fg_color=BG_SECONDARY, corner_radius=12, border_width=1, border_color=BORDER)
    sf.pack(pady=10, padx=20)
    global stats_label, progress
    stats_label = ctk.CTkLabel(sf, text="✓ 0/0", font=("Segoe UI", 16, "bold"), text_color=TEXT_PRIMARY)
    stats_label.pack(pady=10, padx=20)
    progress = ctk.CTkProgressBar(content_frame, width=700, height=8, fg_color=BG_TERTIARY, progress_color=ACCENT, corner_radius=4)
    progress.pack(pady=10)
    progress.set(0)
    global task_input, search_input, priority_menu, category_menu, deadline_input, tasks_box
    inf = ctk.CTkFrame(content_frame, fg_color="transparent")
    inf.pack(pady=10, padx=20)
    task_input = ctk.CTkEntry(inf, width=350, placeholder_text="Новая задача...", font=("Segoe UI", 13), fg_color=BG_SECONDARY, text_color=TEXT_PRIMARY, border_color=BORDER, border_width=1, corner_radius=8)
    task_input.pack(side="left", padx=(0, 8))
    mic_btn = ctk.CTkButton(inf, text="🎤", width=40, height=32, fg_color=ACCENT, hover_color=ACCENT_HOVER, command=listen_voice)
    mic_btn.pack(side="left", padx=5)
    search_input = ctk.CTkEntry(inf, width=200, placeholder_text="Поиск...", font=("Segoe UI", 12), fg_color=BG_SECONDARY, text_color=TEXT_PRIMARY, border_color=BORDER, border_width=1, corner_radius=8)
    search_input.pack(side="left", padx=8)
    search_input.bind("<KeyRelease>", update_search)
    setf = ctk.CTkFrame(content_frame, fg_color="transparent")
    setf.pack(pady=5, padx=20)
    priority_menu = ctk.CTkOptionMenu(setf, values=["Высокий", "Средний", "Низкий"], width=120, font=("Segoe UI", 11), fg_color=BG_SECONDARY, button_color=ACCENT, corner_radius=6)
    priority_menu.pack(side="left", padx=5)
    priority_menu.set("Средний")
    category_menu = ctk.CTkOptionMenu(setf, values=["Учёба", "Тренировки", "Важное", "Бизнес", "Пары"], width=120, font=("Segoe UI", 11), fg_color=BG_SECONDARY, button_color=ACCENT, corner_radius=6)
    category_menu.pack(side="left", padx=5)
    category_menu.set("Учёба")
    deadline_input = ctk.CTkEntry(setf, width=160, placeholder_text="ДД.ММ.ГГГГ ЧЧ:ММ", font=("Segoe UI", 11), fg_color=BG_SECONDARY, text_color=TEXT_PRIMARY, border_color=BORDER, border_width=1, corner_radius=6)
    deadline_input.pack(side="left", padx=5)
    ctk.CTkButton(setf, text="➕ Добавить", command=add_task_ui, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=("Segoe UI", 12, "bold"), width=110, height=32, corner_radius=6).pack(side="left", padx=5)
    filter_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    filter_frame.pack(pady=5, padx=20)
    ctk.CTkButton(filter_frame, text="📋 Все", command=lambda: set_filter("Все"), fg_color=BG_SECONDARY, hover_color=ACCENT, height=28, width=70, font=("Segoe UI", 11)).pack(side="left", padx=4)
    ctk.CTkButton(filter_frame, text="🎓 Пары", command=lambda: set_filter("Пары"), fg_color=BG_SECONDARY, hover_color=ACCENT, height=28, width=70, font=("Segoe UI", 11)).pack(side="left", padx=4)
    ctk.CTkButton(filter_frame, text="💻 Учёба", command=lambda: set_filter("Учёба"), fg_color=BG_SECONDARY, hover_color=ACCENT, height=28, width=70, font=("Segoe UI", 11)).pack(side="left", padx=4)
    ctk.CTkButton(filter_frame, text="💪 Спорт", command=lambda: set_filter("Тренировки"), fg_color=BG_SECONDARY, hover_color=ACCENT, height=28, width=70, font=("Segoe UI", 11)).pack(side="left", padx=4)
    ctk.CTkButton(filter_frame, text="📤 PDF", command=export_to_pdf, fg_color=BG_SECONDARY, hover_color=ACCENT, height=28, width=70, font=("Segoe UI", 11)).pack(side="right", padx=4)
    tasks_box = ctk.CTkScrollableFrame(content_frame, width=750, height=320, fg_color="transparent")
    tasks_box.pack(pady=10, padx=20)
    refresh_tasks()

def show_history_view():
    clear_content_animated()
    ctk.CTkLabel(content_frame, text="📈 Продуктивность за неделю", font=("Segoe UI", 24, "bold"), text_color=TEXT_PRIMARY).pack(pady=20)
    stats = get_weekly_history()
    fig, ax = plt.subplots(figsize=(10, 5), facecolor=BG_PRIMARY)
    ax.set_facecolor(BG_PRIMARY)
    dates = list(stats.keys())[::-1]
    vals = list(stats.values())[::-1]
    ax.bar(dates, vals, color=ACCENT)
    ax.set_title("Выполненные задачи", color=TEXT_PRIMARY, fontsize=16)
    ax.set_ylabel("Количество", color=TEXT_PRIMARY)
    ax.tick_params(colors=TEXT_PRIMARY)
    for sp in ax.spines.values():
        sp.set_color(BORDER)
    FigureCanvasTkAgg(fig, master=content_frame).get_tk_widget().pack(pady=20)

def show_habits_view():
    clear_content_animated()
    update_habit_streaks()
    ctk.CTkLabel(content_frame, text="🔥 Мои стрики", font=("Segoe UI", 24, "bold"), text_color=TEXT_PRIMARY).pack(pady=20)
    habits = get_all_habits()
    today = datetime.datetime.now().strftime("%d.%m.%Y")
    habits_container = ctk.CTkScrollableFrame(content_frame, width=750, height=400, fg_color="transparent")
    habits_container.pack(pady=10, padx=20)
    for habit in habits:
        card = ctk.CTkFrame(habits_container, fg_color=BG_SECONDARY, corner_radius=12, border_width=1, border_color=BORDER)
        card.pack(fill="x", padx=10, pady=8)
        left_frame = ctk.CTkFrame(card, fg_color="transparent")
        left_frame.pack(side="left", fill="y", padx=15, pady=10)
        ctk.CTkLabel(left_frame, text=habit["emoji"], font=("Segoe UI", 28)).pack()
        ctk.CTkLabel(left_frame, text=habit["name"], font=("Segoe UI", 14, "bold"), text_color=TEXT_PRIMARY).pack()
        center_frame = ctk.CTkFrame(card, fg_color="transparent")
        center_frame.pack(side="left", fill="both", expand=True, padx=20)
        streak_color = SUCCESS if habit["current_streak"] > 0 else DANGER
        streak_text = "🔥 " + str(habit['current_streak']) + " дней" if habit["current_streak"] > 0 else "💔 0 дней"
        ctk.CTkLabel(center_frame, text=streak_text, font=("Segoe UI", 18, "bold"), text_color=streak_color).pack(pady=5)
        ctk.CTkLabel(center_frame, text="Рекорд: " + str(habit['longest_streak']) + " дней", font=("Segoe UI", 11), text_color=TEXT_SECONDARY).pack()
        right_frame = ctk.CTkFrame(card, fg_color="transparent")
        right_frame.pack(side="right", fill="y", padx=15, pady=10)
        today_done = get_habit_log(habit["id"], today)
        if today_done:
            ctk.CTkLabel(right_frame, text="✅ Выполнено", font=("Segoe UI", 12, "bold"), text_color=SUCCESS).pack(pady=10)
        else:
            def mark_done(hid=habit["id"]):
                log_habit_completion(hid, today)
                show_habits_view()
                update_motivation()
                send_notification("🔥 Стрик!", "Привычка '" + habit['name'] + "' выполнена!")
            ctk.CTkButton(right_frame, text="Отметить", command=mark_done, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=("Segoe UI", 12, "bold"), width=90, height=32).pack(pady=5)
    add_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    add_frame.pack(pady=20, padx=20)
    ctk.CTkLabel(add_frame, text="Новая привычка:", font=("Segoe UI", 13), text_color=TEXT_SECONDARY).pack(side="left", padx=10)
    habit_name_entry = ctk.CTkEntry(add_frame, width=180, placeholder_text="Название", font=("Segoe UI", 12), fg_color=BG_SECONDARY, text_color=TEXT_PRIMARY)
    habit_name_entry.pack(side="left", padx=5)
    habit_emoji_entry = ctk.CTkEntry(add_frame, width=70, placeholder_text="Эмодзи", font=("Segoe UI", 12), fg_color=BG_SECONDARY, text_color=TEXT_PRIMARY)
    habit_emoji_entry.pack(side="left", padx=5)
    habit_emoji_entry.insert(0, "🎯")
    def add_new_habit():
        name = habit_name_entry.get().strip()
        emoji = habit_emoji_entry.get().strip()
        if name:
            add_habit(name, emoji)
            show_habits_view()
    ctk.CTkButton(add_frame, text="➕ Добавить", command=add_new_habit, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=("Segoe UI", 12, "bold"), width=110, height=32).pack(side="left", padx=10)

def show_calendar_view():
    clear_content_animated()
    ctk.CTkLabel(content_frame, text="Расписание", font=("Segoe UI", 24, "bold"), text_color=TEXT_PRIMARY).pack(pady=20)
    if not os.path.exists(SCHEDULE_FILE):
        ctk.CTkLabel(content_frame, text="Файл не найден!", font=("Segoe UI", 14), text_color=DANGER).pack(pady=20)
        return
    try:
        df = pd.read_excel(SCHEDULE_FILE)
        data = [["День", "Дата", "Время", "Дисциплина", "Преподаватель", "Аудитория"]]
        for _, row in df.iterrows():
            day = str(row['День недели']).strip()
            date = str(row['Дата']).strip()
            time_start = str(row['Время с']).strip()
            time_end = str(row['Время по']).strip()
            subject = str(row['Дисциплина']).strip()
            teacher = str(row['Преподаватель']).strip()
            room = str(row['Аудитория']).strip()
            time_range = time_start + "-" + time_end
            data.append([day, date, time_range, subject, teacher, room])
        sf = ctk.CTkScrollableFrame(content_frame, width=800, height=450, fg_color="transparent")
        sf.pack(pady=20, padx=20)
        hf = ctk.CTkFrame(sf, fg_color=BG_SECONDARY, corner_radius=8)
        hf.pack(fill="x", pady=5)
        for h in data[0]:
            ctk.CTkLabel(hf, text=h, font=("Segoe UI", 13, "bold"), text_color=TEXT_PRIMARY, width=130).pack(side="left", padx=10, pady=10)
        for rd in data[1:]:
            rf = ctk.CTkFrame(sf, fg_color=BG_SECONDARY, corner_radius=8)
            rf.pack(fill="x", pady=2)
            for c in rd:
                ctk.CTkLabel(rf, text=str(c), font=("Segoe UI", 11), text_color=TEXT_SECONDARY, width=130).pack(side="left", padx=10, pady=8)
    except Exception as e:
        ctk.CTkLabel(content_frame, text="Ошибка: " + str(e), font=("Segoe UI", 14), text_color=DANGER).pack(pady=20)

def show_telegram_view():
    clear_content_animated()
    ctk.CTkLabel(content_frame, text="🌐 Telegram-бот", font=("Segoe UI", 24, "bold"), text_color=TEXT_PRIMARY).pack(pady=20)
    info_text = "1. @BotFather\n2. /newbot\n3. Получить токен\n4. pip install python-telegram-bot\n5. Создать bot.py\n6. Запустить на VPS"
    ctk.CTkLabel(content_frame, text=info_text, font=("Segoe UI", 13), text_color=TEXT_SECONDARY, justify="left").pack(pady=20, padx=40)

def show_ai_view():
    clear_content_animated()
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        if r.status_code != 200:
            raise Exception("Ollama не отвечает")
    except:
        ctk.CTkLabel(content_frame, text="❌ Ollama не запущен!", font=("Segoe UI", 18, "bold"), text_color=DANGER).pack(pady=30)
        return
    ctk.CTkLabel(content_frame, text="🤖 AI-Ассистент", font=("Segoe UI", 24, "bold"), text_color=TEXT_PRIMARY).pack(pady=20)
    questions_frame = ctk.CTkScrollableFrame(content_frame, width=800, height=350, fg_color=BG_SECONDARY)
    questions_frame.pack(pady=10, padx=20, fill="both", expand=True)
    questions = [("Во сколько просыпаешься?", "07:00"), ("Во сколько ложишься?", "23:00"), ("Дорога до учебы (мин)?", "30"), ("Часов на кодинг?", "2"), ("Дней спорта в неделю?", "3"), ("Часов на еду?", "2"), ("Часов на отдых?", "2"), ("Часов на соцсети?", "1"), ("Часов пар?", "4"), ("Пик продуктивности?", "утро"), ("Цель на 3 месяца?", profile.get("goal", "Выучить Python")), ("Курсы (часов/нед)?", "2"), ("Общение (часов)?", "1"), ("Обязанности (часов)?", "1"), ("Буфер (часов)?", "1")]
    answer_entries = {}
    for i, (q, d) in enumerate(questions):
        q_frame = ctk.CTkFrame(questions_frame, fg_color="transparent")
        q_frame.pack(fill="x", pady=5, padx=15)
        ctk.CTkLabel(q_frame, text=str(i+1) + ". " + q, font=("Segoe UI", 12), text_color=TEXT_PRIMARY).pack(anchor="w")
        entry = ctk.CTkEntry(q_frame, width=550, font=("Segoe UI", 12), fg_color=BG_TERTIARY, text_color=TEXT_PRIMARY)
        entry.insert(0, d)
        entry.pack(anchor="w")
        answer_entries[i] = entry
    def generate():
        answers = {}
        for i, e in answer_entries.items():
            answers["q_" + str(i+1)] = e.get().strip()
        prompt = "Создай расписание для студента:\n" + json_lib.dumps(answers, ensure_ascii=False, indent=2) + "\nФормат: ВРЕМЯ | ЗАДАЧА"
        loading = ctk.CTkLabel(content_frame, text="🤖 AI думает...", font=("Segoe UI", 13), text_color=WARNING)
        loading.pack(pady=10)
        app.update()
        try:
            response = requests.post(OLLAMA_API_URL, json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}, timeout=180)
            resp = response.json().get("response", "") if response.status_code == 200 else ""
        except:
            resp = ""
        loading.destroy()
        if resp:
            clear_content_animated()
            ctk.CTkLabel(content_frame, text="🎉 Готово!", font=("Segoe UI", 22, "bold"), text_color=SUCCESS).pack(pady=20)
            txt = ctk.CTkTextbox(content_frame, width=800, height=400, font=("Segoe UI", 12), fg_color=BG_SECONDARY, text_color=TEXT_PRIMARY)
            txt.pack(pady=10)
            txt.insert("0.0", resp)
            txt.configure(state="disabled")
            def apply():
                lines = resp.split("\n")
                today = datetime.datetime.now().strftime("%d.%m.%Y")
                for line in lines:
                    if "|" in line:
                        parts = line.split("|")
                        if len(parts) >= 2:
                            time_p = parts[0].strip().split("-")[0].strip()
                            act = parts[1].strip()
                            if ":" in time_p and len(time_p) == 5:
                                add_task_to_db(act, "Высокий", "Важное", today + " " + time_p)
                global tasks
                tasks = get_all_tasks(force_refresh=True)
                show_tasks_view()
                update_status_bar()
                update_motivation()
                send_notification("AI", "Расписание добавлено!")
            ctk.CTkButton(content_frame, text="✅ Применить", command=apply, fg_color=ACCENT, hover_color=ACCENT_HOVER, height=38).pack(pady=20)
        else:
            ctk.CTkLabel(content_frame, text="Ошибка AI", font=("Segoe UI", 14), text_color=DANGER).pack(pady=20)
    ctk.CTkButton(content_frame, text="🚀 Сгенерировать", command=generate, fg_color=ACCENT, hover_color=ACCENT_HOVER, height=38).pack(pady=20)

def update_greeting():
    hour = datetime.datetime.now().hour
    if 6 <= hour < 11:
        text = "🌅 Доброе утро, " + user_name + "!"
    elif 11 <= hour < 17:
        text = "☀️ В разгаре дня, " + user_name + "!"
    elif 17 <= hour < 22:
        text = "🌆 Добрый вечер, " + user_name + "!"
    else:
        text = "🌙 Пора отдыхать, " + user_name
    greeting_label.configure(text=text)

def update_motivation():
    today = datetime.datetime.now().strftime("%d.%m.%Y")
    today_tasks = [t for t in tasks if today in str(t.get("deadline", ""))]
    completed = sum(1 for t in today_tasks if t.get("done", False))
    total = len(today_tasks)
    habits = get_all_habits()
    active_streaks = [h for h in habits if h["current_streak"] > 0]
    streak_info = " | 🔥 " + str(len(active_streaks)) + " стриков" if active_streaks else ""
    if total == 0:
        quote = "✨ Добавь задачи — и начни покорять день!" + streak_info
    elif completed == 0:
        quote = random.choice(MOTIVATION_QUOTES) + "\n🎯 Цель: " + profile.get('goal', 'Достигать высот')
    elif completed < total / 2:
        quote = "🔥 " + str(completed) + "/" + str(total) + " выполнено. Продолжай!" + streak_info
    elif completed < total:
        quote = "⚡ " + str(completed) + "/" + str(total) + " — почти у цели!" + streak_info
    else:
        quote = "🏆 ЛЕГЕНДА! Все " + str(total) + " задач закрыты!" + streak_info
    motivation_label.configure(text=quote)

def update_status_bar():
    now = datetime.datetime.now()
    current_time = now.strftime("%H:%M")
    today = now.strftime("%d.%m.%Y")
    today_tasks = [t for t in tasks if today in str(t.get("deadline", "")) and not t.get("done", False)]
    if not today_tasks:
        status_bar_label.configure(text="✨ Все задачи выполнены!")
        return
    def get_time(task):
        try:
            return task.get("deadline", "").split(" ")[1]
        except:
            return "99:99"
    today_tasks.sort(key=get_time)
    current_task = next((t for t in today_tasks if get_time(t) >= current_time), None)
    if current_task:
        status_bar_label.configure(text="📍 Сейчас: " + current_task.get('text', '')[:50] + "  |  ⏰ " + get_time(current_task) + "  |  🎯 Вперёд!")
    else:
        status_bar_label.configure(text="✨ Все задачи на сегодня выполнены!")

def refresh_greeting_periodically():
    update_greeting()
    app.after(60000, refresh_greeting_periodically)

def refresh_weather_periodically():
    update_weather()
    app.after(1800000, refresh_weather_periodically)

# ===== ИНИЦИАЛИЗАЦИЯ БД =====
init_db()
profile = get_profile()
if not profile:
    name = ctk.CTkInputDialog(text="Как обращаться?", title="Привет!").get_input() or "Друг"
    goal = ctk.CTkInputDialog(text="Цель на 3 месяца?", title="Цель").get_input() or "Выучить Python"
    coding = ctk.CTkInputDialog(text="Часов на кодинг?", title="Кодинг").get_input() or "2"
    sport = ctk.CTkInputDialog(text="Часов на спорт?", title="Спорт").get_input() or "1.5"
    save_profile(name, goal, float(coding), float(sport))
    profile = get_profile()
user_name = profile.get("name", "Друг")
tasks = get_all_tasks()

# ===== ИНТЕРФЕЙС =====
app.configure(fg_color=BG_PRIMARY)

sidebar = ctk.CTkFrame(app, width=320, fg_color=BG_SECONDARY, corner_radius=0)
sidebar.pack(side="left", fill="y")

lf = ctk.CTkFrame(sidebar, fg_color="transparent")
lf.pack(pady=(30, 20), padx=25)
ctk.CTkLabel(lf, text="TaskFlow", font=("Segoe UI", 28, "bold"), text_color=TEXT_PRIMARY).pack()
greeting_label = ctk.CTkLabel(lf, text="🌅 Привет, " + user_name + "!", font=("Segoe UI", 13), text_color=TEXT_SECONDARY, wraplength=280)
greeting_label.pack(pady=(5, 0))

gf = ctk.CTkFrame(sidebar, fg_color=BG_TERTIARY, corner_radius=10, border_width=1, border_color=BORDER)
gf.pack(fill="x", padx=20, pady=15)
ctk.CTkLabel(gf, text="🎯 ЦЕЛИ", font=("Segoe UI", 13, "bold"), text_color=ACCENT).pack(pady=(10, 5))
ctk.CTkLabel(gf, text=profile.get("goal", ""), font=("Segoe UI", 11), wraplength=280, text_color=TEXT_SECONDARY, justify="center").pack(padx=15, pady=(0, 10))

ff = ctk.CTkFrame(sidebar, fg_color=BG_TERTIARY, corner_radius=10, border_width=1, border_color=BORDER)
ff.pack(fill="x", padx=20, pady=15)
ctk.CTkLabel(ff, text="🍅 ФОКУС", font=("Segoe UI", 13, "bold"), text_color=SUCCESS).pack(pady=(10, 5))
focus_task_label = ctk.CTkLabel(ff, text="Готов?", font=("Segoe UI", 11), text_color=TEXT_SECONDARY)
focus_task_label.pack(pady=(0, 5))
focus_time_label = ctk.CTkLabel(ff, text="00:00", font=("Segoe UI", 36, "bold"), text_color=TEXT_PRIMARY)
focus_time_label.pack(pady=5)
focus_frame = ff
ctk.CTkButton(ff, text="▶️ Старт", font=("Segoe UI", 12, "bold"), fg_color=ACCENT, hover_color=ACCENT_HOVER, height=36, corner_radius=8, command=lambda: start_focus_mode("Фокус", 25)).pack(pady=(0, 10), padx=15, fill="x")

nav = [("📋 Задачи", "tasks"), ("🔥 Привычки", "habits"), ("📈 История", "history"), ("📅 Календарь", "calendar"), ("🌐 Telegram", "telegram"), ("🤖 AI", "ai")]
for txt, view in nav:
    if view == "tasks":
        cmd = show_tasks_view
    elif view == "habits":
        cmd = show_habits_view
    elif view == "history":
        cmd = show_history_view
    elif view == "calendar":
        cmd = show_calendar_view
    elif view == "telegram":
        cmd = show_telegram_view
    else:
        cmd = show_ai_view
    btn = ctk.CTkButton(sidebar, text=txt, font=("Segoe UI", 13, "bold"), fg_color=BG_TERTIARY, text_color=TEXT_PRIMARY, hover_color=ACCENT, height=42, corner_radius=8, command=cmd)
    btn.pack(pady=3, padx=20, fill="x")

rs = ctk.CTkFrame(app, width=220, fg_color=BG_SECONDARY, corner_radius=0)
rs.pack(side="right", fill="y")
ctk.CTkLabel(rs, text="⚙️", font=("Segoe UI", 16, "bold"), text_color=TEXT_PRIMARY).pack(pady=(30, 10), padx=20)
weather_frame = ctk.CTkFrame(rs, fg_color=BG_TERTIARY, corner_radius=8)
weather_frame.pack(fill="x", padx=20, pady=10)
weather_label = ctk.CTkLabel(weather_frame, text="🌤 Загрузка...", font=("Segoe UI", 11), text_color=TEXT_SECONDARY, wraplength=180)
weather_label.pack(pady=10, padx=10)

def toggle_theme():
    global current_theme
    if current_theme == "dark":
        ctk.set_appearance_mode("light")
        current_theme = "light"
        theme_btn.configure(text="🌙")
    else:
        ctk.set_appearance_mode("dark")
        current_theme = "dark"
        theme_btn.configure(text="☀️")

theme_btn = ctk.CTkButton(rs, text="☀️", font=("Segoe UI", 12, "bold"), fg_color=ACCENT, hover_color=ACCENT_HOVER, height=38, command=toggle_theme)
theme_btn.pack(pady=8, padx=20, fill="x")
ctk.CTkButton(rs, text="🔄 Синхронизировать", font=("Segoe UI", 11, "bold"), fg_color=ACCENT, hover_color=ACCENT_HOVER, height=38, command=lambda: clean_and_sync_daily(True)).pack(pady=8, padx=20, fill="x")

main = ctk.CTkFrame(app, fg_color=BG_PRIMARY)
main.pack(side="left", fill="both", expand=True)

hf = ctk.CTkFrame(main, fg_color="transparent")
hf.pack(pady=(20, 5), padx=30)
ctk.CTkLabel(hf, text="МОЙ ДЕНЬ", font=("Segoe UI", 32, "bold"), text_color=TEXT_PRIMARY).pack()

motivation_frame = ctk.CTkFrame(main, fg_color=BG_SECONDARY, corner_radius=10, border_width=1, border_color=BORDER)
motivation_frame.pack(pady=10, padx=30, fill="x")
motivation_label = ctk.CTkLabel(motivation_frame, text="✨ Загрузка...", font=("Segoe UI", 14), text_color=TEXT_SECONDARY, wraplength=750, justify="center")
motivation_label.pack(pady=12, padx=20)

content_frame = ctk.CTkFrame(main, fg_color=BG_PRIMARY, corner_radius=10)
content_frame.pack(pady=10, padx=30, fill="both", expand=True)

status_bar = ctk.CTkFrame(app, height=38, fg_color=BG_SECONDARY, corner_radius=0)
status_bar.pack(side="bottom", fill="x")
status_bar_label = ctk.CTkLabel(status_bar, text="📍 Загрузка...", font=("Segoe UI", 11, "bold"), text_color=TEXT_SECONDARY)
status_bar_label.pack(pady=8, padx=20, anchor="w")

def auto_update():
    clean_and_sync_daily(False)
    app.after(auto_update_interval, auto_update)

def on_closing():
    try:
        plt.close('all')
    except:
        pass
    app.destroy()

app.protocol("WM_DELETE_WINDOW", on_closing)

# ===== ЗАПУСК =====
show_tasks_view()
update_greeting()
update_motivation()
update_status_bar()

def delayed_weather_update():
    update_weather()
    refresh_weather_periodically()

app.after(2000, delayed_weather_update)
refresh_greeting_periodically()
clean_and_sync_daily(True)
auto_update()
app.mainloop()
## Мои достижения
- Создал приложение TaskFlow с AI
- Прикрутил Telegram-бота
- Загрузил код на GitHub! 🎉
