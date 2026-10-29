"""Assert every quiz answer and reading claim in the draft units 2-5.

    cd backend && uv run python -I ../docs/devhub-2.0/review/python-units-2-5/verify_answers.py
"""

import sys

def raises(src, exc):
    try:
        exec(compile(src, "<q>", "exec"), {})
    except exc:
        return True
    except Exception:
        return False
    return False

def syntax_error(src):
    try:
        compile(src, "<q>", "exec")
    except SyntaxError:
        return True
    return False

checks = {}
# --- unit 2
checks["u2 assign-vs-compare: SyntaxError"] = syntax_error("x = 5\nif x = 5:\n    pass\n")
falsy = {"0": 0, '""': "", '"0"': "0", "0.0": 0.0, '" "': " "}
checks["u2 falsy-values: {0, \"\", 0.0}"] = {k for k, v in falsy.items() if not v} == {"0", '""', "0.0"}
checks["u2 not-and: True"] = (not (3 > 2 and 1 > 5)) is True
# reading table rows
checks["u2 table"] = (3 == 3, 3 != 3, 2 < 5, 5 >= 5) == (True, False, True, True)
checks["u2 not True"] = (not True) is False
def ticket(age):
    if age < 7: return 0
    elif age <= 18: return 5000
    elif age <= 64: return 10000
    else: return 3000
checks["u2 exercise solvable"] = [ticket(a) for a in (6, 7, 18, 19, 64, 65)] == [0, 5000, 5000, 10000, 10000, 3000]
# --- unit 3
checks["u3 range table"] = (list(range(5)), list(range(1, 6)), list(range(0, 10, 3)), list(range(5, 0, -1))) == (
    [0, 1, 2, 3, 4], [1, 2, 3, 4, 5], [0, 3, 6, 9], [5, 4, 3, 2, 1])
checks["u3 range-count: 9"] = len(range(1, 10)) == 9
lines = {"a": len(range(0, 6, 2)), "b": len("abc"), "c": len(range(1, 3)), "d": len(range(3, 0))}
checks["u3 three-lines: a,b"] = {k for k, n in lines.items() if n == 3} == {"a", "b"} and lines["d"] == 0
checks["u3 exercise 1..100 = 5050"] = sum(range(1, 101)) == 5050
checks["u3 exercise 7x9"] = f"7 x 9 = {7 * 9}" == "7 x 9 = 63"
# --- unit 4
checks["u4 return-ends: '0 또는 음수'"] = (lambda n: "양수" if n > 0 else "0 또는 음수")(-3) == "0 또는 음수"
area = "def area(width, height=1):\n    return width * height\n"
ok = {c: not raises(area + c, Exception) and not syntax_error(area + c)
      for c in ("area(3)", "area(3, 4)", "area(height=2, width=3)", "area()", "area(width=3, 4)")}
checks["u4 valid-calls: a,b,c"] = ok == {"area(3)": True, "area(3, 4)": True, "area(height=2, width=3)": True,
                                        "area()": False, "area(width=3, 4)": False}
checks["u4 area() TypeError"] = raises(area + "area()", TypeError)
checks["u4 positional after keyword SyntaxError"] = syntax_error(area + "area(width=3, 4)")
checks["u4 default after non-default rule"] = syntax_error("def f(a=1, b):\n    pass\n")
g = {}
exec('def greet(name, greeting="안녕하세요"):\n    return greeting + ", " + name\n', g)
checks["u4 keyword greet"] = g["greet"](greeting="좋은 아침", name="지수") == "좋은 아침, 지수"
discounted = lambda price, rate=0.1: int(price * (1 - rate))
checks["u4 exercise solvable"] = (discounted(12000), discounted(12000, rate=0.25)) == (10800, 9000)
# --- unit 5
nums = [10, 20, 30, 40]
checks["u5 negative-index: 40"] = nums[-1] == 40
checks["u5 slicing: [20, 30]"] = nums[1:3] == [20, 30]
checks["u5 missing-key KeyError"] = raises('user = {"name": "민수"}\nprint(user["age"])', KeyError)
fruits = ["사과", "배"]; fruits.append("귤")
answers = {"a": len(fruits) == 3, "b": "배" in fruits, "c": fruits[2] == "귤", "d": fruits[0] == "배"}
checks["u5 list-after-append: a,b,c"] = {k for k, v in answers.items() if v} == {"a", "b", "c"}
checks["u5 IndexError"] = raises('f = ["a", "b", "c"]\nf[3]', IndexError)
user = {"name": "민수", "age": 21, "city": "서울"}
checks["u5 get"] = (user.get("email"), user.get("email", "없음"), "email" in user) == (None, "없음", False)
out = [f"{k} {v}" for k, v in user.items()]
checks["u5 items order"] = out == ["name 민수", "age 21", "city 서울"]
checks["u5 duplicate literal key"] = eval('{"x": 1, "x": 2}') == {"x": 2}
fr = ["사과", "배", "귤"]; fr[1] = "포도"; fr.append("감")
checks["u5 table"] = fr == ["사과", "포도", "귤", "감"] and fr[1:3] == ["포도", "귤"]
scores = [72, 88, 95, 64, 81]
checks["u5 exercise high"] = [s for s in scores if s >= 80] == [88, 95, 81]
counts = {}
for w in ["python", "java", "python", "go", "python"]:
    counts[w] = counts.get(w, 0) + 1
checks["u5 exercise counts"] = counts == {"python": 3, "java": 1, "go": 1}

for name, passed in checks.items():
    print("PASS" if passed else "FAIL", name)
print(sys.version.split()[0], f"{sum(checks.values())}/{len(checks)} passed")
sys.exit(0 if all(checks.values()) else 1)
