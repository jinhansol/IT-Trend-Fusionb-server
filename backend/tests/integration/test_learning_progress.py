"""Activity confirmation, quiz grading, unit completion and XP against MariaDB."""

import threading
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.content_loader.loader import apply_track
from app.content_loader.schema import read_track_directory
from app.db.session import create_session_factory
from app.main import create_app
from app.models.user import User
from app.schemas.progress import QuizSubmission
from app.services import learning_progress, rewards
from tests.content_helpers import activity, question, quiz, unit, write_track

pytestmark = pytest.mark.integration

# Unit "one": two required activities, one optional; 2-question quiz, 80% to pass
# (so both answers must be right). q1 single -> "b", q2 multiple -> "a" + "c".
UNIT_ONE = unit(
    "one",
    1,
    activities=[activity("read-a"), activity("read-b"), activity("extra", required=False)],
    quiz=quiz([question("q1"), question("q2", type="multiple", correct=("a", "c"))]),
)
UNIT_TWO = unit("two", 2, quiz=quiz([question("q1")]))


def load(engine, directory):
    session = create_session_factory(engine)()
    try:
        apply_track(session, read_track_directory(directory))
        session.commit()
    finally:
        session.close()


@pytest.fixture()
def app(clean_db, integration_settings, tmp_path):
    load(clean_db, write_track(tmp_path, slug="py", units=[UNIT_ONE, UNIT_TWO]))
    return create_app(integration_settings)


@pytest.fixture()
def client(app):
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


class Learner:
    """A registered user plus helpers that talk to the API with their token."""

    def __init__(self, client, email):
        response = client.post(
            "/api/auth/register",
            json={"email": email, "password": "correct horse 1", "display_name": email[:5]},
        )
        assert response.status_code == 201, response.text
        self.client = client
        self.id = response.json()["user"]["id"]
        self.headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    def get(self, path):
        return self.client.get(path, headers=self.headers)

    def post(self, path, json=None):
        return self.client.post(path, json=json, headers=self.headers)

    def confirm(self, activity_id):
        return self.post(f"/api/me/activities/{activity_id}/confirm")

    def submit(self, quiz_id, answers, submission_id=None):
        return self.post(
            f"/api/me/quizzes/{quiz_id}/attempts",
            {"client_submission_id": submission_id or str(uuid.uuid4()), "answers": answers},
        )

    def unit_progress(self, unit_slug="one"):
        return self.get(f"/api/me/tracks/py/units/{unit_slug}/progress").json()

    def summary(self):
        return self.get("/api/me/summary").json()


def unit_info(client, unit_slug="one"):
    detail = client.get(f"/api/tracks/py/units/{unit_slug}").json()
    quiz_out = client.get(f"/api/tracks/py/units/{unit_slug}/quiz").json()
    activities = {a["slug"]: a["id"] for a in detail["activities"]}
    questions = {
        f"q{q['position']}": {
            "id": q["id"],
            "choices": {c["label"].split()[-1]: c["id"] for c in q["choices"]},
        }
        for q in quiz_out["questions"]
    }
    return activities, quiz_out["id"], questions


def answers(questions, q1=("b",), q2=("a", "c")):
    picked = {"q1": q1, "q2": q2}
    return [
        {"question_id": q["id"], "choice_ids": [q["choices"][k] for k in picked[key]]}
        for key, q in questions.items()
    ]


def xp_rows(engine, user_id):
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT amount, reason, idempotency_key FROM xp_ledger WHERE user_id = :u"),
            {"u": user_id},
        ).all()


# --- completion rule ---------------------------------------------------------------------


