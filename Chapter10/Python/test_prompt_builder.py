"""离线测试：只检查提示词生成和示例数据，不评估语言模型。"""
import json
import tempfile
import unittest
from pathlib import Path
from prompt_builder import ROOT, DEMO_REQUEST, build_prompt, save_prompt

class PromptTests(unittest.TestCase):
    def test_required_blocks(self):
        p = build_prompt(DEMO_REQUEST)
        for heading in ('【工作任务】', '【已核对的场景资料】', '【用户原话 U-01】',
                        '【整理规则】', '【固定输出格式】'):
            self.assertIn(heading, p)
    def test_default_context(self):
        p = build_prompt(DEMO_REQUEST)
        self.assertIn('本次暂停作业', p)
        self.assertIn('DEMO-S01', p)
    def test_no_template_placeholders(self):
        p = build_prompt(DEMO_REQUEST)
        self.assertNotIn('{{CONTEXT}}', p)
        self.assertNotIn('{{USER_REQUEST_JSON}}', p)
    def test_empty(self):
        for s in ('', '  ', '\n\t'):
            with self.assertRaises(ValueError): build_prompt(s)
    def test_wrong_type(self):
        with self.assertRaises(ValueError): build_prompt(None)
    def test_long_input(self):
        with self.assertRaises(ValueError): build_prompt('甲' * 6001)
    def test_quotes_and_newline(self):
        s = '先去"东库"。\n再去西库。'
        self.assertIn(json.dumps(s, ensure_ascii=False), build_prompt(s))
    def test_literal_braces(self):
        s = '保留原话中的{{CONTEXT}}和{{USER_REQUEST_JSON}}。'
        self.assertIn(json.dumps(s, ensure_ascii=False), build_prompt(s))
    def test_custom_context(self):
        p = build_prompt('只去A', 'F-A：A开放。')
        self.assertIn('F-A：A开放。', p)
        self.assertNotIn('F-B：仓库B', p)
    def test_empty_context(self):
        with self.assertRaises(ValueError): build_prompt('A', '')
    def test_reserved_context_marker(self):
        with self.assertRaises(ValueError): build_prompt('A', '{{USER_REQUEST_JSON}}')
    def test_utf8_write(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / '提示词.txt'
            p = build_prompt(DEMO_REQUEST)
            save_prompt(p, path)
            self.assertEqual(path.read_text(encoding='utf-8'), p)
    def test_expected_schema_keys(self):
        data = json.loads((ROOT / 'examples' / 'expected_main.json').read_text(encoding='utf-8'))
        self.assertEqual(set(data), {'status','visit_order','skipped','reason_codes','questions','evidence_ids'})
        self.assertEqual(data['visit_order'], ['A','C'])
    def test_sft_records_have_full_prompt(self):
        for line in (ROOT / 'examples' / 'sft_pairs_demo.jsonl').read_text(encoding='utf-8').splitlines():
            item = json.loads(line)
            messages = item['messages']
            self.assertEqual([m['role'] for m in messages], ['user','assistant'])
            self.assertIn('【固定输出格式】', messages[0]['content'])
            self.assertIsInstance(json.loads(messages[1]['content']), dict)

if __name__ == '__main__':
    unittest.main(verbosity=2)
