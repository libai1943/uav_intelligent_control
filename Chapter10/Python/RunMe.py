from pathlib import Path
import unittest
from prompt_builder import build_prompt,save_prompt,DEMO_REQUEST
if __name__=='__main__':
    suite=unittest.defaultTestLoader.discover(str(Path(__file__).parent),pattern='test_prompt_builder.py')
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():raise SystemExit(1)
    out=Path(__file__).parent/'results'/'complete_prompt.txt'
    save_prompt(build_prompt(DEMO_REQUEST),out)
    print(out)
