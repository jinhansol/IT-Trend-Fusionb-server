"""Run every ```python block in the draft units and print its output under the code.

    cd backend && uv run python -I ../docs/devhub-2.0/review/python-units-2-5/run_examples.py

Compare each output with the "# ..." comments in the code. Exercise templates print
nothing (or None), and a block that continues the previous one in the same reading
fails alone with NameError; verify_answers.py checks those cases.
"""

import contextlib
import io
import re
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
BLOCK = re.compile(r"```python\n(.*?)```", re.S)

for path in sorted(HERE.glob("units/*.yaml")):
    unit = yaml.safe_load(path.read_text(encoding="utf-8"))
    texts = [(a["slug"], a.get("body_md") or "") for a in unit["activities"]]
    texts += [(q["key"], q["prompt"]) for q in unit["quiz"]["questions"]]
    for where, text in texts:
        for code in BLOCK.findall(text):
            out = io.StringIO()
            try:
                with contextlib.redirect_stdout(out):
                    exec(compile(code, where, "exec"), {})
                result = out.getvalue()
            except Exception as exc:  # expected for error examples
                result = out.getvalue() + f"!! {type(exc).__name__}: {exc}\n"
            print(f"===== {path.name} :: {where}\n{code}----- output:\n{result}")