def test_activities_only_or_quiz_only_do_not_complete(client, clean_db):
    activities, quiz_id, questions = unit_info(client)

    only_activities = Learner(client, "acts@example.com")
    only_activities.confirm(activities["read-a"])
    body = only_activities.confirm(activities["read-b"]).json()
    assert body["progress"]["state"] == "in_progress"
    assert body["progress"]["activities_done"] == 2 and body["granted_rewards"] == []

    only_quiz = Learner(client, "quiz@example.com")
    result = only_quiz.submit(quiz_id, answers(questions)).json()
    assert result["passed"] is True
    assert result["progress"]["state"] == "in_progress"
    assert result["granted_rewards"] == []

    assert xp_rows(clean_db, only_activities.id) == [] and xp_rows(clean_db, only_quiz.id) == []


def test_activities_then_quiz_completes_once_with_xp(client, clean_db):
    activities, quiz_id, questions = unit_info(client)
    learner = Learner(client, "a@example.com")
    learner.confirm(activities["read-a"])
    learner.confirm(activities["read-b"])  # optional "extra" is not needed

    result = learner.submit(quiz_id, answers(questions)).json()
    assert result["progress"]["state"] == "completed"
    assert result["granted_rewards"] == [{"amount": 100, "reason": "unit_completed"}]
    assert result["xp"] == {"total": 100, "level": 2, "xp_into_level": 0, "xp_for_next_level": 150}

    # Passing again or re-confirming never pays twice.
    again = learner.submit(quiz_id, answers(questions)).json()
    assert again["granted_rewards"] == [] and again["xp"]["total"] == 100
    assert learner.confirm(activities["read-a"]).json()["granted_rewards"] == []
    assert len(xp_rows(clean_db, learner.id)) == 1


def test_quiz_then_activities_completes_on_the_last_activity(client, clean_db):
    activities, quiz_id, questions = unit_info(client)
    learner = Learner(client, "b@example.com")
    learner.submit(quiz_id, answers(questions))
    assert learner.confirm(activities["read-a"]).json()["progress"]["state"] == "in_progress"

    last = learner.confirm(activities["read-b"]).json()
    assert last["progress"]["state"] == "completed"
    assert last["granted_rewards"] == [{"amount": 100, "reason": "unit_completed"}]


# --- grading and answer disclosure -------------------------------------------------------


def test_failed_attempt_hides_answers_until_passed(client, clean_db):
    _, quiz_id, questions = unit_info(client)
    learner = Learner(client, "c@example.com")

    failed = learner.submit(quiz_id, answers(questions, q2=("a",))).json()
    assert (failed["score"], failed["max_score"], failed["score_percent"]) == (1, 2, 50)
    assert failed["passed"] is False and failed["answers_revealed"] is False
    assert [f["correct"] for f in failed["feedback"]] == [True, False]
    assert all(f["correct_choice_ids"] is None for f in failed["feedback"])
    assert all(f["explanation"] is None for f in failed["feedback"])

    passed = learner.submit(quiz_id, answers(questions)).json()
    assert passed["passed"] is True and passed["answers_revealed"] is True
    q2 = questions["q2"]["choices"]
    assert passed["feedback"][1]["correct_choice_ids"] == sorted([q2["a"], q2["c"]])
    assert passed["feedback"][1]["explanation"] == "Because."

    progress = learner.unit_progress()
    assert progress["quiz"] == {"passed": True, "attempts": 2, "best_score_percent": 100}


def test_public_quiz_never_contains_answers(client, clean_db):
    raw = client.get("/api/tracks/py/units/one/quiz").text
    for leaked in ("is_correct", "correct", "explanation", "Because."):
        assert leaked not in raw
    detail = client.get("/api/tracks/py/units/one").json()
    assert detail["quiz"]["question_count"] == 2 and detail["quiz"]["pass_score_percent"] == 80


