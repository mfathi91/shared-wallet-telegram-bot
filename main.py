import json
import logging
from datetime import datetime

from configuration import Configuration
from database import Database
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# Enable logging
log_file = open('log.txt', 'a+')
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file.name),
        logging.StreamHandler()
    ]
)

# Create and initialize the configuration
config = Configuration('config.json', logging)

# Create and initialize the database
database = Database(config, 'db.sql3')

WALLET, SENDER, NOTE, AMOUNT, CONFIRM = range(5)
WALLET_BALANCE = 5
HISTORY_END = 6


# ------------------- update conversation functions -------------------
async def update_choose_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [config.get_currencies()]
    await update.message.reply_text(
        'Which wallet do you want to change?',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True
        ),
    )
    return WALLET


async def update_choose_payer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.chat_data['wallet'] = update.message.text
    reply_keyboard = [config.get_user_names()]
    await update.message.reply_text(
        'Who did the payment?',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True
        ),
    )
    return SENDER


async def update_enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.chat_data['sender'] = update.message.text
    logging.info("Sender is: %s", update.message.text)
    await update.message.reply_text(
        'Ok.\n'
        f'How many {context.chat_data["wallet"]}s?',
        reply_markup=ReplyKeyboardRemove(),
    )
    return AMOUNT


async def update_enter_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.chat_data['amount'] = update.message.text
    logging.info("Amount is: %s", update.message.text)
    await update.message.reply_text(
        'Ok.\n'
        'Do you have a note for this payment? If not, enter /skip .',
        reply_markup=ReplyKeyboardRemove(),
    )
    return NOTE


async def update_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    note_input = update.message.text
    context.chat_data['note'] = '-' if note_input == '/skip' else note_input

    payment_wallet = context.chat_data['wallet']
    payment_sender = context.chat_data['sender']
    payment_note = context.chat_data['note']
    payment_amount = context.chat_data['amount']
    reply_keyboard = [['Yes', 'No']]
    await update.message.reply_text(
        'Do you confirm the following payment?\n'
        f'Wallet: {payment_wallet}\n'
        f'Payer: {payment_sender}\n'
        f'Note: {payment_note}\n'
        f'Amount: {payment_amount}',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Yes or No'
        ),
    )
    return CONFIRM


async def update_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == 'Yes':
        wallet = context.chat_data['wallet']
        database.write_transaction(context.chat_data['sender'], float(context.chat_data['amount']), wallet, context.chat_data['note'])
        await update.message.reply_text(
            get_formatted_balance(wallet),
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        await update.message.reply_text(
            'Ok, the process is canceled.',
            reply_markup=ReplyKeyboardRemove(),
        )
    return ConversationHandler.END


# ------------------ status conversation --------------------
async def status_choose_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [config.get_currencies()]
    await update.message.reply_text(
        'Which wallet do you want to see?',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True
        ),
    )
    return WALLET_BALANCE


async def status_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    wallet = update.message.text
    await update.message.reply_text(
        get_formatted_balance(wallet),
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


# ------------------ status conversation --------------------
async def history_choose_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [config.get_currencies()]
    await update.message.reply_text(
        'For which wallet do you want to create a report?',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True
        ),
    )
    return HISTORY_END


async def history_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    wallet = update.message.text
    p = f'/tmp/{datetime.now()}.json'
    with open(p, 'w') as f:
        f.write(get_formatted_wallet_history(wallet))
    await update.message.reply_document(
        p,
        filename=f'{wallet}_wallet_history.json'
    )
    return ConversationHandler.END


# ----------- cancel current operation for all the conversations -------------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.chat_data.clear()
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logging.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(
        'Ok, the process is canceled.', reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


# --------------------- Utility methods -----------------------
def get_formatted_balance(wallet: str) -> str:
    record = database.get_balance(wallet)
    if record:
        amount = record[0]
        if amount != '0':
            creditor_user = record[1]
            other_user = config.get_username1() if creditor_user == config.get_username2() else config.get_username2()
            symbol = config.get_symbol(wallet)
            return f'{creditor_user}: {amount} {symbol}\n{other_user}: 0 {symbol}'
    return '0'


def get_formatted_wallet_history(wallet: str) -> str:
    result = {'payments': []}
    payments = database.get_payments(wallet)
    for payment in payments:
        record = {'payer': payment[0], 'amount': payment[1], 'note': payment[2], 'datetime': payment[3]}
        result['payments'].append(record)
    return json.dumps(result, sort_keys=True, indent=4)


# -------------------------------------------------
def main():
    application = Application.builder().token(config.get_token()).build()

    # Add conversation handler for changing a wallet
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('update', update_choose_wallet, filters.User(config.get_user_chat_ids()))],
        states={
            WALLET: [MessageHandler(filters.Regex(f'^({"|".join(config.get_currencies())})$'), update_choose_payer)],
            SENDER: [MessageHandler(filters.Regex(f'^({config.get_username1()}|{config.get_username2()})$'), update_enter_amount)],
            AMOUNT: [MessageHandler(filters.Regex('^[0-9]+(.[0-9]{2})?$') & ~filters.COMMAND, update_enter_note)],
            NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_confirm), CommandHandler('skip', update_confirm)],
            CONFIRM: [MessageHandler(filters.Regex('^(Yes|No)$'), update_end)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    application.add_handler(conv_handler)

    # Add conversation handler for getting wallet status
    wallet_status_handler = ConversationHandler(
        entry_points=[CommandHandler('status', status_choose_wallet, filters.User(config.get_user_chat_ids()))],
        states={
            WALLET_BALANCE: [MessageHandler(filters.Regex(f'^({"|".join(config.get_currencies())})$'), status_end)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    application.add_handler(wallet_status_handler)

    # Add conversation handler to get a report for all the payments of a wallet
    wallet_history_handler = ConversationHandler(
        entry_points=[CommandHandler('history', history_choose_wallet, filters.User(config.get_user_chat_ids()))],
        states={
            HISTORY_END: [MessageHandler(filters.Regex(f'^({"|".join(config.get_currencies())})$'), history_end)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    application.add_handler(wallet_history_handler)

    # Start the Bot
    application.run_polling()


if __name__ == '__main__':
    main()
