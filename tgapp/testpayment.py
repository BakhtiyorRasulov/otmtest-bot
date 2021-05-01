import logging

from telegram import LabeledPrice, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    PreCheckoutQueryHandler,
    CallbackContext,
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)



def paytest(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    title = "To'lov"
    description = "Test buyurtmasi uchun to'lov."
    payload = "Test-Payload"
    provider_token = "398062629:TEST:999999999_F91D8F69C042267444B74CC0B3C747757EB0E065"
    start_parameter = "test-payment"
    currency = "UZS"
    price = 10000
    prices = [LabeledPrice("Test", price * 100)]

    # optionally pass need_name=True, need_phone_number=True
    context.bot.send_invoice(
        chat_id, title, description, payload, provider_token, start_parameter, currency, prices
    )


def precheckout_callback(update: Update, _: CallbackContext) -> None:
    query = update.pre_checkout_query
    # check the payload, is this from your bot?
    if query.invoice_payload != 'Test-Payload':
        # answer False pre_checkout_query
        query.answer(ok=False, error_message="Xatolik yuz berdi.")
    else:
        query.answer(ok=True)


def successful_payment_callback(update: Update, _: CallbackContext) -> None:
    # do something after successfully receiving payment?
    update.message.reply_text("To'lov amalga oshirildi.")


def main() -> None:
    # Create the Updater and pass it your bot's token.
    updater = Updater("1743994187:AAHsH5qpEV-atIC-vBhi9aixB-zCnMWCAWQ")

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # simple start function
    dispatcher.add_handler(CommandHandler("start", start_callback))

    # Add command handler to start the payment invoice
    dispatcher.add_handler(CommandHandler("tulov", start_without_shipping_callback))

    # Optional handler if your product requires shipping

    # Pre-checkout handler to final check
    dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))

    # Success! Notify your user!
    dispatcher.add_handler(MessageHandler(Filters.successful_payment, successful_payment_callback))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()