import json
import logging
from dataclasses import dataclass
from enum import Enum, auto

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections
from telebot import TeleBot, types, util

from tgapp.models import BotUsers, Subject
from tgapp.tools.find_res import getResult
from tgapp.tools.result_check import getPoint
from tgapp.tools.solidify_result import getSolid


logger = logging.getLogger(__name__)


class Stage(Enum):
    NAME = auto()
    PHONE = auto()
    PROFILE = auto()
    EDIT_NAME = auto()
    EDIT_PHONE = auto()
    LANGUAGE = auto()
    SUBJECT = auto()
    FIRST_ANSWERS = auto()
    SECOND_ANSWERS = auto()
    CONFIRM = auto()


@dataclass
class Session:
    stage: Stage
    subject_name: str = ""
    language: str = ""
    test_number: int = 0
    answers: str = ""
    subject_message_id: int | None = None


def keyboard(*rows):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for row in rows:
        markup.row(*row)
    return markup


def parse_answers(text, count):
    tokens = text.split(" ")
    return "".join(token[-1:] or "-" for token in tokens[:count]).ljust(count, "-")


class ExamBot:
    def __init__(self, client):
        self.client = client
        self.strings = json.loads((settings.BASE_DIR / "lang.json").read_text(encoding="utf-8"))
        self.sessions = {}
        client.register_message_handler(
            self.handle_message, content_types=["text", "contact"], chat_types=["private"]
        )
        client.register_callback_query_handler(self.handle_subject, func=lambda query: True)

    def send(self, chat_id, text, markup=None):
        parts = [part for part in util.smart_split(text) if part]
        for part in parts[:-1]:
            self.client.send_message(chat_id, part)
        return self.client.send_message(chat_id, parts[-1], reply_markup=markup)

    def menu(self, person, labels, message="select_section"):
        self.send(person.chat_id, labels[message], keyboard(
            (labels["start_test"], labels["instructions"]),
            (labels["communication"], labels["personal_information"]),
            (labels["change_language"],),
        ))

    def ask_phone(self, chat_id, labels):
        self.send(chat_id, labels["phone_input"], keyboard(
            (types.KeyboardButton(labels["send_phone_number"], request_contact=True),),
        ))

    def handle_message(self, message):
        close_old_connections()
        chat_id = message.chat.id
        command = (message.text or "").split(maxsplit=1)
        command = command[0].split("@", 1)[0] if command else ""
        if command == "/stop":
            BotUsers.objects.filter(chat_id=chat_id).update(status=False)
            self.sessions.pop(chat_id, None)
            self.send(chat_id, "STOP", types.ReplyKeyboardRemove())
            return
        if command == "/start":
            self.sessions.pop(chat_id, None)
            person, _ = BotUsers.objects.get_or_create(chat_id=chat_id, defaults={"lang": "uz"})
            labels = self.strings.get(person.lang, self.strings["uz"])
            self.send(chat_id, f"{labels['hello']} {message.from_user.first_name} {labels['hello_massage']}",
                      types.ReplyKeyboardRemove())
            self.send(chat_id, labels["name_input"])
            self.sessions[chat_id] = Session(Stage.NAME)
            return
        if command.startswith("/"):
            return

        person = BotUsers.objects.filter(chat_id=chat_id).first()
        if person is None:
            return
        session = self.sessions.get(chat_id)
        if not person.status and (session is None or session.stage not in {Stage.NAME, Stage.PHONE}):
            return

        labels = self.strings.get(person.lang, self.strings["uz"])
        if message.text == labels["back"] and session and session.stage not in {Stage.NAME, Stage.PHONE}:
            self.sessions.pop(chat_id, None)
            self.menu(person, labels, "backto")
        elif session:
            self.handle_session(person, labels, session, message)
        elif message.text is not None:
            self.handle_menu(person, labels, message.text)

    def handle_menu(self, person, labels, text):
        chat_id = person.chat_id
        if text == labels["start_test"]:
            markup = types.InlineKeyboardMarkup()
            for subject in Subject.objects.order_by("pk"):
                name = subject.name_ru if person.lang == "ru" else subject.name_uz
                if name:
                    markup.add(types.InlineKeyboardButton(name, callback_data=f"subject:{subject.pk}"))
            if not markup.keyboard:
                self.send(chat_id, labels["file_not_found"])
                return
            self.send(chat_id, labels["start_test"], keyboard((labels["back"],)))
            sent = self.send(chat_id, labels["start_test_msg"], markup)
            self.sessions[chat_id] = Session(Stage.SUBJECT, subject_message_id=sent.message_id)
        elif text == labels["personal_information"]:
            self.send(chat_id, f"{labels['your_name']} {person.last_name}\n"
                      f"{labels['your_phone']} {person.phone_number}\nid: {chat_id}",
                      keyboard((labels["edit"],), (labels["back"],)))
            self.sessions[chat_id] = Session(Stage.PROFILE)
        elif text == labels["change_language"]:
            self.send(chat_id, f"{self.strings['ru']['choose_language']}\n{self.strings['uz']['choose_language']}",
                      keyboard(tuple(labels["lang"] for labels in self.strings.values())))
            self.sessions[chat_id] = Session(Stage.LANGUAGE)
        elif text == labels["instructions"]:
            self.menu(person, labels, "instructions_preview")
        elif text == labels["communication"]:
            self.menu(person, labels, "communication_msg")
        elif text == labels["back"]:
            self.menu(person, labels, "backto")

    def handle_session(self, person, labels, session, message):
        chat_id = person.chat_id
        text = message.text
        match session.stage:
            case Stage.NAME | Stage.EDIT_NAME if text is not None:
                if not text.strip() or len(text) > BotUsers._meta.get_field("last_name").max_length:
                    self.send(chat_id, labels["name_input"])
                    return
                person.last_name = text
                person.save(update_fields=["last_name"])
                self.ask_phone(chat_id, labels)
                session.stage = Stage.PHONE if session.stage == Stage.NAME else Stage.EDIT_PHONE
            case Stage.PHONE | Stage.EDIT_PHONE:
                phone = message.contact.phone_number if message.contact else text
                if not phone or not phone.strip() or len(phone) > BotUsers._meta.get_field("phone_number").max_length:
                    self.ask_phone(chat_id, labels)
                    return
                person.phone_number = phone
                person.status = True
                person.save(update_fields=["phone_number", "status"])
                self.sessions.pop(chat_id, None)
                if session.stage == Stage.PHONE:
                    self.send(chat_id, labels["register_success"])
                self.menu(person, labels)
            case Stage.PROFILE if text == labels["edit"]:
                self.send(chat_id, labels["name_input"], keyboard((labels["back"],)))
                session.stage = Stage.EDIT_NAME
            case Stage.LANGUAGE:
                for lang, translations in self.strings.items():
                    if text == translations["lang"]:
                        person.lang = lang
                        person.save(update_fields=["lang"])
                        self.sessions.pop(chat_id, None)
                        self.menu(person, translations)
                        break
            case Stage.FIRST_ANSWERS if text is not None:
                self.send(chat_id, labels["enter_second"])
                session.answers = parse_answers(text, 45)
                session.stage = Stage.SECOND_ANSWERS
            case Stage.SECOND_ANSWERS if text is not None:
                answers = session.answers + parse_answers(text, 60)
                rows = ["".join(f"{index + 1:>3}. {answers[index]:3}"
                                for index in range(row, 105, 21)) for row in range(21)]
                self.send(chat_id, "\n".join(rows) + "\n" + labels["confirm"],
                          keyboard((labels["yes"], labels["no"]), (labels["back"],)))
                session.answers = answers
                session.stage = Stage.CONFIRM
            case Stage.CONFIRM if text == labels["no"]:
                self.send(chat_id, labels["reenter"] + "\n" + labels["enter_first"])
                session.answers = ""
                session.stage = Stage.FIRST_ANSWERS
            case Stage.CONFIRM if text == labels["yes"]:
                self.show_results(person, labels, session)

    def handle_subject(self, query):
        close_old_connections()
        self.client.answer_callback_query(query.id)
        message = query.message
        if not message or message.chat.type != "private" or message.chat.id != query.from_user.id:
            return
        chat_id = message.chat.id
        session = self.sessions.get(chat_id)
        if not session or session.stage != Stage.SUBJECT or session.subject_message_id != message.message_id:
            return
        prefix, _, subject_id = (query.data or "").partition(":")
        if prefix != "subject" or not subject_id.isascii() or not subject_id.isdecimal() or len(subject_id) > 18:
            return

        person = BotUsers.objects.filter(chat_id=chat_id, status=True).first()
        subject = Subject.objects.filter(pk=int(subject_id)).first()
        if person is None or subject is None:
            return
        language = "ru" if person.lang == "ru" else "uz"
        labels = self.strings[language]
        subject_name = subject.name_ru if language == "ru" else subject.name_uz
        files = list(subject.file_set.filter(language=language).order_by("pk"))
        if not subject_name or not files:
            self.send(chat_id, labels["file_not_found"])
            return

        stored_number = person.last_test_no
        previous = int(stored_number) if stored_number.isascii() and stored_number.isdecimal() else 0
        test_number = previous + 1 if previous < len(files) else 1
        try:
            with files[test_number - 1].upload.open("rb") as document:
                self.client.send_document(chat_id, document)
        except OSError:
            self.send(chat_id, labels["file_not_found"])
            return

        person.last_test_no = str(test_number)
        person.save(update_fields=["last_test_no"])
        self.sessions[chat_id] = Session(Stage.FIRST_ANSWERS, subject_name, language, test_number)
        self.send(chat_id, labels["answer_msg"])
        self.send(chat_id, labels["enter_first"])

    def show_results(self, person, labels, session):
        chat_id = person.chat_id
        try:
            score, result = getPoint(session.language, session.subject_name, session.test_number, session.answers)
            grant, contract = getResult(score, session.language, "kunduzgi", session.subject_name)
        except (OSError, ValueError, KeyError, TypeError):
            logger.warning("Exam results could not be loaded.")
            self.send(chat_id, labels["file_not_found"])
            return
        total = len(grant.splitlines()) + len(contract.splitlines())
        self.send(chat_id, labels["pass"].format(score, total) if total else labels["fail"].format(score))
        if grant:
            self.send(chat_id, "Grant asosida:\n" + grant)
        if contract:
            self.send(chat_id, "Kontrakt asosida:\n" + contract)
        self.send(chat_id, getSolid(result))
        self.menu(person, labels)
        self.sessions.pop(chat_id, None)


class PollingErrors:
    def handle(self, exception):
        logger.warning("Telegram polling or update handling failed.")
        return True


class Command(BaseCommand):
    help = "Run the Telegram exam bot."

    def handle(self, *args, **options):
        if not settings.BOT_TOKEN:
            raise CommandError("Set bot_token before starting polling.")
        # Library error messages can contain request URLs and Telegram payloads.
        logging.getLogger("TeleBot").disabled = True
        try:
            client = TeleBot(settings.BOT_TOKEN, threaded=False, exception_handler=PollingErrors())
        except ValueError:
            raise CommandError("bot_token has an invalid format.") from None
        ExamBot(client)
        client.infinity_polling(allowed_updates=["message", "callback_query"])
