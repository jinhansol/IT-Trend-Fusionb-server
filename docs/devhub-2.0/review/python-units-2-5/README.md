# Python 기초 2~5단원 초안 — 검토 자료

> **상태: UNVERIFIED 초안, 사용자 검토 전. 정식 콘텐츠가 아닙니다.** 이 폴더는 학습 콘텐츠 로더의 반영 대상이 아닙니다.
> 설명·예제·퀴즈는 AI(Claude)가 일반 지식으로 작성했고, 공식 Python 문서와 대조하지 않았습니다
> (작성 환경에서 docs.python.org 접속 불가). 예제 출력과 퀴즈 정답은 Python 3.12 실행으로만 확인했습니다.
> 로더와 CI는 `backend/content/<트랙>/`만 읽습니다. 확정 후 `units/*.yaml`을
> `backend/content/python/units/`로 옮기는 별도 커밋으로 반영합니다.

| 단원 | 파일 | 예상 | 난이도 | 퀴즈 (단일+복수) |
|---|---|---|---|---|
| 2. 조건문 | `units/02-conditionals.yaml` | 40분 | 입문 | 4 + 1 |
| 3. 반복문 | `units/03-loops.yaml` | 45분 | 입문~초급 | 4 + 1 |
| 4. 함수 | `units/04-functions.yaml` | 45분 | 초급 | 4 + 1 |
| 5. 리스트와 딕셔너리 | `units/05-lists-and-dicts.yaml` | 50분 | 초급 | 4 + 1 |

## 구성
- 모든 단원은 1단원(`backend/content/python/units/01-variables-and-types.yaml`)과 형식이 같습니다.
  - 필수 읽기 2개, 공식 튜토리얼 링크(필수) 1개, 선택 실습 1개
  - 퀴즈 5문항, 통과 기준 80%
  - `technologies: [python]`
- 난이도 표기:
  - 단원: 입문 → 초급
  - 문항: 하 / 중 / 중상. 작성자가 판단한 값이며, 검토 시 조정하면 됩니다.
- 앞 단원에서 배우지 않은 개념은 쓰지 않도록 했습니다.
  - 예: 2단원의 거짓 값 설명에서는 리스트와 `None`을 빼고 `0`, `0.0`, `""`만 다룹니다.
  - 5단원 실습만 1~4단원 개념을 종합합니다.

