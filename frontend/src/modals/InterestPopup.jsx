// src/components/common/InterestPopup.jsx
import React, { useState, useEffect } from "react";
import { Check } from "lucide-react"; 
import { useNavigate } from "react-router-dom"; // ✅ [추가] 페이지 이동 훅

import { saveInterests, getInterests } from "../api/userAPI";
import PopupLayout from "../components/common/PopupLayout";

export default function InterestPopup({ onClose, user, setUser }) {
  const navigate = useNavigate(); // ✅ [추가] 훅 초기화

  const MAX_SELECTION = 7;
  const [selected, setSelected] = useState([]);
  const [mainFocus, setMainFocus] = useState("career");
  const [loading, setLoading] = useState(false);

  // 카테고리 구성
  const sections = [
    {
      title: "Development Fields",
      color: "text-blue-600",
      items: [
        "Frontend", "Backend", "Fullstack", "DevOps", "Security",
        "AI / ML", "Data Eng.", "Cloud", "Game Dev",
        "Mobile App", "Embedded", "Blockchain",
      ],
    },
    {
      title: "Tech Stack",
      color: "text-emerald-600",
      items: [
        "Python", "JavaScript", "TypeScript", "React", "Vue",
        "Next.js", "Node.js", "Spring Boot", "Flask / FastAPI",
        "TensorFlow", "PyTorch", "Docker / K8s", "Java", "C++"
      ],
    },
    {
      title: "Industry & Trends",
      color: "text-purple-600",
      items: [
        "AI Ethics", "Robotics", "Web3", "Startups", "Cloud Trends",
        "Data Privacy", "Open Source", "Productivity", "Sustainability",
      ],
    },
  ];

  // 메인 포커스 옵션
  const focusOptions = [
    { key: "career", label: "Career 🔍" },
    { key: "dev", label: "Development 💻" },
  ];

  // 토글 선택
  const toggleSelection = (item) => {
    if (selected.includes(item)) {
      setSelected(selected.filter((v) => v !== item));
    } else if (selected.length < MAX_SELECTION) {
      setSelected([...selected, item]);
    }
  };

  // 기존 관심사 불러오기
  useEffect(() => {
    if (!user?.id) return;
    const fetchInterests = async () => {
      try {
        const res = await getInterests(user.id);
        if (res) {
            setSelected(res.interests || []);
            if (res.main_focus) setMainFocus(res.main_focus);
        }
      } catch {
        console.log("ℹ️ 저장된 관심사가 없습니다.");
      }
    };
    fetchInterests();
  }, [user]);

  // ✅ 저장 처리 (핵심 수정 부분)
  const handleSave = async () => {
    if (!user?.id) return;
    
    setLoading(true);
    try {
      // 1. 백엔드 저장
      await saveInterests(user.id, selected, mainFocus);

      // 2. 로컬 상태 업데이트
      const updatedUser = { 
          ...user, 
          main_focus: mainFocus,
          interest_topics: selected 
      };
      
      setUser(updatedUser);
      localStorage.setItem("user", JSON.stringify(updatedUser));

      // 3. 🔔 [중요] 대시보드들에게 "데이터 갱신해!"라고 신호 보내기
      window.dispatchEvent(new Event("auth-change"));

      alert("관심사가 저장되었습니다! 맞춤형 정보를 제공해드릴게요.");
      
      // 4. ✅ [핵심] 선택한 분야로 페이지 강제 이동
      if (mainFocus === "career") {
          navigate("/career");
      } else if (mainFocus === "dev") {
          navigate("/dev");
      }

      // 5. 팝업 닫기
      onClose();

    } catch (err) {
      console.error("❌ 관심사 저장 실패:", err);
      alert("저장 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <PopupLayout title={`반가워요, ${user?.username}님! 👋`} onClose={onClose}>
      {/* 스크롤 가능한 컨테이너 */}
      <div className="max-h-[70vh] overflow-y-auto px-1 custom-scrollbar">
        
        {/* 헤더 */}
        <div className="text-center mb-6">
          <p className="text-gray-500 text-sm">
            관심 있는 기술과 분야를 선택해주세요.<br/>
            선택하신 정보를 바탕으로 <strong>Career</strong>와 <strong>Dev</strong> 정보를 추천해드립니다.
          </p>
          <p className="text-emerald-600 text-sm mt-2 font-medium bg-emerald-50 inline-block px-3 py-1 rounded-full">
            {selected.length} / {MAX_SELECTION} 선택됨
          </p>
        </div>

        {/* 메인 포커스 선택 */}
        <div className="mb-8 text-center">
          <p className="font-bold text-gray-700 mb-3 text-sm">가장 관심 있는 분야는?</p>
          <div className="flex justify-center gap-3">
            {focusOptions.map((opt) => (
              <button
                key={opt.key}
                onClick={() => setMainFocus(opt.key)}
                className={`px-4 py-2 rounded-lg border text-sm font-semibold transition-all
                  ${
                    mainFocus === opt.key
                      ? "bg-slate-800 text-white border-slate-800 shadow-md"
                      : "border-gray-200 text-gray-500 hover:border-slate-300 hover:text-slate-600"
                  }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* 관심사 리스트 */}
        <div className="space-y-6 mb-6">
          {sections.map((section, idx) => (
            <div key={idx} className="bg-gray-50/50 rounded-xl p-4 border border-gray-100">
              <div className="flex items-center gap-2 mb-3">
                <span className={`text-sm font-bold uppercase tracking-wider ${section.color}`}>
                  {section.title}
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                {section.items.map((item) => {
                  const isSelected = selected.includes(item);
                  const disabled = !isSelected && selected.length >= MAX_SELECTION;
                  return (
                    <button
                      key={item}
                      onClick={() => toggleSelection(item)}
                      disabled={disabled}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm border transition-all duration-200
                        ${
                          isSelected
                            ? "border-emerald-500 bg-emerald-50 text-emerald-700 font-semibold shadow-sm"
                            : "border-gray-200 bg-white text-gray-600 hover:border-emerald-300 hover:text-emerald-600"
                        }
                        ${disabled ? "opacity-40 cursor-not-allowed" : ""}
                      `}
                    >
                      {isSelected && <Check size={14} strokeWidth={3} />}
                      {item}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* 저장 버튼 */}
        <div className="sticky bottom-0 bg-white pt-2 pb-1 border-t border-gray-100">
            <button
                onClick={handleSave}
                disabled={selected.length === 0 || loading}
                className={`w-full py-3 rounded-xl font-bold text-white transition-all shadow-lg
                ${
                    selected.length > 0 && !loading
                    ? "bg-emerald-600 hover:bg-emerald-700 transform hover:-translate-y-0.5"
                    : "bg-gray-300 cursor-not-allowed"
                }`}
            >
                {loading ? "저장 중..." : "설정 완료 & 시작하기 🚀"}
            </button>
        </div>
      </div>
    </PopupLayout>
  );
}