// Unit quiz: one question at a time, graded by the server.
// Choice order is shuffled here for display only; answers are sent as choice ids.
// Before the learner passes, the result shows only the score and which questions were
// wrong. After passing, the server reveals correct answers and explanations.
import { useState } from "react";
import { CheckCircle2, RotateCcw, XCircle } from "lucide-react";
import { fetchUnitQuiz, submitQuiz } from "../../api/progress";
import Markdown from "./Markdown";

function shuffled(items) {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function prepare(quiz) {
  return { ...quiz, questions: quiz.questions.map((q) => ({ ...q, choices: shuffled(q.choices) })) };
}

const newSubmissionId = () => crypto.randomUUID();

export default function QuizPanel({ trackSlug, unitSlug, summary, passed, onResult }) {
  // phase: idle | loading | answering | submitting | result | error
  const [phase, setPhase] = useState("idle");
  const [quiz, setQuiz] = useState(null);
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState({}); // question id -> Set of choice ids
  const [submissionId, setSubmissionId] = useState(null);
  const [result, setResult] = useState(null);
  const [message, setMessage] = useState("");

  const start = async () => {
    setPhase("loading");
    setMessage("");
    try {
      setQuiz(prepare(await fetchUnitQuiz(trackSlug, unitSlug)));
      setIndex(0);
      setAnswers({});
      setResult(null);
      setSubmissionId(newSubmissionId());
      setPhase("answering");
    } catch {
      setMessage("퀴즈를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.");
      setPhase("error");
    }
  };

  const retry = () => {
    setQuiz((current) => prepare(current));
    setIndex(0);
    setAnswers({});
    setResult(null);
    setSubmissionId(newSubmissionId());
    setPhase("answering");
  };

  const toggle = (question, choiceId) => {
    setAnswers((prev) => {
      const picked = new Set(question.type === "single" ? [] : prev[question.id] ?? []);
      if (question.type === "multiple" && picked.has(choiceId)) picked.delete(choiceId);
      else picked.add(choiceId);
      return { ...prev, [question.id]: picked };
    });
  };

  const submit = async () => {
    setPhase("submitting");
    setMessage("");
    const payload = quiz.questions.map((q) => ({ question_id: q.id, choice_ids: [...(answers[q.id] ?? [])] }));
    try {
      const data = await submitQuiz(quiz.id, submissionId, payload);
      setResult(data);
      setPhase("result");
      onResult(data);
    } catch (error) {
      if (error.code === "QUIZ_RETIRED") {
        setMessage("퀴즈가 새 버전으로 바뀌었습니다. 다시 불러와 주세요.");
        setPhase("error");
      } else if (error.status) {
        setMessage("답안을 제출하지 못했습니다. 퀴즈를 다시 불러와 주세요.");
        setPhase("error");
      } else {
        // Network failure: the answer may or may not have reached the server, so the
        // retry keeps the same submission id and is graded at most once.
        setMessage("네트워크 오류로 제출을 확인하지 못했습니다. 다시 제출해 주세요.");
        setPhase("answering");
      }
    }
  };

  const questionCount = summary.question_count;

  return (
    <section className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6" aria-labelledby="quiz-title">
      <header className="flex items-center justify-between mb-4">
        <h2 id="quiz-title" className="font-bold text-lg">
          단원 퀴즈
        </h2>
        {passed ? (
          <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-md bg-emerald-100 text-emerald-700">
            <CheckCircle2 size={12} /> 통과
          </span>
        ) : (
          <span className="text-xs text-slate-500">
            {questionCount}문항 · {summary.pass_score_percent}% 이상 통과
          </span>
        )}
      </header>

      {(phase === "idle" || phase === "error") && (
        <div>
          {message && <p className="text-sm text-rose-600 mb-3">{message}</p>}
          <p className="text-sm text-slate-600 mb-4">
            {passed
              ? "이미 통과한 퀴즈입니다. 복습 삼아 다시 풀어도 XP는 추가되지 않습니다."
              : "필수 활동 확인과 퀴즈 통과를 모두 마치면 단원이 완료됩니다. 재도전은 횟수 제한이 없습니다."}
          </p>
          <button
            onClick={start}
            className="px-5 py-2.5 rounded-xl bg-indigo-600 text-white font-semibold hover:bg-indigo-700"
          >
            {phase === "error" ? "퀴즈 다시 불러오기" : passed ? "다시 풀어보기" : "퀴즈 풀기"}
          </button>
        </div>
      )}

      {phase === "loading" && <p className="text-slate-400">퀴즈를 불러오는 중...</p>}

      {(phase === "answering" || phase === "submitting") && quiz && (
        <QuestionStep
          question={quiz.questions[index]}
          index={index}
          total={quiz.questions.length}
          picked={answers[quiz.questions[index].id] ?? new Set()}
          onToggle={toggle}
          onPrev={() => setIndex((i) => i - 1)}
          onNext={() => setIndex((i) => i + 1)}
          onSubmit={submit}
          submitting={phase === "submitting"}
          message={message}
        />
      )}

      {phase === "result" && result && <QuizResultView quiz={quiz} result={result} onRetry={retry} />}
    </section>
  );
}

function QuestionStep({ question, index, total, picked, onToggle, onPrev, onNext, onSubmit, submitting, message }) {
  const last = index === total - 1;
  const multiple = question.type === "multiple";
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <span className="text-xs font-bold text-indigo-600 bg-indigo-50 px-3 py-1 rounded-full">
          Q{index + 1} / {total}
        </span>
        {multiple && <span className="text-xs text-slate-500">정답을 모두 고르세요</span>}
      </div>
      <div className="font-semibold mb-4">
        <Markdown>{question.prompt}</Markdown>
      </div>

      <div className="space-y-2" role={multiple ? "group" : "radiogroup"} aria-label={`Q${index + 1} 보기`}>
        {question.choices.map((choice) => {
          const selected = picked.has(choice.id);
          return (
            <button
              key={choice.id}
              type="button"
              role={multiple ? "checkbox" : "radio"}
              aria-checked={selected}
              onClick={() => onToggle(question, choice.id)}
              className={`w-full text-left px-4 py-3 rounded-xl border font-medium transition ${
                selected
                  ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                  : "border-slate-200 text-slate-700 hover:border-indigo-300"
              }`}
            >
              <span className="font-mono text-sm">{choice.label}</span>
            </button>
          );
        })}
      </div>

      {message && <p className="text-sm text-rose-600 mt-4">{message}</p>}

      <div className="flex justify-between mt-6">
        <button
          type="button"
          onClick={onPrev}
          disabled={index === 0 || submitting}
          className="px-4 py-2 rounded-lg border border-slate-200 text-sm font-semibold disabled:opacity-40"
        >
          이전
        </button>
        {last ? (
          <button
            type="button"
            onClick={onSubmit}
            disabled={picked.size === 0 || submitting}
            className="px-5 py-2 rounded-lg bg-indigo-600 text-white text-sm font-semibold disabled:opacity-40"
          >
            {submitting ? "채점 중..." : "제출하기"}
          </button>
        ) : (
          <button
            type="button"
            onClick={onNext}
            disabled={picked.size === 0}
            className="px-5 py-2 rounded-lg bg-indigo-600 text-white text-sm font-semibold disabled:opacity-40"
          >
            다음
          </button>
        )}
      </div>
    </div>
  );
}

