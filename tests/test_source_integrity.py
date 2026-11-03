"""Startup regression checks; never launch Chrome or submit a ritual."""
import ast
import csv
import os
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent.parent


class SourceIntegrityTests(unittest.TestCase):
    def test_no_unresolved_merge_markers_and_python_parses(self):
        for directory, folders, names in os.walk(ROOT):
            folders[:] = [name for name in folders if name not in ('.git', '.venv', '__pycache__')]
            for name in names:
                path = Path(directory) / name
                if path.suffix not in ('.py', '.cmd', '.csv'):
                    continue
                source = path.read_text(encoding='utf-8-sig')
                if re.search(r'^(?:<<<<<<< |=======\s*$|>>>>>>> )', source, re.M):
                    self.fail(f'Unresolved merge marker: {path.relative_to(ROOT)}')
                if path.suffix == '.py':
                    try:
                        ast.parse(source, filename=str(path))
                    except SyntaxError as error:
                        self.fail(f'Invalid Python: {path.relative_to(ROOT)}:{error.lineno}')

    def test_csv_keeps_one_copy_of_all_original_rows(self):
        expected = {f'{i}.csv': 500 for i in range(1, 8)}
        # Name.csv also had a legitimate third row outside the conflict block.
        expected.update({'Name.csv': 3, 'Title.csv': 1000})
        expected.update({f'close_{name}.csv': 900 for name in ('effort', 'gratitude', 'note', 'peer_story', 'share')})
        for name, count in expected.items():
            with self.subTest(file=name), (ROOT / 'csv' / name).open(encoding='utf-8-sig', newline='') as stream:
                self.assertEqual(sum(1 for _ in csv.reader(stream)), count)

    def test_both_versions_of_each_screen_title_are_preserved(self):
        expected = {
            'main.py': [('편안했던 장면 하나 떠올리기', '기분 좋아지는 생각 찾기'),
                        ('내 인생의 기억에서 강점(장점)과 가치 찾기', '지난 기억에서 내가 좋아하는 나의 장점 찾기'),
                        ('남에 대한 평가는 나에 대한 평가', '동료의 장점을 칭찬하기')],
            'close.py': [('아침에 정한 강점 행동을 돌아봅니다', '아침에 정한 행동을 돌아봅니다'),
                         ('오늘 감사했던 일을 동료들과 나눕니다', '감사한 일을 동료들과 나눕니다'),
                         ('오늘의 감사일기', '나의; 감사일기')],
        }
        for name, alternatives in expected.items():
            tree = ast.parse((ROOT / 'Playwright' / name).read_text(encoding='utf-8'))
            patterns = [re.compile(ast.literal_eval(node.args[0])) for node in ast.walk(tree)
                        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and isinstance(node.func.value, ast.Name) and node.func.value.id == 're'
                        and node.func.attr == 'compile']
            self.assertEqual(len(patterns), 3)
            for old, new in alternatives:
                self.assertTrue(any(pattern.search(old) and pattern.search(new) for pattern in patterns))
            self.assertFalse(any(pattern.search('unrelated-screen') for pattern in patterns))


if __name__ == '__main__':
    unittest.main()
