import json
import os
import runpy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.conf import settings
from django.test import TestCase, override_settings
from telebot import TeleBot, types

from tgapp.management.commands.bot import ExamBot, Stage
from tgapp.models import BotUsers, File, Subject
from tgapp.tools.result_check import getPoint


class BotTests(TestCase):
    first = 10_000_000_001
    second = 10_000_000_002

    def setUp(self):
        self.client = TeleBot("123:fake-test-token", threaded=False)
        self.send = Mock(side_effect=[
            Mock(message_id=message_id) for message_id in range(100, 150)
        ])
        self.client.send_message = self.send
        self.client.send_document = Mock()
        self.client.answer_callback_query = Mock()
        self.bot = ExamBot(self.client)
        self.labels = self.bot.strings["uz"]
        for chat_id in (self.first, self.second):
            BotUsers.objects.create(chat_id=chat_id, lang="uz", status=True)

    def message(self, chat_id, text=None, phone=None):
        update = {
            "message_id": 1,
            "date": 1,
            "chat": {"id": chat_id, "type": "private"},
            "from": {"id": chat_id, "is_bot": False, "first_name": "Example"},
        }
        if phone is None:
            update["text"] = text
        else:
            update["contact"] = {"phone_number": phone, "first_name": "Example"}
        self.client.process_new_messages([types.Message.de_json(update)])

    def choose_subject(self, chat_id, subject, message_id):
        query = types.CallbackQuery.de_json({
            "id": "example-query",
            "chat_instance": "example-chat",
            "from": {"id": chat_id, "is_bot": False, "first_name": "Example"},
            "message": {
                "message_id": message_id,
                "date": 1,
                "chat": {"id": chat_id, "type": "private"},
                "text": "Choose a subject",
            },
            "data": f"subject:{subject.pk}",
        })
        self.client.process_new_callback_query([query])

    def test_stop_only_updates_sender_and_clears_sender_session(self):
        self.message(self.first, "/start")
        self.message(self.second, "/start")
        self.message(self.first, "/stop")

        self.assertNotIn(self.first, self.bot.sessions)
        self.assertEqual(self.bot.sessions[self.second].stage, Stage.NAME)
        self.assertFalse(BotUsers.objects.get(chat_id=self.first).status)
        self.assertTrue(BotUsers.objects.get(chat_id=self.second).status)
        self.message(self.first, self.labels["personal_information"])
        self.assertEqual(self.send.call_args.args[:2], (self.first, "STOP"))

    def test_registration_with_contact_does_not_log_private_data(self):
        with self.assertNoLogs("tgapp.management.commands.bot", level="DEBUG"):
            self.message(self.first, "/start")
            self.message(self.first, "Private example name")
            self.message(self.first, phone="+998901234567")

        profile = BotUsers.objects.get(chat_id=self.first)
        self.assertEqual(profile.last_name, "Private example name")
        self.assertEqual(profile.phone_number, "+998901234567")
        self.assertTrue(profile.status)
        self.assertNotIn(self.first, self.bot.sessions)

    def test_interleaved_exams_use_each_chats_own_subject_and_answers(self):
        subject = Subject.objects.create(name_uz="Matematika-Chet tili")
        other_subject = Subject.objects.create(name_uz="Chet tili-Ona tili")
        with TemporaryDirectory() as data, override_settings(MEDIA_ROOT=data, ANSWERS_DIR=Path(data)):
            (Path(data) / "exam.pdf").write_bytes(b"example PDF")
            for exam, letter in ((subject, "A"), (other_subject, "B")):
                File.objects.create(subject_name=exam, upload="exam.pdf")
                directory = Path(data) / exam.name_uz
                directory.mkdir()
                (directory / "1.json").write_text(json.dumps({"answers": [letter] * 105}), encoding="utf-8")

            for chat_id in (self.first, self.second):
                self.message(chat_id, self.labels["start_test"])
            first_prompt = self.bot.sessions[self.first].subject_message_id
            second_prompt = self.bot.sessions[self.second].subject_message_id
            self.choose_subject(self.first, subject, second_prompt)
            self.assertEqual(self.bot.sessions[self.first].stage, Stage.SUBJECT)
            self.choose_subject(self.first, subject, first_prompt)
            self.choose_subject(self.second, other_subject, second_prompt)
            for chat_id, letter in ((self.first, "A"), (self.second, "B")):
                self.message(chat_id, " ".join([letter] * 45))
            for chat_id, letter in ((self.second, "B"), (self.first, "A")):
                self.message(chat_id, " ".join([letter] * 60))

            with patch("tgapp.management.commands.bot.getPoint", wraps=getPoint) as score:
                self.message(self.second, self.labels["yes"])
                self.message(self.first, self.labels["yes"])
                self.assertEqual([call.args[1:] for call in score.call_args_list], [
                    (other_subject.name_uz, 1, "B" * 105),
                    (subject.name_uz, 1, "A" * 105),
                ])
            results = [call.args for call in self.send.call_args_list if "280.5" in call.args[1]]
            self.assertEqual([chat_id for chat_id, _ in results], [self.second, self.first])
            self.assertEqual(self.bot.sessions, {})

    def test_debug_false_is_parsed_as_a_boolean(self):
        for configured, expected in (("False", False), ("True", True)):
            with patch.dict(os.environ, {"debug": configured, "secret_key": "test-key"}):
                configured_settings = runpy.run_path(str(settings.BASE_DIR / "tgproj" / "settings.py"))
                self.assertIs(configured_settings["DEBUG"], expected)
