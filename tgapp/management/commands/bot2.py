from django.core.management.base import BaseCommand  # , CommandError
import logging
import json
from tgapp.models import BotUsers, Subject
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, InlineKeyboardButton, \
    InlineKeyboardMarkup, LabeledPrice, Update, PreCheckoutQuery
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    PreCheckoutQueryHandler,
    CallbackContext,
)
# from pprint import pprint
import random

from tgapp.tools.result_check import getPoint
from tgapp.tools.find_res import getResult
from tgapp.tools.solidify_result import getSolid


# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

LANGUAGE, NAME, PHONE = range(3)
PERSON_INFO, CHANGE_NAME, CHANGE_PHONE = range(3)
CHANGE_LANGUAGE = range(1)

SELECT_SUBJECT, WAITING_FOR_ANSWERS = range(2)

with open('lang.json', encoding='utf-8') as json_file:
    string = json.load(json_file)

# Globals
random_num = 0
query = ''
sResult = ''
documents = []
# ----------------------------new user registrations------------------

def start(update: Update, _: CallbackContext) -> int:
    reply_keyboard = [[string['uz']['lang'], string['ru']['lang']]]
    update.message.reply_text(
        string['ru']['choose_language'] + "\n\r" + string['uz']['choose_language'] + "\n\r",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return LANGUAGE


def keyboard_generator(person):
    menu_keyboard = [[KeyboardButton(string[person.lang]['start_test']),
                      KeyboardButton(string[person.lang]['instructions'])],
                     [KeyboardButton(string[person.lang]['communication']),
                      KeyboardButton(string[person.lang]['change_language'])],
                     [KeyboardButton(string[person.lang]['personal_information'])],
                     ]
    return menu_keyboard


def language(update: Update, _: CallbackContext) -> int:
    user = update.message.from_user
    lang = "uz"
    if update.message.text == string['ru']['lang']:
        lang = "ru"
    if update.message.text == string['uz']['lang']:
        lang = "uz"
    logger.info("state: LANGUAGE, chat_id: %d, %s: %s ", update.message.chat_id, user.first_name, update.message.text)
    person, created = BotUsers.objects.update_or_create(
        chat_id=update.message.chat_id, defaults={"lang": lang}
    )
    person.save()
    update.message.reply_text(
        "{} {} {}".format(string[lang]['hello'], user.first_name, string[lang]['hello_massage']),
        reply_markup=ReplyKeyboardRemove(),
    )
    update.message.reply_text(
        string[lang]['name_input']
    )
    return NAME


def name(update: Update, _: CallbackContext) -> int:
    user = update.message.from_user
    logger.info("state: NAME, chat_id: %d, %s: %s ", update.message.chat_id, user.first_name, update.message.text)
    person, created = BotUsers.objects.update_or_create(
        chat_id=update.message.chat_id, defaults={"last_name": update.message.text}
    )
    person.save()
    reply_markup = ReplyKeyboardMarkup([[KeyboardButton(string[person.lang]['send_phone_number'],
                                                        request_contact=True)]],
                                       resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text(
        string[person.lang]['phone_input'], reply_markup=reply_markup
    )
    return PHONE


def phone(update: Update, _: CallbackContext) -> int:
    user = update.message.from_user
    if update.message.contact is not None:
        phone_number = update.message.contact.phone_number
        logger.info("state: PHONE, chat_id: %d, %s: %s ", update.message.chat_id, user.first_name,
                    update.message.contact.phone_number)
    else:
        phone_number = update.message.text
        logger.info("state: PHONE, chat_id: %d, %s: %s ", update.message.chat_id, user.first_name, update.message.text)

    person, created = BotUsers.objects.update_or_create(
        chat_id=update.message.chat_id, defaults={"phone_number": phone_number, "status": True}
    )
    person.save()
    main_menu_keyboard = keyboard_generator(person)
    reply_kb_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text(
        string[person.lang]['register_success'],
    )
    update.message.reply_text(
        string[person.lang]['select_section'],
        reply_markup=reply_kb_markup,
    )

    return ConversationHandler.END


def stop(update: Update, _: CallbackContext) -> int:
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    person = BotUsers.objects.update(status=False)
    update.message.reply_text(
        'Bye! I hope we can talk again some day.', reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


# ------------------------------------------------------------------

# ----------------------------edit user registrations------------------


def person_info_start(update: Update, _: CallbackContext) -> int:
    user = update.message.from_user
    logger.info("state: PERSON_INFO, chat_id: %d, %s: %s ", update.message.chat_id, user.first_name,
                update.message.text)

    person = BotUsers.objects.get(chat_id=update.message.chat_id)

    if person.status:
        status = "active"
    else:
        status = "passive"
    main_menu_keyboard = [[KeyboardButton(string[person.lang]['edit'])],
                          [KeyboardButton(string[person.lang]['back'])]]
    reply_kb_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True, one_time_keyboard=True)
    text = "{} {}\n\r{} {}\n\r{} {}".format(
        string[person.lang]['your_name'], person.last_name,
        string[person.lang]['your_phone'], person.phone_number,
        string[person.lang]['status'], status
    )

    update.message.reply_text(text, reply_markup=reply_kb_markup)

    return PERSON_INFO


def person_info(update: Update, _: CallbackContext) -> int:
    user = update.message.from_user
    logger.info("state: PERSON_INFO, chat_id: %d, %s: %s ", update.message.chat_id, user.first_name,
                update.message.text)

    person = BotUsers.objects.get(chat_id=update.message.chat_id)

    if update.message.text == string['uz']['edit'] or update.message.text == string['ru']['edit']:
        update.message.reply_text(
            string[person.lang]['name_input']
        )
        return CHANGE_NAME

    if update.message.text == string['uz']['back'] or update.message.text == string['ru']['back']:
        person = BotUsers.objects.get(chat_id=update.message.chat_id)
        main_menu_keyboard = keyboard_generator(person)
        reply_kb_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True, one_time_keyboard=True)
        update.message.reply_text(
            string[person.lang]['register_success'],
            reply_markup=reply_kb_markup,
        )
        return ConversationHandler.END


def change_name(update: Update, _: CallbackContext) -> int:
    user = update.message.from_user
    logger.info("state: CHANGE_NAME, chat_id: %d, %s: %s ", update.message.chat_id, user.first_name,
                update.message.text)
    person, created = BotUsers.objects.update_or_create(
        chat_id=update.message.chat_id, defaults={"last_name": update.message.text}
    )
    person.save()
    reply_markup = ReplyKeyboardMarkup(
        [[KeyboardButton(string[person.lang]['send_phone_number'], request_contact=True)]], resize_keyboard=True,
        one_time_keyboard=True)
    update.message.reply_text(
        string[person.lang]['phone_input'], reply_markup=reply_markup
    )
    return CHANGE_PHONE


def change_phone(update: Update, _: CallbackContext) -> int:
    user = update.message.from_user
    if update.message.contact is not None:
        phone_number = update.message.contact.phone_number
    else:
        phone_number = update.message.text

    logger.info("state: CHANGE_PHONE, %s: %s ", update.message.chat_id, user.first_name, phone_number)

    person, created = BotUsers.objects.update_or_create(
        chat_id=update.message.chat_id, defaults={"phone_number": phone_number, "status": True}
    )
    person.save()
    main_menu_keyboard = keyboard_generator(person)
    reply_kb_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text(
        string[person.lang]['select_section'],
        reply_markup=reply_kb_markup,
    )
    return ConversationHandler.END


# ------------------------------------------------------------------

# ----------------------------change language------------------


def change_language_start(update: Update, _: CallbackContext) -> int:
    reply_keyboard = [[string['uz']['lang'], string['ru']['lang']]]
    update.message.reply_text(
        string['ru']['choose_language'] + "\n\r" + string['uz']['choose_language'] + "\n\r",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return CHANGE_LANGUAGE


def change_language(update: Update, _: CallbackContext) -> int:
    user = update.message.from_user
    lang = "uz"
    if update.message.text == string['ru']['lang']:
        lang = "ru"
    if update.message.text == string['uz']['lang']:
        lang = "uz"
    logger.info("state: CHANGE_LANGUAGE, chat_id: %d, %s: %s ", update.message.chat_id, user.first_name,
                update.message.text)
    person, created = BotUsers.objects.update_or_create(
        chat_id=update.message.chat_id, defaults={"lang": lang}
    )
    person.save()
    main_menu_keyboard = keyboard_generator(person)
    reply_kb_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text(
        string[person.lang]['select_section'],
        reply_markup=reply_kb_markup,
    )
    return ConversationHandler.END


# ------------------------------------------------------------------


def echo(update: Update, _: CallbackContext) -> None:
    user = update.message.from_user
    person = BotUsers.objects.get(chat_id=update.message.chat_id)
    logger.info("state: ECHO, chat_id: %d, %s: %s ", update.message.chat_id, user.first_name, update.message.text)
    if update.message.text == string[person.lang]['back']:
        main_menu_keyboard = keyboard_generator(person)
        reply_kb_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True, one_time_keyboard=True)
        update.message.reply_text(
            string[person.lang]['back'],
            reply_markup=reply_kb_markup,
        )
        return ConversationHandler.END
    if update.message.text == string[person.lang]['instructions']:
        main_menu_keyboard = keyboard_generator(person)
        reply_kb_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True, one_time_keyboard=True)
        update.message.reply_text(
            string[person.lang]['instructions_msg'],
            reply_markup=reply_kb_markup,
        )
        return ConversationHandler.END
    if update.message.text == string[person.lang]['communication']:
        main_menu_keyboard = keyboard_generator(person)
        reply_kb_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True, one_time_keyboard=True)
        update.message.reply_text(
            string[person.lang]['communication_msg'],
            reply_markup=reply_kb_markup,
        )
        return ConversationHandler.END