## 검증 (작성 시점)
| 검사 | 방법 | 결과 |
|---|---|---|
| 예제 출력 | `run_examples.py`로 모든 ```python 블록 실행 (Python 3.12.3) | 주석의 출력과 모두 일치 |
| 정답·주장 | `verify_answers.py`로 단언 (정답, 오류 종류, 표의 값, 실습 정답) | 29/29 통과 |
| 로더 검증 | 1~5단원 임시 트랙을 테스트 DB에 `content_loader load --dry-run` | 통과 (굵게 표시 규칙 포함, 저장 안 함) |
| 공식 문서 링크 | docs.python.org | **UNVERIFIED**: 작성 환경에서 접속 차단. 앵커 없이 페이지 URL만 사용 |

`run_examples.py` 출력에서 다음 세 블록은 의도된 결과입니다.
- `greet`, `user`의 NameError: 앞 블록에 이어지는 코드라 단독 실행 시 발생합니다.
- `KeyError: 'age'`: 그 오류를 묻는 문항입니다.

`verify_answers.py`는 이 세 블록을 이어서 실행하거나 별도로 확인합니다.

```bash
cd backend
uv run python -I ../docs/devhub-2.0/review/python-units-2-5/run_examples.py
uv run python -I ../docs/devhub-2.0/review/python-units-2-5/verify_answers.py
```

## 검토 요청 사항
1. 학습 목표와 난이도가 대상(처음 배우는 사람)에 맞는지.
2. 공식 튜토리얼 링크와 안내 문구. 링크가 열리는지, 해당 절이 맞는지 확인 필요.
3. 예제와 퀴즈의 표현.
   - 오답 선택지가 지나치게 쉽거나 헷갈리지 않는지.
   - 복수 선택 문항의 난이도.
4. 단원 순서(2 조건문 → 3 반복문 → 4 함수 → 5 리스트·딕셔너리)와 예상 학습 시간.
5. 실습 주제를 바꾸고 싶은 단원이 있는지.

---

## 2단원. 조건문  (`02-conditionals.yaml`)

- slug `conditionals` · 예상 40분 · 기술 `python` · 통과 기준 80%
- 난이도: 입문 (1단원 직후). 들여쓰기·콜론 문법을 처음 접함
- 선수 학습: 1단원(변수, int/float/str/bool)
- 요약: 비교·논리 연산으로 참과 거짓을 만들고, if / elif / else로 상황에 따라 다른 코드를 실행하는 방법을 배웁니다.

### 학습 목표
1. 비교 연산자(`==`, `!=`, `<`, `>`, `<=`, `>=`)로 `True`/`False`를 만들 수 있다
2. `and`, `or`, `not`으로 조건을 조합할 수 있다
3. `if`/`elif`/`else`의 실행 순서(처음 참인 블록 하나만)를 설명하고 조건 순서를 올바르게 정할 수 있다
4. `=`(대입)와 `==`(비교)를 구분하고, 거짓으로 취급되는 기본 값(`0`, `0.0`, `""`)을 안다

### 활동 구성 (설명)
| # | 종류 | 제목 | 필수 | 소제목 · 링크 · 첫 문장 |
|---|---|---|---|---|
| 1 | 읽기 | 비교 연산과 논리 연산 | 필수 | 논리 연산자, 참·거짓으로 쓰이는 값 |
| 2 | 읽기 | if, elif, else | 필수 | 동작 순서 |
| 3 | 외부 자료 | 공식 튜토리얼: 제어 흐름 도구 | 필수 | https://docs.python.org/ko/3/tutorial/controlflow.html (UNVERIFIED: 이 환경에서 접속 불가) |
| 4 | 실습 | 직접 해보기: 입장료 계산 | 선택 | 나이에 따라 입장료를 정하는 프로그램을 완성해 보세요. |

### 예제 코드 (3개, 모두 Python 3.12로 실행해 주석의 출력과 일치 확인)

<details><summary>비교 연산과 논리 연산</summary>

```python
age = 15
print(age >= 13 and age < 20)  # True
print(13 <= age < 20)          # True (비교를 이어 쓸 수도 있습니다)
print(not age > 10)            # False
```
</details>

<details><summary>if, elif, else</summary>

```python
score = 85

if score >= 90:
    grade = "A"
elif score >= 80:
    grade = "B"
elif score >= 70:
    grade = "C"
else:
    grade = "F"

print(grade)  # B
```
</details>

<details><summary>if, elif, else</summary>

```python
n = 7
if n % 2 == 0:
    print("짝수")
else:
    print("홀수")  # 홀수
```
</details>

### 퀴즈 · 정답 · 해설
| # | key | 유형 | 난이도 | 문항 | 정답 | 해설 |
|---|---|---|---|---|---|---|
| 1 | `elif-first-match` | 단일 | 하 | 다음 코드의 출력은 무엇일까요?  (아래 문항 코드) | `b) B` | 위에서부터 검사해 처음으로 참인 `score >= 80` 블록만 실행합니다. 85는 70 이상이기도 하지만 그 블록은 건너뜁니다. |
| 2 | `assign-vs-compare` | 단일 | 하 | `x = 5` 다음에 `if x = 5:`라고 쓰면 어떻게 될까요? | `c) SyntaxError가 발생한다` | 조건에는 비교 연산자 `==`를 써야 합니다. `=`는 대입이므로 `if x = 5:`는 실행 전에 `SyntaxError`가 납니다. |
| 3 | `falsy-values` | 복수 | 중 | 조건 자리에서 **거짓**으로 취급되는 값을 **모두** 고르세요. | `a) 0` / `b) ""` / `d) 0.0` | `0`, `0.0`, 빈 문자열 `""`은 거짓입니다. `"0"`과 `" "`은 글자가 들어 있는 문자열이므로 참입니다. |
| 4 | `not-and` | 단일 | 중 | `not (3 > 2 and 1 > 5)`의 결과는 무엇일까요? | `a) True` | `3 > 2`는 참, `1 > 5`는 거짓이라 `and`의 결과는 `False`입니다. `not`이 이를 뒤집어 `True`가 됩니다. |
| 5 | `condition-order` | 단일 | 중 | 다음 코드의 출력은 무엇일까요?  (아래 문항 코드) | `b) D` | 95는 첫 조건 `score >= 60`에서 이미 참이므로 `D`를 출력하고 나머지는 건너뜁니다. 넓은 조건을 먼저 쓰면 좁은 조건에 닿지 못합니다. |

<details><summary>문항 1 코드 (`elif-first-match`)</summary>

```python
score = 85
if score >= 90:
    print("A")
