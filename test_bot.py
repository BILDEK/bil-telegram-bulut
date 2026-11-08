"""Offline tests: do not access real Telegram/Gemini or credentials."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from cryptography.fernet import Fernet
import bot
from pc_protocol import open_job


class CloudRoutingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.now = int(time.time())
        self.key = Fernet.generate_key()
        self.patches = patch.multiple(bot, CHAT_ID="42", TOKEN="FAKE-NOT-REAL", GEMINI_KEY="fake",
                                     PC_QUEUE_KEY=self.key, PC_JOBS_FILE=str(self.base / "jobs.json"),
                                     OFFSET_FILE=str(self.base / "offset.json"))
        self.patches.start()
        self.addCleanup(self.patches.stop)

    def update(self, text, ident=123, sender=42, chat_type="private", date=None):
        return {"update_id": ident, "message": {"date": self.now if date is None else date,
                "text": text, "chat": {"id": 42, "type": chat_type},
                "from": {"id": sender, "is_bot": False}}}

    def queue(self):
        return json.loads((self.base / "jobs.json").read_text())["jobs"]

    def test_status_encrypted(self):
        bot.pc_reply(self.update("/pc durum"), "/pc durum")
        job = open_job(self.queue()[0], self.key, "42", self.now)
        self.assertEqual(job["action"], "status")

    def test_agent_not_plaintext(self):
        text = "/pc ajan gizli-test-komut"
        bot.pc_reply(self.update(text), text)
        self.assertNotIn("gizli-test-komut", (self.base / "jobs.json").read_text())
        job = open_job(self.queue()[0], self.key, "42", self.now)
        self.assertEqual(job["text"], "gizli-test-komut")

    def test_pair_alias(self):
        bot.pc_reply(self.update("/pc bağlan"), "/pc bağlan")
        self.assertEqual(open_job(self.queue()[0], self.key, "42", self.now)["action"], "pair")

    def test_duplicate_not_added(self):
        for _ in range(2):
            bot.pc_reply(self.update("/pc durum"), "/pc durum")
        self.assertEqual(len(self.queue()), 1)

    def test_stale_command_not_executed(self):
        self.assertIn("süresi dolmuş", bot.pc_reply(self.update("/pc durum", date=self.now - 601), "/pc durum"))
        self.assertFalse((self.base / "jobs.json").exists())

    def test_queue_limit(self):
        for i in range(52):
            bot.pc_reply(self.update("/pc durum", ident=i), "/pc durum")
        self.assertEqual(len(self.queue()), 50)
        self.assertEqual(self.queue()[0]["id"], "2")

    def test_owner_filter_and_no_gemini_for_pc(self):
        updates = [self.update("/pc durum", ident=1, sender=99),
                   self.update("/pc durum", ident=2, chat_type="group"),
                   self.update("/pc durum", ident=3)]
        def tg(method, **kwargs):
            return {"ok": True, "result": updates if method == "getUpdates" else {}}
        with patch.object(bot, "tg", side_effect=tg), patch.object(bot, "gemini") as gemini, contextlib.redirect_stdout(io.StringIO()):
            bot.main()
            gemini.assert_not_called()
        self.assertEqual(len(self.queue()), 1)
        self.assertEqual(self.queue()[0]["id"], "3")
        self.assertEqual(bot.load_offset(), 4)

    def test_error_logging_no_token(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            bot.log_error("test", RuntimeError("FAKE-NOT-REAL/private-command"))
        self.assertNotIn("FAKE-NOT-REAL", out.getvalue())


if __name__ == "__main__":
    unittest.main()
