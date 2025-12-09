// src/components/roadmap/QuizModal.jsx
import React, { useState, useEffect } from "react";
import axios from "axios";
import { X, CheckCircle, AlertCircle } from "lucide-react";

export default function QuizModal({ isOpen, onClose, onFinish }) {
  const [questions, setQuestions] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [score, setScore] = useState(0);
  const [showResult, setShowResult] = useState(false);
  const [loading, setLoading] = useState(false);

  // 퀴즈 데이터 로드
  useEffect(() => {
    if (isOpen) {
      setLoading(true);
      // 백엔드 API 호출 (없으면 더미 데이터 사용)
      axios.get("http://localhost:8000/api/quiz/generate")
        .then(res => {
            setQuestions(res.data.questions);
            setLoading(false);
        })
        .catch(() => {
            // API가 아직 없을 때를 대비한 백업 데이터
            setQuestions([
                { id: 1, q: "HTML의 의미는?", options: ["Hyper Text Markup Language", "High Tech Main Lang", "Hyper Tool Multi Level", "Home Tool Markup"], answer: "Hyper Text Markup Language" },
                { id: 2, q: "React는 무엇인가?", options: ["Database", "Library", "Operating System", "Browser"], answer: "Library" },
            ]);
            setLoading(false);
        });
      
      // 초기화
      setCurrentIndex(0);
      setScore(0);
      setShowResult(false);
    }
  }, [isOpen]);

  const handleAnswer = (option) => {
    const isCorrect = option === questions[currentIndex].answer;
    if (isCorrect) setScore(prev => prev + 1);

    if (currentIndex + 1 < questions.length) {
      setCurrentIndex(prev => prev + 1);
    } else {
      finishQuiz(score + (isCorrect ? 1 : 0));
    }
  };

  const finishQuiz = async (finalScore) => {
    setLoading(true);
    try {
        // 결과 분석 요청
        const res = await axios.post("http://localhost:8000/api/quiz/submit", { score: finalScore });
        onFinish(res.data.stats); // 부모(Dashboard)에 스탯 전달
    } catch (e) {
        console.error(e);
        // 에러 시 더미 스탯 전달
        onFinish([
            { subject: 'Frontend', A: 80, fullMark: 100 },
            { subject: 'Backend', A: 60, fullMark: 100 },
            { subject: 'CS', A: 50, fullMark: 100 },
            { subject: 'AI', A: 40, fullMark: 100 },
            { subject: 'Tools', A: 70, fullMark: 100 },
            { subject: 'Comm', A: 90, fullMark: 100 },
        ]);
    }
    setLoading(false);
    setShowResult(true);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-white w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden relative animate-fade-in-up">
        {/* 닫기 버튼 */}
        <button onClick={onClose} className="absolute top-4 right-4 text-gray-400 hover:text-gray-600">
          <X size={24} />
        </button>

        {loading ? (
          <div className="p-10 text-center">
            <div className="animate-spin w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full mx-auto mb-4"></div>
            <p className="text-gray-500 font-medium">AI가 문제를 생성하고 있습니다...</p>
          </div>
        ) : showResult ? (
          <div className="p-10 text-center">
            <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle size={32} />
            </div>
            <h2 className="text-2xl font-bold text-gray-800 mb-2">진단 완료!</h2>
            <p className="text-gray-500 mb-6">회원님의 개발 능력치가 분석되었습니다.</p>
            <button 
              onClick={onClose}
              className="w-full bg-indigo-600 text-white py-3 rounded-xl font-bold hover:bg-indigo-700 transition"
            >
              결과 확인하기
            </button>
          </div>
        ) : (
          <div className="p-8">
            <div className="flex justify-between items-center mb-6">
              <span className="text-xs font-bold text-indigo-500 bg-indigo-50 px-3 py-1 rounded-full">
                Q{currentIndex + 1} / {questions.length}
              </span>
              <span className="text-xs text-gray-400">Life Coding Test</span>
            </div>

            <h3 className="text-xl font-bold text-gray-800 mb-8 leading-relaxed">
              {questions[currentIndex]?.q}
            </h3>

            <div className="space-y-3">
              {questions[currentIndex]?.options.map((opt, idx) => (
                <button
                  key={idx}
                  onClick={() => handleAnswer(opt)}
                  className="w-full text-left p-4 rounded-xl border border-gray-200 hover:border-indigo-500 hover:bg-indigo-50 hover:text-indigo-700 transition-all font-medium text-gray-600"
                >
                  {opt}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}