elif score >= 80:
    print("B")
elif score >= 70:
    print("C")
else:
    print("F")
```
</details>

<details><summary>문항 5 코드 (`condition-order`)</summary>

```python
score = 95
if score >= 60:
    print("D")
elif score >= 90:
    print("A")
else:
    print("F")
```
</details>

## 3단원. 반복문  (`03-loops.yaml`)

- slug `loops` · 예상 45분 · 기술 `python` · 통과 기준 80%
- 난이도: 입문~초급. `range` 끝값 미포함과 반복 추적이 주된 난관
- 선수 학습: 1·2단원(조건문은 break/continue 예제에 사용)
- 요약: for와 range()로 정해진 횟수만큼, while로 조건이 참인 동안 같은 코드를 반복하고, break와 continue로 반복을 조절합니다.

### 학습 목표
1. `for`와 `range(start, stop, step)`으로 정해진 횟수만큼 반복할 수 있다 (끝값 미포함)
2. 문자열을 `for`로 한 글자씩 순회할 수 있다
3. `while`로 조건 반복을 작성하고 무한 반복을 피할 수 있다
4. `break`와 `continue`의 차이를 설명할 수 있다

### 활동 구성 (설명)
| # | 종류 | 제목 | 필수 | 소제목 · 링크 · 첫 문장 |
|---|---|---|---|---|
| 1 | 읽기 | for와 range() | 필수 | `for`는 여러 값을 **하나씩 꺼내** 같은 코드를 반복합니다. |
| 2 | 읽기 | while, break, continue | 필수 | break와 continue |
| 3 | 외부 자료 | 공식 튜토리얼: 제어 흐름 도구 | 필수 | https://docs.python.org/ko/3/tutorial/controlflow.html (UNVERIFIED: 이 환경에서 접속 불가) |
| 4 | 실습 | 직접 해보기: 구구단과 합계 | 선택 | 아래 두 프로그램을 완성해 보세요. |

### 예제 코드 (4개, 모두 Python 3.12로 실행해 주석의 출력과 일치 확인)

<details><summary>for와 range()</summary>

```python
for i in range(3):
    print("안녕", i)
# 안녕 0
# 안녕 1
# 안녕 2
```
</details>

<details><summary>for와 range()</summary>

```python
total = 0
for ch in "2026":
    total = total + int(ch)
print(total)  # 10
```
</details>

<details><summary>while, break, continue</summary>

```python
money = 10000
count = 0
while money >= 3000:
    money = money - 3000
    count = count + 1
print(count, money)  # 3 1000
```
</details>

<details><summary>while, break, continue</summary>

```python
for n in range(1, 10):
    if n % 2 == 0:
        continue      # 짝수는 건너뜁니다
    if n > 5:
        break         # 5보다 큰 홀수를 만나면 끝냅니다
    print(n)
