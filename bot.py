import os
import telebot
from dotenv import load_dotenv
import database
import llm_helper
import threading
from flask import Flask

# Load environment variables from .env file
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN not found. Please create a .env file and add your token.")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# Change this string and redeploy to notify all users!
CURRENT_VERSION = "1.1 - Debt Tracking"
NEW_FEATURE_MESSAGE = "🚀 *New Feature Deployed!*\n\nI can now track your debts! You can say things like:\n- '300 owed to aditya'\n- 'aditya owes me 500'\n- '300 to aditya cleared'\n\nI will keep track of who owes you (and who you owe) and remind you!"

# Initialize database and LLM
database.init_db()
try:
    llm_helper.init_llm()
    print("LLM initialized successfully.")
except Exception as e:
    print(f"Warning: {e}")

# Notify users of new features
try:
    last_announced = database.get_setting("last_announced_version")
    if last_announced != CURRENT_VERSION:
        users = database.get_all_users()
        for u in users:
            try:
                bot.send_message(u, NEW_FEATURE_MESSAGE, parse_mode='Markdown')
            except Exception as e:
                print(f"Could not send notification to {u}: {e}")
        database.set_setting("last_announced_version", CURRENT_VERSION)
        print(f"Notified users about version {CURRENT_VERSION}")
except Exception as e:
    print(f"Notification system error: {e}")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "Hello! I am your personal Expense Tracker and Finance Agent. 💰\n\n"
        "You can simply type your expenses like:\n"
        "- 'taxi 300'\n"
        "- 'lunch 500 UPI'\n"
        "- '300 owed to aditya'\n\n"
        "I will automatically categorize and save them!"
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    text = message.text
    
    bot.send_chat_action(message.chat.id, 'typing')
    parsed_data = llm_helper.parse_expense(text)
    
    reply = ""
    is_transaction = False
    
    if parsed_data:
        # Check if it's a debt interaction
        if parsed_data.get('is_debt') or parsed_data.get('is_debt_clear'):
            is_transaction = True
            amount = parsed_data.get('amount')
            person_name = parsed_data.get('person_name', 'unknown')
            debt_type = parsed_data.get('debt_type')
            
            if parsed_data.get('is_debt_clear'):
                database.clear_debt(user_id, person_name)
                reply = f"✅ Cleared debts with {person_name.title()}!"
            else:
                database.add_debt(user_id, amount, person_name, debt_type)
                direction = "You owe" if debt_type == "i_owe" else "Owed to you by"
                reply = f"📝 Debt Recorded: {direction} {person_name.title()} ({amount})"
                
        # Check if it's a standard expense
        elif parsed_data.get('is_expense') and parsed_data.get('amount') is not None:
            is_transaction = True
            amount = parsed_data.get('amount')
            category = parsed_data.get('category', 'other')
            payment_source = parsed_data.get('payment_source', 'unknown')
            description = parsed_data.get('description', text)
            
            database.add_expense(user_id, amount, category, payment_source, description)
            monthly_total = database.get_monthly_total(user_id)
            
            reply = (
                f"✅ Recorded!\n"
                f"Amount: {amount}\n"
                f"Category: {category.capitalize()}\n"
                f"Payment Source: {payment_source}\n\n"
                f"📊 Total spent this month: {monthly_total}"
            )
        else:
            # It's a conversation or advice request
            monthly_total = database.get_monthly_total(user_id)
            recent_expenses = database.get_recent_expenses(user_id)
            reply = llm_helper.get_finance_advice(user_id, text, monthly_total, recent_expenses)
            bot.reply_to(message, reply)
            return

    # If it was an expense or debt, append the reminder to the reply
    if is_transaction:
        uncleared = database.get_uncleared_debts(user_id)
        if uncleared:
            reply += "\n\n🔔 Reminders:"
            for d in uncleared:
                amt, person, dtype = d
                if dtype == "i_owe":
                    reply += f"\n- You owe {person.title()}: {amt}"
                else:
                    reply += f"\n- {person.title()} owes you: {amt}"
                    
        bot.reply_to(message, reply)

# --- FLASK SERVER (TO KEEP RENDER HAPPY) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    print("Starting Flask server...")
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    print("Bot is starting up...")
    bot.infinity_polling()
