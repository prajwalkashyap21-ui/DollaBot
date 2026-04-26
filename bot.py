import os
import telebot
from dotenv import load_dotenv
import database
import llm_helper
import threading
from flask import Flask
from datetime import datetime, timedelta

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

CURRENT_VERSION = "1.3 - Custom Recurring Dates"
NEW_FEATURE_MESSAGE = "🚀 *New Feature Deployed!*\n\nYou can now specify the exact date for your recurring expenses! Example:\n- _\"Set up Netflix for 500 every month on the 15th\"_\n- _\"Change my rent date to the 5th\"_"

database.init_db()
llm_helper.init_llm()

# Notify users of new features
try:
    last_announced = database.get_setting("last_announced_version")
    if last_announced != CURRENT_VERSION:
        users = database.get_all_users()
        for u in users:
            try:
                bot.send_message(u, NEW_FEATURE_MESSAGE, parse_mode='Markdown')
            except Exception as e:
                pass
        database.set_setting("last_announced_version", CURRENT_VERSION)
except Exception as e:
    pass

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = """👋 *Welcome to your AI Finance Manager!*

I understand natural language, so you can just text me like a real person!

🌟 *Here is what I can do for you:*

*1️⃣ Track Expenses*
- _"taxi 300"_
- _"bought lunch for 500 using UPI"_

*2️⃣ Manage Debts & IOUs*
- _"300 owed to aditya"_
- _"aditya owes me 500"_
- _"300 to aditya cleared"_

*3️⃣ Subscriptions & Recurring*
- _"Gemini subscription 2000 autopay"_
- _"Set up Netflix for 500 every month on the 15th"_
- _"Rent paid"_

*4️⃣ Financial Advice*
- _"How much have I spent this month?"_
- _"What subscriptions do I have?"_
- _"What recurring expenses are unpaid?"_

Just send your first expense to get started! 🚀"""
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    text = message.text
    
    bot.send_chat_action(message.chat.id, 'typing')
    parsed_data = llm_helper.parse_expense(text)
    
    if not parsed_data:
        bot.reply_to(message, "I'm sorry, I had a little trouble understanding that. Could you try rephrasing it?")
        return
        
    if "error" in parsed_data:
        bot.reply_to(message, f"🛠 *System Error:*\n`{parsed_data['error']}`", parse_mode="Markdown")
        return
        
    reply = ""
    is_transaction = False
    
    # Check Recurring
    if parsed_data.get('is_recurring_setup') or parsed_data.get('is_recurring_update') or parsed_data.get('is_recurring_payment'):
        is_transaction = True
        amount = parsed_data.get('amount')
        payee = parsed_data.get('payee', 'unknown')
        
        if parsed_data.get('is_recurring_setup'):
            category = parsed_data.get('category', 'recurring')
            description = parsed_data.get('description', text)
            is_autopay = parsed_data.get('is_autopay', False)
            day_of_month = parsed_data.get('day_of_month') or datetime.now().day
            database.add_recurring(user_id, amount, category, payee, description, is_autopay, day_of_month)
            reply = f"🔄 Setup Recurring: {payee.title()} ({amount}) on the {day_of_month}th of every month.\nAutopay: {'Yes' if is_autopay else 'No'}"
            
        elif parsed_data.get('is_recurring_update'):
            day_of_month = parsed_data.get('day_of_month')
            payee = parsed_data.get('payee')
            
            update_msg = []
            if payee and payee.lower() != "unknown" and payee.lower() != "bill":
                if amount:
                    database.update_recurring_amount(user_id, payee, amount)
                    update_msg.append(f"amount to {amount}")
                if day_of_month:
                    database.update_recurring_date(user_id, payee, day_of_month)
                    update_msg.append(f"date to the {day_of_month}th")
            elif amount: # update by amount if payee is not provided
                if day_of_month:
                    database.update_recurring_date_by_amount(user_id, amount, day_of_month)
                    update_msg.append(f"date to the {day_of_month}th for the {amount} bill")
            
            reply = f"🔄 Updated recurring payment: {' and '.join(update_msg)}."
            
        elif parsed_data.get('is_recurring_payment'):
            current_month = datetime.now().strftime("%Y-%m")
            database.mark_recurring_paid(user_id, payee, current_month)
            if amount:
                database.add_expense(user_id, amount, 'recurring', 'unknown', f"Paid {payee}")
            reply = f"✅ Marked {payee.title()} as paid for this month!"

    # Check Debt
    elif parsed_data.get('is_debt') or parsed_data.get('is_debt_clear'):
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
            
    # Check Expense Delete
    elif parsed_data.get('is_expense_delete'):
        is_transaction = True
        amount = parsed_data.get('amount')
        database.delete_recent_expense(user_id, amount)
        monthly_total = database.get_monthly_total(user_id)
        if amount:
            reply = f"🗑 Deleted! Removed your most recent expense of {amount}.\n📊 New monthly total: {monthly_total}"
        else:
            reply = f"🗑 Deleted! Removed your most recent expense.\n📊 New monthly total: {monthly_total}"

    # Check Expense Update
    elif parsed_data.get('is_expense_update'):
        is_transaction = True
        amount = parsed_data.get('amount')
        expense_date_str = parsed_data.get('expense_date')
        if amount and expense_date_str:
            try:
                new_date = datetime.strptime(expense_date_str, "%Y-%m-%d")
                database.update_recent_expense_date(user_id, amount, new_date)
                reply = f"📅 Updated the date of your {amount} expense to {expense_date_str}."
            except:
                reply = "❌ Could not understand the new date format."
        else:
            reply = "❌ Please specify the exact amount of the expense you want to update, and the new date."

    # Check Standard Expense
    elif parsed_data.get('is_expense') and parsed_data.get('amount') is not None:
        is_transaction = True
        amount = parsed_data.get('amount')
        category = parsed_data.get('category', 'other')
        payment_source = parsed_data.get('payment_source', 'unknown')
        description = parsed_data.get('description', text)
        
        expense_date_str = parsed_data.get('expense_date')
        expense_date = None
        if expense_date_str:
            try:
                expense_date = datetime.strptime(expense_date_str, "%Y-%m-%d")
            except:
                pass
        
        database.add_expense(user_id, amount, category, payment_source, description, expense_date)
        monthly_total = database.get_monthly_total(user_id)
        reply = f"✅ Recorded!\nAmount: {amount}\nCategory: {category.capitalize()}\n📊 Total spent this month: {monthly_total}"
    else:
        # Advice / List queries
        monthly_total = database.get_monthly_total(user_id)
        recent_expenses = database.get_recent_expenses(user_id)
        recurring_expenses = database.get_all_recurring(user_id)
        reply = llm_helper.get_finance_advice(user_id, text, monthly_total, recent_expenses, recurring_expenses)
        bot.reply_to(message, reply)
        return

    # Append reminders
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