# 1
# 3
# 5
```
</details>

### 퀴즈 · 정답 · 해설
| # | key | 유형 | 난이도 | 문항 | 정답 | 해설 |
|---|---|---|---|---|---|---|
| 1 | `range-step` | 단일 | 하 | 다음 코드의 출력은 무엇일까요?  (아래 문항 코드) | `a) 2 4 6` | `range(2, 8, 2)`는 2부터 8 직전까지 2씩 건너뛴 2, 4, 6을 만듭니다. 끝값 8은 포함되지 않습니다. |
| 2 | `range-count` | 단일 | 하 | `for i in range(1, 10):` 안의 코드는 몇 번 실행될까요? | `b) 9번` | `range(1, 10)`은 1부터 9까지이므로 9번 실행됩니다. |
| 3 | `while-result` | 단일 | 중 | 다음 코드의 출력은 무엇일까요?  (아래 문항 코드) | `c) -2` | `n`은 10, 7, 4, 1을 거쳐 -2가 됩니다. -2가 되면 `n > 0`이 거짓이라 반복이 끝나고 -2를 출력합니다. |
| 4 | `break-continue` | 단일 | 중 | 다음 코드의 출력은 무엇일까요?  (아래 문항 코드) | `a) 1 3` | 1은 출력하고, 2는 `continue`로 건너뛰고, 3은 출력합니다. 4에서 `break`로 반복이 끝나므로 5는 실행되지 않습니다. |
| 5 | `three-lines` | 복수 | 중상 | 본문에 `print()` 한 줄만 있을 때, 정확히 **3번** 출력하는 반복문을 **모두** 고르세요. | `a) for i in range(0, 6, 2):` / `b) for ch in "abc":` | `range(0, 6, 2)`는 0, 2, 4이고 `"abc"`는 글자가 3개라 3번입니다. `range(1, 3)`은 1, 2로 2번이고, `range(3, 0)`은 간격이 양수라 값이 없어 한 번도 실행되지 않습니다. |

<details><summary>문항 1 코드 (`range-step`)</summary>

```python
for i in range(2, 8, 2):
    print(i, end=" ")
```
</details>

<details><summary>문항 3 코드 (`while-result`)</summary>

```python
n = 10
while n > 0:
    n = n - 3
print(n)
```
</details>

<details><summary>문항 4 코드 (`break-continue`)</summary>

```python
for i in range(1, 6):
    if i == 2:
        continue
    if i == 4:
        break
    print(i, end=" ")
```
</details>

## 4단원. 함수  (`04-functions.yaml`)

- slug `functions` · 예상 45분 · 기술 `python` · 통과 기준 80%
- 난이도: 초급. `return` vs `print`, 지역 변수가 흔한 오개념
- 선수 학습: 1~3단원
- 요약: 반복되는 코드를 def로 묶어 이름을 붙이고, 매개변수로 값을 받아 return으로 결과를 돌려주는 함수를 만듭니다.

### 학습 목표
1. `def`로 함수를 정의하고 인자를 넘겨 호출할 수 있다 (매개변수·인자 용어 구분)
2. `return`과 `print()`의 차이, `return`이 없을 때 `None`이 됨을 설명할 수 있다
3. 기본값 매개변수와 키워드 인자를 쓸 수 있고 순서 규칙을 안다
4. 함수 안의 변수가 지역 변수임을 이해한다

### 활동 구성 (설명)
| # | 종류 | 제목 | 필수 | 소제목 · 링크 · 첫 문장 |
|---|---|---|---|---|
| 1 | 읽기 | 함수 정의와 return | 필수 | return과 print는 다릅니다 |
| 2 | 읽기 | 기본값, 키워드 인자, 지역 변수 | 필수 | 기본값이 있는 매개변수, 키워드 인자, 지역 변수 |
| 3 | 외부 자료 | 공식 튜토리얼: 제어 흐름 도구 | 필수 | https://docs.python.org/ko/3/tutorial/controlflow.html (UNVERIFIED: 이 환경에서 접속 불가) |
| 4 | 실습 | 직접 해보기: 할인 가격 함수 | 선택 | 아래 함수를 완성해 보세요. |

### 예제 코드 (5개, 모두 Python 3.12로 실행해 주석의 출력과 일치 확인)

<details><summary>함수 정의와 return</summary>

```python
def add(a, b):
    return a + b

result = add(3, 4)
print(result)       # 7
print(add(10, 20))  # 30
```
</details>

<details><summary>함수 정의와 return</summary>

```python
def show(x):
    print(x * 2)

value = show(5)  # 10이 출력됩니다
print(value)     # None
```
</details>

<details><summary>기본값, 키워드 인자, 지역 변수</summary>

```python
def greet(name, greeting="안녕하세요"):
    return greeting + ", " + name