def test_start(update: Update, _: CallbackContext) -> int:
    user = update.message.from_user
    logger.info("state: START_TEST, chat_id: %d, %s: %s ", update.message.chat_id, user.first_name, update.message.text)
    person = BotUsers.objects.get(chat_id=update.message.chat_id)

    main_menu_keyboard = [[KeyboardButton(string[person.lang]['back'])]]
    reply_kb_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text(
        string[person.lang]['start_test'],
        reply_markup=reply_kb_markup,
    )
    subject = Subject.objects.all()
    keyboard = []
    for s in subject:
        if person.lang == 'uz':
            keyboard.append([InlineKeyboardButton(s.name_uz, callback_data=s.name_uz)])
        if person.lang == 'ru':
            keyboard.append([InlineKeyboardButton(s.name_ru, callback_data=s.name_ru)])
        print(s)
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        string[person.lang]['start_test_msg'],
        reply_markup=reply_markup
    )

    return SELECT_SUBJECT


def select_subject(update: Update, _: CallbackContext) -> int:
    global query
    query = update.callback_query
    person = BotUsers.objects.get(chat_id=query.message.chat.id)
    query.answer()
    query.delete_message()
    user_answers = ""
    logger.info("state: SELECT_SUBJECT, chat_id: %d, %s: %s ", query.message.chat.id, query.message.chat.username,
                query.data)

    if person.lang == 'uz':
        subject = Subject.objects.get(name_uz=query.data)
    if person.lang == 'ru':
        subject = Subject.objects.get(name_ru=query.data)
    subject_files = subject.file.filter(language=str(person.lang))

    file_quantity = subject_files.count()
    if file_quantity > 0:
        global random_num
        if int(person.last_test_no)+1 >= file_quantity:
            person.last_test_no = '1'
            person.save()
        else:
            person.last_test_no = str(int(person.last_test_no)+1)
            person.save()
        random_num = int(person.last_test_no)
        random_file_url = subject.file.filter(language=str(person.lang))[random_num-1].upload
        print(random_file_url)
        document = open(str(random_file_url), 'rb')
        query.message.reply_document(document)
        query.message.reply_text(
            string[person.lang]['answer_msg']
        )
    else:
        main_menu_keyboard = [[KeyboardButton(string[person.lang]['back'])]]
        reply_kb_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True, one_time_keyboard=True)
        query.message.reply_text(
            string[person.lang]['file_not_found'],
            reply_markup=reply_kb_markup
        )
    user_answers += update.message.text
    user = update.message.from_user
    logger.info("state: WAITING_FOR_ANSWERS, chat_id: %d, %s: %s ", update.message.chat_id, user.first_name, update.message.text)
    update.message.reply_text(user_answers)

    return WAITING_FOR_ANSWERS


