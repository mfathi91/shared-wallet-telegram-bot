import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from configuration import Configuration
from database import Database
from payment import Payment

# Ensure the env variable is present
version_env = os.environ.get('VERSION', None)
volumes_dir_env = os.environ.get('VOLUMES_DIRECTORY', None)
if not version_env:
    raise RuntimeError('VERSION not defined as an environment variable')
if not volumes_dir_env:
    raise RuntimeError('VOLUMES_DIRECTORY not defined as an environment variable')
volumes_dir = Path(volumes_dir_env)

# Enable logging
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
file_handler = logging.FileHandler(Path.joinpath(volumes_dir, 'log.txt'))
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        console_handler,
        file_handler
    ]
)

# Create and initialize the configuration
config = Configuration(str(Path(volumes_dir, 'config.json')), logging)

# Create and initialize the database
database = Database(config, str(Path(volumes_dir, 'db.sq3')))

# Build the application
logging.info(f'Detected version: {version_env}')
application = Application.builder().token(config.get_token()).build()

# State of the conversations
WALLET, PAYER, NOTE, AMOUNT, CONFIRM = range(5)
WALLET_BALANCE = 5


# ------------------- update conversation functions -------------------
async def update_choose_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logging.info("User %s issued /update command", update.message.from_user.first_name)
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
    reply_keyboard = [config.get_usernames()]
    await update.message.reply_text(
        'Whose balance to increase?',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True
        ),
    )
    return PAYER


async def update_enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.chat_data['payer'] = update.message.text
    await update.message.reply_text(
        'Ok.\n'
        f'How many {context.chat_data["wallet"]}s?',
        reply_markup=ReplyKeyboardRemove(),
    )
    return AMOUNT


async def update_enter_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.chat_data['amount'] = update.message.text
    await update.message.reply_text(
        'Ok.\n'
        'Do you have a note for this payment? If not, enter /skip .',
        reply_markup=ReplyKeyboardRemove(),
    )
    return NOTE


async def update_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    note_input = update.message.text
    context.chat_data['note'] = '-' if note_input == '/skip' else note_input

    cd = context.chat_data
    payment = Payment(cd['payer'], cd['amount'], cd['wallet'], config.get_wallet_symbol(cd['wallet']), cd['note'])
    cd['payment'] = payment
    reply_keyboard = [['Yes', 'No']]
    await update.message.reply_text(
        'Do you confirm the following payment?\n'
        f'{payment.format()}',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Yes or No'
        ),
    )
    return CONFIRM


async def update_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == 'Yes':
        payment = context.chat_data['payment']
        logging.info('User %s finalized /update command. Parameters: %s', update.message.from_user.first_name, payment.jsonify())
        database.write_transaction(payment)
        await update.message.reply_text(
            get_formatted_balance(payment.wallet),
            reply_markup=ReplyKeyboardRemove(),
        )

        # Inform the other user about the payment
        other = config.get_other_chat_id(update.message.chat_id)
        msg = f'{payment.format()}\n' \
              f'New status:\n' \
              f'{get_formatted_balance(payment.wallet)}'
        await application.bot.send_message(
            chat_id=other,
            text=msg
        )
    else:
        await update.message.reply_text(
            'Ok, the process is canceled.',
            reply_markup=ReplyKeyboardRemove(),
        )
    return ConversationHandler.END


# ------------------ status conversation --------------------
async def status_choose_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logging.info("User %s issued /status command", update.message.from_user.first_name)
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


# ------------------ last 3 command --------------------
async def last_3_payments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logging.info("User %s issued /last3 command", update.message.from_user.first_name)
    payments = database.get_payments()[-3:]
    if payments:
        msg = '\n'.join(format_payment(payer=p[0], amount=p[1], wallet=p[2], note=p[3], date=p[4]) for p in payments)
    else:
        msg = 'No payments registered'
    await update.message.reply_text(text=msg)
    return ConversationHandler.END


# ------------------ history command --------------------
async def history_payments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logging.info("User %s issued /history command", update.message.from_user.first_name)
    history_json = f'/tmp/{datetime.now()}.json'
    with open(history_json, 'w') as f:
        f.write(jsonify_payments(database.get_payments()))
    await update.message.reply_document(
        document=history_json,
        filename=f'history.json'
    )
    return ConversationHandler.END


# ------------------ about command --------------------
async def about_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logging.info("User %s issued /about command", update.message.from_user.first_name)
    await update.message.reply_text(text=f'Shared wallet Telegram Bot v{version_env}')
    return ConversationHandler.END


# ----------- cancel current operation for all the conversations -------------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logging.info("User %s issued /cancel command", update.message.from_user.first_name)
    context.chat_data.clear()
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
            creditor = record[1]
            debtor = config.get_other_username(creditor)
            symbol = config.get_wallet_symbol(wallet)
            return f'{creditor}: {amount} {symbol}\n{debtor}: 0 {symbol}'
    return '0'


def jsonify_payments(payments: List[Tuple]) -> str:
    result = {'payments': []}
    for payment in payments:
        wallet = payment[2]
        record = {'payer': payment[0], 'amount': f'{payment[1]} {config.get_wallet_symbol(wallet)}', 'wallet': wallet, 'note': payment[3], 'datetime': payment[4]}
        result['payments'].append(record)
    return json.dumps(result, indent=4)


def format_payment(payer: str, amount: str, wallet: str, note: str, date: str = None) -> str:
    f = f'Payer: {payer}\n' \
        f'Amount: {amount} {config.get_wallet_symbol(wallet)}\n' \
        f'Wallet: {wallet}\n' \
        f'Note: {note}\n'
    if date:
        f += f'Date: {date}\n'
    return f


# -------------------------------------------------
def main():
    # Add conversation handler for changing a wallet
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('update', update_choose_wallet, filters.User(config.get_chat_ids()))],
        states={
            WALLET: [MessageHandler(filters.Regex(f'^({"|".join(config.get_currencies())})$'), update_choose_payer)],
            PAYER: [MessageHandler(filters.Regex(f'^({"|".join(config.get_usernames())})$'), update_enter_amount)],
            AMOUNT: [MessageHandler(filters.Regex('^[0-9]+(.[0-9]{2})?$') & ~filters.COMMAND, update_enter_note)],
            NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_confirm), CommandHandler('skip', update_confirm)],
            CONFIRM: [MessageHandler(filters.Regex('^(Yes|No)$'), update_end)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    application.add_handler(conv_handler)

    # Add conversation handler for getting wallet status
    wallet_status_handler = ConversationHandler(
        entry_points=[CommandHandler('status', status_choose_wallet, filters.User(config.get_chat_ids()))],
        states={
            WALLET_BALANCE: [MessageHandler(filters.Regex(f'^({"|".join(config.get_currencies())})$'), status_end)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    application.add_handler(wallet_status_handler)

    # Add command handler to get the last three payments (regardless of the wallets)
    application.add_handler(CommandHandler('last3', last_3_payments, filters.User(config.get_chat_ids())))

    # Add command handler to get the full history of the payments
    application.add_handler(CommandHandler('history', history_payments, filters.User(config.get_chat_ids())))

    # Add command handler to get general information about the bot
    application.add_handler(CommandHandler('about', about_handler, filters.User(config.get_chat_ids())))

    # Start the Bot
    application.run_polling()


if __name__ == '__main__':
    main()
