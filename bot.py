from telegram.request import HTTPXRequest
import sqlite3
import os
import datetime
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ===== НАСТРОЙКИ =====
TOKEN = "8640467186:AAELymnVpz5cnC2XFomKP6jh-hWhbHN89tY"  # ← Вставь токен от BotFather
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "taskflow.db")

# ===== БАЗА ДАННЫХ =====
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def get_user_profile():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profile LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    if result:
        return {"name": result[1], "goal": result[2], "coding_hours": result[3], "sport_hours": result[4]}
    return {"name": "Друг", "goal": "Достигать высот", "coding_hours": 2, "sport_hours": 1.5}

def get_today_tasks():
    conn = get_db_connection()
    cursor = conn.cursor()
    today = datetime.datetime.now().strftime("%d.%m.%Y")
    cursor.execute("""
        SELECT id, text, done, category, deadline, priority 
        FROM tasks 
        WHERE deadline LIKE ? 
        ORDER BY deadline
    """, (f"{today}%",))
    tasks = cursor.fetchall()
    conn.close()
    return [{"text": t[1], "done": bool(t[2]), "category": t[3], "deadline": t[4], "priority": t[5]} for t in tasks]

def get_habits():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, emoji, current_streak, longest_streak FROM habits")
    habits = cursor.fetchall()
    conn.close()
    return [{"name": h[0], "emoji": h[1], "current_streak": h[2], "longest_streak": h[3]} for h in habits]

def add_task_from_telegram(text, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tasks")
    count = cursor.fetchone()[0]
    cursor.execute(
        "INSERT INTO tasks (text, done, priority, category, deadline, display_order) VALUES (?, 0, ?, ?, ?, ?)",
        (text, "Средний", "Важное", "", count)
    )
    conn.commit()
    conn.close()

# ===== КОМАНДЫ БОТА =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    profile = get_user_profile()
    await update.message.reply_text(
        f"👋 Привет, {profile['name']}!\n\n"
        f"🎯 Твоя цель: {profile['goal']}\n"
        f"💻 Кодинг: {profile['coding_hours']} ч/день\n"
        f"💪 Спорт: {profile['sport_hours']} ч/день\n\n"
        f"📋 Доступные команды:\n"
        f"/plan — план на сегодня\n"
        f"/add [задача] — добавить задачу\n"
        f"/habits — мои стрики\n"
        f"/stats — статистика"
    )

async def plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /plan — показывает план на сегодня"""
    tasks = get_today_tasks()
    profile = get_user_profile()
    
    if not tasks:
        await update.message.reply_text("📭 На сегодня задач нет! Отдыхай или добавь новые задачи.")
        return
    
    completed = sum(1 for t in tasks if t["done"])
    total = len(tasks)
    
    message = f"📅 **План на сегодня**\n"
    message += f"Выполнено: {completed}/{total}\n\n"
    
    # Группируем задачи по категориям
    categories = {}
    for task in tasks:
        cat = task["category"] or "Другое"
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(task)
    
    for cat, cat_tasks in categories.items():
        emoji = "📚" if "Учёба" in cat else "💪" if "Спорт" in cat else "💻" if "Кодинг" in cat else "📌"
        message += f"\n{emoji} **{cat}**\n"
        for task in cat_tasks:
            status = "✅" if task["done"] else "⬜"
            time = task["deadline"].split(" ")[1] if " " in task["deadline"] else ""
            message += f"{status} {time} {task['text']}\n"
    
    await update.message.reply_text(message)

async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /add — добавляет задачу"""
    if not context.args:
        await update.message.reply_text("❌ Использование: /add [текст задачи]\n\nПример: /add Сделать лабу по Python")
        return
    
    task_text = " ".join(context.args)
    add_task_from_telegram(task_text, update.effective_user.id)
    
    await update.message.reply_text(f"✅ Задача добавлена:\n\n{task_text}")

async def habits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /habits — показывает стрики"""
    habits_list = get_habits()
    
    if not habits_list:
        await update.message.reply_text("🔥 Пока нет активных привычек")
        return
    
    message = "🔥 **Мои стрики**\n\n"
    for habit in habits_list:
        emoji = habit["emoji"]
        name = habit["name"]
        current = habit["current_streak"]
        longest = habit["longest_streak"]
        
        if current > 0:
            message += f"{emoji} **{name}**: {current} дней 🔥\n"
            message += f"   Рекорд: {longest} дней\n\n"
        else:
            message += f"{emoji} **{name}**: 0 дней 💔\n"
            message += f"   Рекорд: {longest} дней\n\n"
    
    await update.message.reply_text(message)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats — показывает статистику"""
    tasks = get_today_tasks()
    completed = sum(1 for t in tasks if t["done"])
    total = len(tasks)
    
    progress = (completed / total * 100) if total > 0 else 0
    
    message = f"📊 **Статистика**\n\n"
    message += f"Сегодня: {completed}/{total} задач ({progress:.0f}%)\n"
    
    if progress == 100:
        message += "\n🏆 ЛЕГЕНДА! Все задачи выполнены!"
    elif progress >= 75:
        message += "\n⚡ Почти у цели! Так держать!"
    elif progress >= 50:
        message += "\n🔥 Ты в потоке! Продолжай!"
    elif progress >= 25:
        message += "\n🚀 Набираем обороты!"
    else:
        message += "\n😴 Только начинаем... Давай!"
    
    await update.message.reply_text(message)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обычные сообщения (не команды)"""
    text = update.message.text
    
    # Если сообщение не команда — добавляем как задачу
    if text and not text.startswith("/"):
        add_task_from_telegram(text, update.effective_user.id)
        await update.message.reply_text(f"✅ Добавлено в задачи:\n\n{text}")

# ===== УТРОННИЕ НАПОМИНАНИЯ =====
async def send_morning_reminder(app):
    """Отправляет утренний план всем пользователям (заглушка)"""
    # Здесь можно добавить рассылку утренних планов
    # Для начала просто выводим в консоль
    print("🌅 Morning reminder sent!")

# ===== ЗАПУСК БОТА =====
def main():
    print(" Запуск Telegram-бота...")
    
    # ===== НАСТРОЙКИ ПРОКСИ =====
    # Если у тебя есть прокси, раскомментируй строки ниже:
    # PROXY_URL = "socks5://127.0.0.1:1080"  # Замени на свой прокси
    # request = HTTPXRequest(proxy_url=PROXY_URL)
    # application = Application.builder().token(TOKEN).request(request).build()
    
    # Без прокси (попробуем сначала так):
    from telegram.request import HTTPXRequest
    request = HTTPXRequest(connection_pool_size=8, read_timeout=30, write_timeout=30, connect_timeout=30)
    application = Application.builder().token(TOKEN).request(request).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("plan", plan))
    application.add_handler(CommandHandler("add", add_task))
    application.add_handler(CommandHandler("habits", habits))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем бота с retry
    print("✅ Бот запущен! Ожидание сообщений...")
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        print("💡 Попробуй использовать VPN или прокси")

if __name__ == "__main__":
    main()