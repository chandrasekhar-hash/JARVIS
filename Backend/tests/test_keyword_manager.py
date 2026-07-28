import unittest
from Backend.voice.wakeword.keyword_manager import KeywordManager


class TestKeywordManager(unittest.TestCase):

    def setUp(self):
        self.mgr = KeywordManager(primary_keyword="jarvis")

    def test_initial_keywords(self):
        keywords = self.mgr.get_all_keywords()
        self.assertIn("jarvis", keywords)
        self.assertIn("computer", keywords)
        self.assertIn("nova", keywords)

    def test_add_and_remove_keyword(self):
        self.mgr.add_keyword("alexa")
        self.assertTrue(self.mgr.is_keyword_registered("alexa"))

        self.mgr.remove_keyword("alexa")
        self.assertFalse(self.mgr.is_keyword_registered("alexa"))

    def test_alias_registration(self):
        self.mgr.add_alias("jarvis", "hey buddy")
        self.assertTrue(self.mgr.is_keyword_registered("hey buddy"))

    def test_primary_keyword_change(self):
        self.mgr.set_primary_keyword("friday")
        self.assertEqual(self.mgr.primary_keyword, "friday")
        self.assertTrue(self.mgr.is_keyword_registered("friday"))


if __name__ == "__main__":
    unittest.main()
