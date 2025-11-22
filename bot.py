from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters
import logging
from database import setup_db, get_user_status, add_new_payment, update_payment_status

# --- CONFIGURATION ---
TOKEN = "7328171287:AAEJfKeLnE746bT7pSWb1Nazw7MmpMc0NEY" 
ADMIN_ID = 6585361526  # Apna Telegram User ID Yahan Daalein
PREMIUM_CHANNEL_LINK = "https://t.me/JOIN_LINK_TO_YOUR_PREMIUM_CHANNEL"
PREMIUM_AMOUNT = "₹199" # Premium ka amount
QR_CODE_PATH = 'qr_code.jpg' # QR Code image file ka naam

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ----------------- User Functions -----------------

def start(update: Update, context):
    """Handles the /start command and shows the welcome message."""
    user = update.effective_user
    
    # Buy Premium button
    keyboard = [[
        InlineKeyboardButton("✨ Buy Premium", callback_data='buy_premium')
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_html(
        f"👋 **Welcome, {user.first_name}!**\n\n"
        "Unlock special content by becoming a premium member.",
        reply_markup=reply_markup
    )

def handle_callback_query(update: Update, context):
    """Handles button clicks."""
    query = update.callback_query
    query.answer()
    data = query.data
    user_id = query.from_user.id
    
    if data == 'buy_premium':
        # Send QR Code and payment instructions
        caption_text = (
            f"💰 **Payment Amount:** {PREMIUM_AMOUNT}\n\n"
            "1. Payment is QR code par karein.\n"
            "2. Payment hone ke baad, **screenshot** isi chat mein bhej dein.\n"
            "3. Admin check karne ke baad aapko access denge."
        )
        
        # 'Awaiting_Screenshot' state set karein
        context.user_data['state'] = 'awaiting_screenshot'
        context.bot.send_photo(
            chat_id=user_id,
            photo=open(QR_CODE_PATH, 'rb'),
            caption=caption_text
        )

def handle_screenshot(update: Update, context):
    """Handles the screenshot sent by the user."""
    user_id = update.effective_user.id
    
    # Check if user is in the 'awaiting_screenshot' state
    if context.user_data.get('state') == 'awaiting_screenshot' and update.message.photo:
        photo_file_id = update.message.photo[-1].file_id
        
        # Save payment details to DB
        payment_id = add_new_payment(user_id, PREMIUM_AMOUNT, photo_file_id)
        
        # Notify user
        update.message.reply_text(
            "✅ **Screenshot received!**\n"
            "Aapka payment approval ke liye admin ko bhej diya gaya hai. Kripya intezar karein."
        )
        
        # Reset state
        context.user_data['state'] = None
        
        # --- Notify Admin ---
        send_admin_approval(context.bot, payment_id, user_id, photo_file_id)

    elif update.message.photo:
        # Ignore random photos if not expecting screenshot
        pass
    
    else:
        # User is in awaiting state but sent text, prompt again
        if context.user_data.get('state') == 'awaiting_screenshot':
             update.message.reply_text("Kripya sirf payment ka **screenshot** bhejain.")


# ----------------- Admin Functions -----------------

def send_admin_approval(bot, payment_id, user_id, photo_file_id):
    """Sends the approval message with the screenshot to the admin."""
    
    keyboard = [[
        InlineKeyboardButton("✅ Confirm", callback_data=f'confirm_{payment_id}_{user_id}'),
        InlineKeyboardButton("❌ Reject", callback_data=f'reject_{payment_id}_{user_id}')
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    caption_text = (
        f"🚨 **NEW PAYMENT REQUEST**\n"
        f"• User ID: `{user_id}`\n"
        f"• Payment ID: `{payment_id}`\n"
        f"• Amount: {PREMIUM_AMOUNT}\n\n"
        "Kripya screenshot ki jaanch karein aur approve/reject karein."
    )

    bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo_file_id,
        caption=caption_text,
        reply_markup=reply_markup
    )

def handle_admin_approval(update: Update, context):
    """Handles Confirm/Reject clicks by the admin."""
    query = update.callback_query
    query.answer()
    
    # Data is like: 'confirm_123_456789'
    action, payment_id_str, user_id_str = query.data.split('_')
    payment_id = int(payment_id_str)
    user_id = int(user_id_str)
    
    # Check if the clicker is the Admin
    if query.from_user.id != ADMIN_ID:
        query.edit_message_caption(caption="🚫 Aapko yeh command istemal karne ki anumati nahi hai.", 
                                   reply_markup=None)
        return

    if action == 'confirm':
        # Update DB and notify user
        update_payment_status(payment_id, 'Confirmed', user_id)
        
        # Edit Admin message
        query.edit_message_caption(
            caption=f"✅ **CONFIRMED!** Payment ID `{payment_id}` approved.\n"
                    f"Access granted to user `{user_id}`.",
            reply_markup=None
        )
        
        # Send Premium Link to User
        context.bot.send_message(
            chat_id=user_id,
            text=f"🎉 **Congratulations! Your payment is confirmed.**\n"
                 f"Aapka Premium access ab shuru ho gaya hai. Yahan link hai: {PREMIUM_CHANNEL_LINK}"
        )

    elif action == 'reject':
        # Update DB and notify user
        update_payment_status(payment_id, 'Rejected')
        
        # Edit Admin message
        query.edit_message_caption(
            caption=f"❌ **REJECTED!** Payment ID `{payment_id}` rejected.\n"
                    f"User `{user_id}` ko reject message bheja gaya.",
            reply_markup=None
        )
        
        # Send Reject Message to User
        context.bot.send_message(
            chat_id=user_id,
            text="❌ **Payment Check Failed.**\n"
                 "Kripya dobara jaanch karein aur sahi payment screenshot bhejain, ya admin se sampark karein."
        )


def main():
    """Start the bot."""
    setup_db() # Database initialization
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(handle_callback_query, pattern='buy_premium'))
    dp.add_handler(CallbackQueryHandler(handle_admin_approval, pattern='(confirm|reject)_\d+_\d+'))
    # Handles photos sent by the user
    dp.add_handler(MessageHandler(Filters.photo & ~Filters.command, handle_screenshot))

    # Start the Bot
    updater.start_polling()
    print("Bot shuru ho gaya hai. Commands aur screenshots ka intezaar hai...")
    updater.idle()

if __name__ == '__main__':
    main()