function QuizResultView({ quiz, result, onRetry }) {
  const numberOf = new Map(quiz.questions.map((q, i) => [q.id, i + 1]));
  const wrong = result.feedback.filter((f) => !f.correct).map((f) => numberOf.get(f.question_id));
  const feedbackOf = new Map(result.feedback.map((f) => [f.question_id, f]));

  return (
    <div>
      <div className={`rounded-xl p-5 mb-5 ${result.passed ? "bg-emerald-50" : "bg-rose-50"}`}>
        <p className="flex items-center gap-2 font-bold text-lg">
          {result.passed ? (
            <CheckCircle2 className="text-emerald-600" size={22} />
          ) : (
            <XCircle className="text-rose-600" size={22} />
          )}
          {result.passed ? "통과했습니다!" : "아쉽게도 통과하지 못했습니다"}
        </p>
        <p className="text-sm text-slate-600 mt-1">
          {result.max_score}문항 중 {result.score}문항 정답 ({result.score_percent}점 / 통과 기준{" "}
          {result.pass_score_percent}점)
        </p>
        {wrong.length > 0 && (
          <p className="text-sm text-slate-600 mt-1">틀린 문항: {wrong.map((n) => `Q${n}`).join(", ")}</p>
        )}
      </div>

      {result.answers_revealed ? (
        <ol className="space-y-4 mb-5">
          {quiz.questions.map((q, i) => {
            const feedback = feedbackOf.get(q.id);
            const correctIds = new Set(feedback?.correct_choice_ids ?? []);
            return (
              <li key={q.id} className="border border-slate-100 rounded-xl p-4">
                <p className="text-xs font-bold text-slate-500 mb-1">
                  Q{i + 1} {feedback?.correct ? "· 정답" : "· 오답"}
                </p>
                <Markdown>{q.prompt}</Markdown>
                <p className="text-sm mt-2">
                  <span className="font-semibold">정답: </span>
                  <span className="font-mono">
                    {q.choices
                      .filter((c) => correctIds.has(c.id))
                      .map((c) => c.label)
                      .join(", ")}
                  </span>
                </p>
                {feedback?.explanation && (
                  <div className="text-sm mt-2 bg-slate-50 rounded-lg px-3 py-1">
                    <Markdown>{feedback.explanation}</Markdown>
                  </div>
                )}
              </li>
            );
          })}
        </ol>
      ) : (
        <p className="text-sm text-slate-500 mb-5">정답과 해설은 퀴즈를 통과하면 공개됩니다.</p>
      )}

      <button
        type="button"
        onClick={onRetry}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-200 text-sm font-semibold"
      >
        <RotateCcw size={14} /> 다시 풀기
      </button>
    </div>
  );
}