print(greet("민수"))          # 안녕하세요, 민수
print(greet("민수", "반가워"))  # 반가워, 민수
```
</details>

<details><summary>기본값, 키워드 인자, 지역 변수</summary>

```python
print(greet(greeting="좋은 아침", name="지수"))  # 좋은 아침, 지수
```
</details>

<details><summary>기본값, 키워드 인자, 지역 변수</summary>

```python
def double(n):
    n = n * 2
    return n

x = 5
print(double(x))  # 10
print(x)          # 5
```
</details>

### 퀴즈 · 정답 · 해설
| # | key | 유형 | 난이도 | 문항 | 정답 | 해설 |
|---|---|---|---|---|---|---|
| 1 | `default-argument` | 단일 | 하 | 다음 코드의 출력은 무엇일까요?  (아래 문항 코드) | `b) 15` | `b`를 넘기지 않았으므로 기본값 10이 쓰여 5 + 10 = 15를 돌려줍니다. |
| 2 | `no-return` | 단일 | 중 | 다음 코드에서 **마지막 줄**의 출력은 무엇일까요?  (아래 문항 코드) | `b) None` | `hello()`는 `hi`를 출력하지만 `return`이 없으므로 돌려주는 값은 `None`입니다. |
| 3 | `local-variable` | 단일 | 중 | 다음 코드의 출력은 무엇일까요?  (아래 문항 코드) | `a) 5` | 함수 안의 `x`는 지역 변수라 바깥의 `n`은 바뀌지 않습니다. 돌려준 6은 어디에도 담지 않았으므로 `n`은 그대로 5입니다. |
| 4 | `valid-calls` | 복수 | 중상 | `def area(width, height=1):`로 정의한 함수를 오류 없이 호출하는 것을 **모두** 고르세요. | `a) area(3)` / `b) area(3, 4)` / `c) area(height=2, width=3)` | `width`는 기본값이 없으니 반드시 넘겨야 합니다. 키워드 인자는 순서를 바꿔도 되지만, 위치 인자가 키워드 인자 뒤에 오면 `SyntaxError`입니다. |
| 5 | `return-ends` | 단일 | 하 | `check(-3)`의 결과는 무엇일까요?  (아래 문항 코드) | `b) "0 또는 음수"` | `-3 > 0`은 거짓이라 첫 `return`을 건너뛰고 두 번째 `return`이 실행됩니다. `n`이 양수였다면 첫 `return`에서 함수가 끝났을 것입니다. |

<details><summary>문항 1 코드 (`default-argument`)</summary>

```python
def add(a, b=10):
    return a + b

print(add(5))
```
</details>

<details><summary>문항 2 코드 (`no-return`)</summary>

```python
def hello():
    print("hi")

result = hello()
print(result)
```
</details>

<details><summary>문항 3 코드 (`local-variable`)</summary>

```python
def plus_one(x):
    x = x + 1
    return x

n = 5
plus_one(n)
print(n)
```
</details>

<details><summary>문항 5 코드 (`return-ends`)</summary>

```python
def check(n):
    if n > 0:
        return "양수"
    return "0 또는 음수"