def waiting_for_answers(update: Update, context: CallbackContext) -> int:
    global random_num, query, sResult, documents
    person = BotUsers.objects.get(chat_id=query.message.chat.id)
    user = update.message.from_user
    logger.info("state: WAITING_FOR_ANSWERS, chat_id: %d, %s: %s ", update.message.chat_id, user.first_name, update.message.text)
    # find results
    if update.message.text != string[person.lang]['back']:
        fEarnedPoint, user_answers = getPoint(person.lang, query.data, random_num, user_answers)
        #sResult = getResult(fEarnedPoint, person.lang, 'kunduzgi', query.data)
        if len(sResult.splitlines()) != 0:
            update.message.reply_text(string[person.lang]['pass'].format(fEarnedPoint, len(sResult.splitlines())))

            chat_id = update.message.chat_id
            title = "To'lov"
            description = "Test buyurtmasi uchun to'lov."
            payload = "Test-Payload"
            provider_token = "398062629:TEST:999999999_F91D8F69C042267444B74CC0B3C747757EB0E065"
            start_parameter = "test-payment"
            currency = "UZS"
            price = 10000
            prices = [LabeledPrice("TestTulovi", price * 100)]
            context.bot.send_invoice(
                chat_id, title, description, payload, provider_token, start_parameter, currency, prices
            )
        else:
            update.message.reply_text(string[person.lang]['fail'].format(fEarnedPoint))
        update.message.reply_text(string[person.lang]['showPoint'].format(fEarnedPoint, getSolid(user_answers)))
    main_menu_keyboard = keyboard_generator(person)
    reply_kb_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text(
        string[person.lang]['back'],
        reply_markup=reply_kb_markup,
    )
    return ConversationHandler.END


