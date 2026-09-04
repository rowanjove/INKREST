import unittest
from novel_agent.json_utils import loads_json_object, repair_truncated_json


class TruncatedJSONRecoveryTests(unittest.TestCase):
    def test_repair_clean_json(self):
        sample = '{"arc_id": "A01", "chapters": [{"chapter_id": "001"}]}'
        self.assertEqual(repair_truncated_json(sample)["arc_id"], "A01")

    def test_repair_truncated_chapters_array(self):
        truncated = '''{
  "arc_id": "A01",
  "arc_name": "阶段一",
  "chapters": [
    {"chapter_id": "001", "chapter_title": "第一章"},
    {"chapter_id": "002", "chapter_title": "第二章"},
    {"chapter_id": "003", "chapter_title": "第三章", "scene_type": "burst
'''
        with self.assertRaises(Exception):
            loads_json_object(truncated)
        result = repair_truncated_json(truncated)
        self.assertEqual(result["arc_id"], "A01")
        self.assertEqual(result["arc_name"], "阶段一")
        self.assertEqual(len(result["chapters"]), 2)
        self.assertEqual(result["chapters"][0]["chapter_id"], "001")
        self.assertEqual(result["chapters"][1]["chapter_id"], "002")

    def test_repair_truncated_with_code_fence(self):
        fence = chr(96) * 3
        truncated = f'''{fence}json
{{
  "arc_id": "A02",
  "chapters": [
    {{"chapter_id": "010", "chapter_title": "第十章"}}
'''
        with self.assertRaises(Exception):
            loads_json_object(truncated)
        result = repair_truncated_json(truncated)
        self.assertEqual(result["arc_id"], "A02")
        self.assertEqual(len(result["chapters"]), 1)


if __name__ == "__main__":
    unittest.main()