```
</details>

## 5단원. 리스트와 딕셔너리  (`05-lists-and-dicts.yaml`)

- slug `lists-and-dicts` · 예상 50분 · 기술 `python` · 통과 기준 80%
- 난이도: 초급. 1~4단원 개념을 종합(반복·조건과 함께 사용)
- 선수 학습: 1~4단원 (실습은 반복문·조건문 사용)
- 요약: 여러 값을 순서대로 담는 리스트와, 키로 값을 찾는 딕셔너리를 만들고 꺼내고 바꾸는 방법을 배웁니다.

### 학습 목표
1. 리스트를 만들고 인덱스(0부터, 음수)와 슬라이싱(끝 미포함)으로 값을 꺼낼 수 있다
2. `append`, 값 변경, `in`, `len`, `for` 순회를 쓸 수 있다
3. 딕셔너리에서 키로 값을 꺼내고, 추가·변경하고, `items()`로 순회할 수 있다
4. 없는 키의 `KeyError`와 `get()`의 기본값 처리를 구분할 수 있다

### 활동 구성 (설명)
| # | 종류 | 제목 | 필수 | 소제목 · 링크 · 첫 문장 |
|---|---|---|---|---|
| 1 | 읽기 | 리스트 | 필수 | 자주 쓰는 기능 |
| 2 | 읽기 | 딕셔너리 | 필수 | 없는 키 다루기, 반복하기 |
| 3 | 외부 자료 | 공식 튜토리얼: 자료 구조 | 필수 | https://docs.python.org/ko/3/tutorial/datastructures.html (UNVERIFIED: 이 환경에서 접속 불가) |
| 4 | 실습 | 직접 해보기: 점수표와 단어 세기 | 선택 | 아래 두 프로그램을 완성해 보세요. |

### 예제 코드 (4개, 모두 Python 3.12로 실행해 주석의 출력과 일치 확인)

<details><summary>리스트</summary>

```python
fruits = ["사과", "배", "귤"]
print(fruits[0])    # 사과  (번호는 0부터 시작합니다)
print(fruits[-1])   # 귤    (음수는 뒤에서부터 셉니다)
print(len(fruits))  # 3
```
</details>

<details><summary>리스트</summary>

```python
scores = [80, 95, 70]
total = 0
for s in scores:
    total = total + s
print(total / len(scores))  # 81.66666666666667
```
</details>

<details><summary>딕셔너리</summary>

```python
user = {"name": "민수", "age": 20}
print(user["name"])      # 민수
user["age"] = 21         # 있는 키는 값을 바꿉니다
user["city"] = "서울"     # 없는 키는 새로 추가합니다
print(user)  # {'name': '민수', 'age': 21, 'city': '서울'}
```
</details>

<details><summary>딕셔너리</summary>

```python
for key, value in user.items():
    print(key, value)
# name 민수
# age 21
# city 서울
```
</details>

### 퀴즈 · 정답 · 해설
| # | key | 유형 | 난이도 | 문항 | 정답 | 해설 |
|---|---|---|---|---|---|---|
| 1 | `negative-index` | 단일 | 하 | `nums = [10, 20, 30, 40]`일 때 `nums[-1]`의 값은 무엇일까요? | `c) 40` | 음수 번호는 뒤에서부터 셉니다. `-1`은 마지막 값인 40입니다. |
| 2 | `slicing` | 단일 | 중 | `nums = [10, 20, 30, 40]`일 때 `nums[1:3]`의 값은 무엇일까요? | `b) [20, 30]` | 슬라이싱은 시작 번호부터 끝 번호 **직전**까지입니다. 1번(20)과 2번(30)이 담깁니다. |
| 3 | `missing-key` | 단일 | 하 | 다음 코드를 실행하면 어떻게 될까요?  (아래 문항 코드) | `c) KeyError가 발생한다` | 없는 키를 대괄호로 꺼내면 `KeyError`가 납니다. 오류 없이 확인하려면 `user.get("age")`처럼 `get()`을 씁니다. |
| 4 | `list-after-append` | 복수 | 중 | `fruits = ["사과", "배"]` 다음에 `fruits.append("귤")`을 실행했습니다. 참인 것을 **모두** 고르세요. | `a) len(fruits) == 3` / `b) "배" in fruits` / `c) fruits[2] == "귤"` | `append()`는 끝에 값을 추가하므로 `["사과", "배", "귤"]`이 됩니다. 길이는 3, 2번 값은 `"귤"`, 0번 값은 `"사과"`입니다. |
| 5 | `update-and-add` | 단일 | 중 | 다음 코드의 출력은 무엇일까요?  (아래 문항 코드) | `b) {'apple': 5, 'pear': 1}` | `apple`은 이미 있는 키라 값이 5로 바뀌고, `pear`는 없는 키라 새로 추가됩니다. 키는 중복되지 않습니다. |

<details><summary>문항 3 코드 (`missing-key`)</summary>

```python
user = {"name": "민수"}
print(user["age"])
```
</details>

<details><summary>문항 5 코드 (`update-and-add`)</summary>

```python
stock = {"apple": 3}
stock["apple"] = stock["apple"] + 2
stock["pear"] = 1
print(stock)
```
</details>