def precheckout_callback(update: Update, _: CallbackContext) -> None:
    print("CHECKOUT")
    query = update.pre_checkout_query
    # check the payload, is this from your bot?
    if query.invoice_payload != 'Test-Payload':
        # answer False pre_checkout_query
        query.answer(ok=False, error_message="Xatolik yuz berdi.")
    else:
        query.answer(ok=True)
        #update.answer_pre_checkout_query(query.id, True, error_message="TIMEOUT 10sec", api_kwargs=None)

def answer_precheckout_callback(update: Update, _: CallbackContext) -> None:
    print("Answer")
    query = update.answer_pre_checkout_query
    query.answer(ok=True)


def successful_payment_callback(update: Update, _: CallbackContext) -> None:
    global sResult
    # do something after successfully receiving payment?
    update.message.reply_text("To'lov amalga oshirildi.")
    update.message.reply_text(sResult)


def main() -> None:
    updater = Updater("1743994187:AAHsH5qpEV-atIC-vBhi9aixB-zCnMWCAWQ")
    dispatcher = updater.dispatcher
    user_register_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LANGUAGE: [MessageHandler(Filters.regex('^({}|{})$'.format(string['uz']['lang'], string['ru']['lang'])),
                                      language)],
            NAME: [MessageHandler(Filters.text & ~Filters.command, name)],
            PHONE: [MessageHandler(Filters.text | Filters.contact & ~Filters.command, phone)],
        },
        fallbacks=[CommandHandler('stop', stop)],
    )

    user_info_conv_hendler = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex(
            '^({}|{})$'.format(string['uz']['personal_information'], string['ru']['personal_information'])),
                                     person_info_start)],
        states={
            PERSON_INFO: [MessageHandler(Filters.text & ~Filters.command, person_info)],
            CHANGE_NAME: [MessageHandler(Filters.text & ~Filters.command, change_name)],
            CHANGE_PHONE: [MessageHandler(Filters.text | Filters.contact & ~Filters.command, change_phone)],

        },
        fallbacks=[CommandHandler('stop', stop)],
    )

    change_language_conv_hendler = ConversationHandler(
        entry_points=[MessageHandler(
            Filters.regex('^({}|{})$'.format(string['uz']['change_language'], string['ru']['change_language'])),
            change_language_start)],
        states={
            CHANGE_LANGUAGE: [MessageHandler(Filters.text & ~Filters.command, change_language)],
        },
        fallbacks=[CommandHandler('stop', stop)],
    )
    test_start_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(Filters.regex('^({}|{})$'.format(string['uz']['start_test'], string['ru']['start_test'])),
                           test_start)],
        states={
            SELECT_SUBJECT: [CallbackQueryHandler(select_subject)],
            WAITING_FOR_ANSWERS: [MessageHandler(Filters.text & ~Filters.command, waiting_for_answers)],

        },
        fallbacks=[MessageHandler(Filters.regex('^({}|{})$'.format(string['uz']['back'], string['ru']['back'])), echo)],
    )
    dispatcher.add_handler(test_start_conv_handler)

    dispatcher.add_handler(change_language_conv_hendler)
    dispatcher.add_handler(user_register_conv_handler)
    dispatcher.add_handler(user_info_conv_hendler)
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
    dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    dispatcher.add_handler(PreCheckoutQueryHandler(answer_precheckout_callback))
    dispatcher.add_handler(MessageHandler(Filters.successful_payment, successful_payment_callback))

    updater.start_polling()

    updater.idle()


class Command(BaseCommand):
    help = 'tg bot'

    def handle(self, *args, **options):
        main()