@pytest.mark.parametrize(
    "mutate",
    [
        lambda q, o: [{"question_id": o["q1"]["id"], "choice_ids": [o["q1"]["choices"]["b"]]}],
        lambda q, o: [{"question_id": q["q1"]["id"], "choice_ids": [q["q2"]["choices"]["a"]]}],
        lambda q, o: [
            {"question_id": q["q1"]["id"], "choice_ids": list(q["q1"]["choices"].values())[:2]}
        ],
        lambda q, o: [{"question_id": q["q2"]["id"], "choice_ids": []}],
        lambda q, o: answers(q) + answers(q)[:1],
    ],
    ids=["other-quiz", "foreign-choice", "single-two-choices", "multiple-empty", "duplicate"],
)
def test_invalid_answers_are_rejected_without_recording(client, clean_db, mutate):
    _, quiz_id, questions = unit_info(client)
    _, _, other_questions = unit_info(client, "two")
    learner = Learner(client, "d@example.com")

    response = learner.submit(quiz_id, mutate(questions, other_questions))
    assert response.status_code == 422
    assert response.json()["error"]["code"] in ("INVALID_ANSWER", "VALIDATION_ERROR")
    assert learner.unit_progress()["quiz"]["attempts"] == 0


# --- idempotency, concurrency, rollback --------------------------------------------------


def test_resubmitting_the_same_submission_returns_the_same_attempt(client, clean_db):
    activities, quiz_id, questions = unit_info(client)
    learner = Learner(client, "e@example.com")
    learner.confirm(activities["read-a"])
    learner.confirm(activities["read-b"])
    submission_id = str(uuid.uuid4())

    first = learner.submit(quiz_id, answers(questions), submission_id).json()
    retry = learner.submit(quiz_id, answers(questions), submission_id).json()
    assert retry["attempt_id"] == first["attempt_id"]
    assert first["granted_rewards"] and retry["granted_rewards"] == []
    assert learner.unit_progress()["quiz"]["attempts"] == 1

    _, other_quiz, other_questions = unit_info(client, "two")
    reused = learner.submit(other_quiz, answers(other_questions)[:1], submission_id)
    assert reused.status_code == 409
    assert reused.json()["error"]["code"] == "SUBMISSION_ID_REUSED"


