# asyncio 작업을 안전하게 취소하는 방법 (가상 기술 블로그)

이 글은 테스트를 위해 직접 작성한 가상의 기술 블로그 글이다. Python 3.12의 `asyncio.TaskGroup`을 사용해 여러 작업을 함께 실행하고, 하나가 실패했을 때 나머지를 안전하게 취소하는 방법을 정리한다. 예시 서비스는 외부 API 세 곳을 동시에 호출해 결과를 합치는 가상의 집계 서버다.

## 문제 상황

기존 코드는 `asyncio.gather`로 세 작업을 실행했다. 한 작업이 예외를 던져도 나머지 작업은 계속 실행되었고, 그 결과 이미 실패한 요청을 위해 외부 API 호출이 계속 나갔다. 또한 취소된 작업이 연결을 정리하지 못해 연결 풀이 고갈되는 일이 있었다.

## TaskGroup으로 바꾸기

`TaskGroup`은 그룹 안의 작업 하나가 실패하면 나머지 작업을 자동으로 취소하고, 모든 작업이 끝날 때까지 기다린 뒤 예외를 `ExceptionGroup`으로 묶어 전달한다.

```python
import asyncio

async def fetch_all(client, urls):
    results = {}
    async with asyncio.TaskGroup() as group:
        tasks = {url: group.create_task(client.get(url)) for url in urls}
    for url, task in tasks.items():
        results[url] = task.result()
    return results
```

호출하는 쪽에서는 `except*` 구문으로 실패한 작업의 예외만 골라 처리할 수 있다.

```python
try:
    data = await fetch_all(client, URLS)
except* TimeoutError as group:
    log.warning("timeouts: %d", len(group.exceptions))
```

## 정리 코드는 finally에

취소는 `CancelledError` 예외로 전달되므로, 연결 반환 같은 정리 작업은 반드시 `finally` 블록에 두어야 한다. 정리 작업 안에서 다시 `await`를 쓰는 경우에는 그 작업도 취소될 수 있다는 점을 고려해야 한다.

- 연결 반환과 파일 닫기는 `finally`에서 처리한다.
- `CancelledError`를 잡았다면 반드시 다시 던진다.
- 시간 제한은 `asyncio.timeout()`으로 그룹 바깥에서 건다.

> 주의: `CancelledError`를 잡고 다시 던지지 않으면 TaskGroup이 취소를 완료하지 못하고 멈출 수 있다. 이 글의 예시는 Python 3.11 이상에서만 동작한다.

## 시간 제한 걸기

그룹 전체에 시간 제한을 걸 때는 `async with asyncio.timeout(5):` 블록 안에 TaskGroup을 둔다. 시간이 다 되면 그룹 안의 모든 작업이 취소되고, 바깥에서는 `TimeoutError` 하나만 받는다. 작업마다 다른 제한이 필요하면 각 코루틴 안에서 따로 `asyncio.timeout()`을 건다.

## 결과

가상의 집계 서버에서 이 방식으로 바꾼 뒤 한 작업이 실패하면 나머지 호출이 즉시 중단되었고, 연결 풀 고갈 문제는 재현되지 않았다. 다만 외부 API가 취소 요청을 받은 뒤에도 서버 쪽 처리를 계속하는지는 이 글에서 확인하지 않았다.
