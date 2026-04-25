import os
import telebot
from dotenv import load_dotenv
import database
import llm_helper

# Load environment variables from .env file
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN not found. Please create a .env file and add your token.")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# Initialize database and LLM
database.init_db()
try:
    llm_helper.init_llm()
    print("LLM initialized successfully.")
except Exception as e:
    print(f"Warning: {e}")
    print("Please make sure you have added GEMINI_API_KEY to your .env file.")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "Hello! I am your personal Expense Tracker and Finance Agent. 💰\n\n"
        "You can simply type your expenses like:\n"
        "- 'taxi 300'\n"
        "- 'lunch 500 UPI'\n"
        "- 'bought groceries for 1200 using Credit Card'\n\n"
        "I will automatically categorize and save them. I'll also let you know your total spend for the month!\n\n"
        "You can also ask me for budgeting advice or to analyze your spending."
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    text = message.text
    
    # Show "typing..." action in the chat
    bot.send_chat_action(message.chat.id, 'typing')
    
    # Try to parse the text as an expense using Gemini
    parsed_data = llm_helper.parse_expense(text)
    
    if parsed_data and parsed_data.get('is_expense') and parsed_data.get('amount') is not None:
        amount = parsed_data['amount']
        category = parsed_data.get('category', 'other')
        payment_source = parsed_data.get('payment_source', 'unknown')
        description = parsed_data.get('description', text)
        
        # Save to database
        database.add_expense(user_id, amount, category, payment_source, description)
        
        # Get updated monthly total
        monthly_total = database.get_monthly_total(user_id)
        
        reply = (
            f"✅ Recorded!\n"
            f"Amount: {amount}\n"
            f"Category: {category.capitalize()}\n"
            f"Payment Source: {payment_source}\n\n"
            f"📊 Total spent this month: {monthly_total}"
        )
        bot.reply_to(message, reply)
    else:
        # Not recognized as a straightforward expense, might be a question or chat
        monthly_total = database.get_monthly_total(user_id)
        recent_expenses = database.get_recent_expenses(user_id)
        
        advice = llm_helper.get_finance_advice(user_id, text, monthly_total, recent_expenses)
        bot.reply_to(message, advice)

if __name__ == "__main__":
    print("Bot is starting up...")
    bot.infinity_polling()