def test_concurrent_passing_submissions_pay_exactly_once(app, client, clean_db):
    activities, quiz_id, questions = unit_info(client)
    learner = Learner(client, "f@example.com")
    learner.confirm(activities["read-a"])
    learner.confirm(activities["read-b"])

    barrier = threading.Barrier(4)
    granted, errors = [], []

    def submit():
        db = app.state.session_factory()
        try:
            user = db.get(User, learner.id)
            db.commit()
            barrier.wait()
            result = learning_progress.submit_quiz(
                db,
                app.state.settings,
                user,
                quiz_id,
                QuizSubmission(client_submission_id=str(uuid.uuid4()), answers=answers(questions)),
            )
            granted.extend(result.granted_rewards)
        except Exception as exc:  # pragma: no cover - reported below
            errors.append(exc)
        finally:
            db.close()

    threads = [threading.Thread(target=submit) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert errors == []
    assert len(granted) == 1
    assert len(xp_rows(clean_db, learner.id)) == 1
    assert learner.unit_progress()["quiz"]["attempts"] == 4


def test_concurrent_confirmations_create_one_record(app, client, clean_db):
    activities, _, _ = unit_info(client)
    learner = Learner(client, "g@example.com")
    barrier = threading.Barrier(3)
    errors = []

    def confirm():
        db = app.state.session_factory()
        try:
            user = db.get(User, learner.id)
            db.commit()
            barrier.wait()
            learning_progress.confirm_activity(db, app.state.settings, user, activities["read-a"])
        except Exception as exc:  # pragma: no cover - reported below
            errors.append(exc)
        finally:
            db.close()

    threads = [threading.Thread(target=confirm) for _ in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert errors == []
    with clean_db.connect() as connection:
        count = connection.execute(
            text("SELECT COUNT(*) FROM user_activity_records WHERE user_id = :u"), {"u": learner.id}
        ).scalar()
    assert count == 1


def test_failure_while_granting_rolls_back_everything(client, clean_db, monkeypatch):
    activities, quiz_id, questions = unit_info(client)
    learner = Learner(client, "h@example.com")
    learner.confirm(activities["read-a"])
    learner.confirm(activities["read-b"])

    def broken_grant(*args, **kwargs):
        raise RuntimeError("ledger unavailable")

    monkeypatch.setattr(rewards, "grant_once", broken_grant)
    response = learner.submit(quiz_id, answers(questions))
    assert response.status_code == 500

    progress = learner.unit_progress()
    assert progress["quiz"]["attempts"] == 0  # the attempt was rolled back too
    assert progress["progress"]["state"] == "in_progress"
    assert progress["progress"]["quiz_passed"] is False
    assert xp_rows(clean_db, learner.id) == []


# --- isolation, auth, restoration, summary ----------------------------------------------


def test_learners_are_isolated(client, clean_db):
    activities, quiz_id, questions = unit_info(client)
    alice = Learner(client, "alice@example.com")
    bob = Learner(client, "bob@example.com")
    alice.confirm(activities["read-a"])
    alice.confirm(activities["read-b"])
    alice.submit(quiz_id, answers(questions))

    assert alice.unit_progress()["progress"]["state"] == "completed"
    bob_view = bob.unit_progress()
    assert bob_view["progress"]["state"] == "not_started"
    assert bob_view["confirmed_activity_ids"] == [] and bob_view["quiz"]["attempts"] == 0
    assert bob.summary()["xp"]["total"] == 0


def test_personal_endpoints_require_login(client, clean_db):
    activities, quiz_id, _ = unit_info(client)
    for method, path in [
        ("get", "/api/me/summary"),
        ("get", "/api/me/tracks/py/progress"),
        ("get", "/api/me/tracks/py/units/one/progress"),
        ("post", f"/api/me/activities/{activities['read-a']}/confirm"),
        ("post", f"/api/me/quizzes/{quiz_id}/attempts"),
    ]:
        assert getattr(client, method)(path).status_code == 401, path


def test_progress_survives_logging_in_again(client, clean_db):
    activities, quiz_id, questions = unit_info(client)
    learner = Learner(client, "i@example.com")
    learner.confirm(activities["read-a"])
    learner.confirm(activities["read-b"])
    learner.submit(quiz_id, answers(questions))

    login = client.post(
        "/api/auth/login", json={"email": "i@example.com", "password": "correct horse 1"}
    ).json()
    fresh = {"Authorization": f"Bearer {login['access_token']}"}
    summary = client.get("/api/me/summary", headers=fresh).json()
    assert summary["completed_units"] == 1 and summary["xp"]["level"] == 2
    track = client.get("/api/me/tracks/py/progress", headers=fresh).json()
    assert [u["state"] for u in track["units"]] == ["completed", "not_started"]


def test_summary_points_to_the_most_recent_unfinished_unit(client, clean_db):
    activities, _, _ = unit_info(client)
    other_activities, _, _ = unit_info(client, "two")
    learner = Learner(client, "j@example.com")
    assert learner.summary()["continue_unit"] is None

    learner.confirm(activities["read-a"])
    learner.confirm(other_activities["read-intro"])
    summary = learner.summary()
    assert summary["in_progress_units"] == 2
    assert summary["continue_unit"]["unit_slug"] == "two"
    assert summary["continue_unit"]["activities_required"] == 1


def test_updated_quiz_rejects_old_version_but_keeps_completion(client, clean_db, tmp_path):
    activities, quiz_id, questions = unit_info(client)
    learner = Learner(client, "k@example.com")
    learner.confirm(activities["read-a"])
    learner.confirm(activities["read-b"])
    learner.submit(quiz_id, answers(questions))

    changed = dict(UNIT_ONE, quiz=quiz([question("q1"), question("q2"), question("q3")]))
    load(clean_db, write_track(tmp_path, slug="py", units=[changed, UNIT_TWO]))

    stale = learner.submit(quiz_id, answers(questions))
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "QUIZ_RETIRED"
    assert learner.unit_progress()["progress"]["state"] == "completed"
    assert client.get("/api/tracks/py/units/one/quiz").json()["version"] == 2