# --- FLASK SERVER & CRON ---
app = Flask(__name__)

def check_reminders():
    today_str = datetime.now().strftime("%Y-%m-%d")
    current_month = datetime.now().strftime("%Y-%m")
    last_run = database.get_setting("last_cron_date")
    
    if last_run != today_str:
        users = database.get_all_users()
        for u in users:
            recurrings = database.get_all_recurring(u)
            for r in recurrings:
                r_id, amount, cat, payee, desc, is_autopay, dom, last_paid, last_notif = r
                
                if is_autopay:
                    target_date = datetime.now() + timedelta(days=2)
                    if target_date.day == dom and last_notif != current_month:
                        bot.send_message(u, f"🔔 *Autopay Notice:*\nYour subscription to {payee.title()} ({amount}) will be auto-debited in 2 days!", parse_mode='Markdown')
                        database.mark_recurring_notified(r_id, current_month)
                else:
                    if datetime.now().day >= dom and last_paid != current_month and last_notif != current_month:
                        bot.send_message(u, f"🔔 *Reminder:*\nYour recurring payment for {payee.title()} ({amount}) is due!\n_Reply with '{payee} paid' once you pay it._", parse_mode='Markdown')
                        database.mark_recurring_notified(r_id, current_month)
                        
        database.set_setting("last_cron_date", today_str)

@app.route('/')
def home():
    check_reminders()
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    bot.infinity_polling()
