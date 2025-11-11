import React, { useState, useEffect } from "react";
import { Check } from "lucide-react";
import { saveInterests, getInterests } from "../api/interestAPI";

export default function InterestPopup({ onClose, user, setUser }) {
  const MAX_SELECTION = 7;
  const [selected, setSelected] = useState([]);
  const [mainFocus, setMainFocus] = useState("career");
  const [loading, setLoading] = useState(false);

  // ✅ 카테고리 구성
  const sections = [
    {
      title: "Development Fields",
      color: "text-blue-500",
      items: [
        "Frontend", "Backend", "Fullstack", "DevOps", "Security",
        "AI / ML", "Data Eng.", "Cloud", "Game Dev",
        "Mobile App", "Embedded", "Blockchain",
      ],
    },
    {
      title: "Tech Stack",
      color: "text-emerald-500",
      items: [
        "Python", "JavaScript", "TypeScript", "React", "Vue",
        "Next.js", "Node.js", "Spring Boot", "Flask / FastAPI",
        "TensorFlow", "PyTorch", "Docker / K8s",
      ],
    },
    {
      title: "Industry & Trends",
      color: "text-purple-500",
      items: [
        "AI Ethics", "Robotics", "Web3", "Startups", "Cloud Trends",
        "Data Privacy", "Open Source", "Productivity", "Sustainability",
      ],
    },
  ];

  // ✅ 메인 포커스 옵션
  const focusOptions = [
    { key: "career", label: "Career 🔍" },
    { key: "dev", label: "Development 💻" },
    { key: "insight", label: "AI Insight 🤖" },
  ];

  // ✅ 토글 선택
  const toggleSelection = (item) => {
    if (selected.includes(item)) {
      setSelected(selected.filter((v) => v !== item));
    } else if (selected.length < MAX_SELECTION) {
      setSelected([...selected, item]);
    }
  };

  // ✅ 기존 관심사 불러오기
  useEffect(() => {
    if (!user?.id) return;
    const fetchInterests = async () => {
      try {
        const res = await getInterests(user.id);
        setSelected(res.interests || []);
        if (res.main_focus) setMainFocus(res.main_focus);
      } catch {
        console.log("ℹ️ No saved interests found");
      }
    };
    fetchInterests();
  }, [user]);

  // ✅ 저장 처리
  const handleSave = async () => {
    if (!user?.id) return;
    if (!mainFocus) return alert("메인 관심 분야를 선택해주세요!");
    setLoading(true);
    try {
      // 백엔드 저장
      await saveInterests(user.id, selected, mainFocus);

      // ✅ main_focus를 로컬에도 반영
      const updatedUser = { ...user, main_focus: mainFocus };
      setUser(updatedUser);
      localStorage.setItem("user", JSON.stringify(updatedUser));

      alert("관심사가 저장되었습니다!");
      onClose();
    } catch (err) {
      console.error("❌ 관심사 저장 실패:", err);
      alert("저장 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-gray-900/50 backdrop-blur-sm flex justify-center items-center z-50">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl p-8 overflow-y-auto max-h-[90vh]">
        {/* 헤더 */}
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold text-gray-900">Select Your Interests</h2>
          <p className="text-gray-500 text-sm mt-1">
            Choose your main focus and favorite topics
          </p>
          <p className="text-emerald-600 text-sm mt-1 font-medium">
            {selected.length} of {MAX_SELECTION} selected
          </p>
        </div>

        {/* ✅ 메인 포커스 선택 */}
        <div className="mb-8 text-center">
          <p className="font-medium text-gray-700 mb-3">I’m most interested in...</p>
          <div className="flex justify-center gap-4">
            {focusOptions.map((opt) => (
              <button
                key={opt.key}
                onClick={() => setMainFocus(opt.key)}
                className={`px-5 py-2.5 rounded-lg border text-sm font-semibold transition-all
                  ${
                    mainFocus === opt.key
                      ? "bg-emerald-600 text-white border-emerald-600"
                      : "border-gray-300 text-gray-700 hover:border-emerald-500 hover:text-emerald-600"
                  }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* ✅ 관심사 리스트 */}
        <div className="space-y-6">
          {sections.map((section, idx) => (
            <div key={idx} className="bg-gray-50 rounded-xl p-5 border border-gray-200">
              <div className="flex items-center gap-2 mb-4">
                <span className={`text-lg font-semibold ${section.color}`}>
                  {section.title}
                </span>
              </div>
              <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
                {section.items.map((item) => {
                  const isSelected = selected.includes(item);
                  const disabled = !isSelected && selected.length >= MAX_SELECTION;
                  return (
                    <button
                      key={item}
                      onClick={() => toggleSelection(item)}
                      disabled={disabled}
                      className={`flex items-center justify-center gap-2 px-3 py-2 rounded-md border text-sm font-medium transition-all
                        ${
                          isSelected
                            ? "border-emerald-500 bg-emerald-50 text-emerald-700"
                            : "border-gray-300 text-gray-700 hover:border-gray-400 hover:bg-gray-100"
                        }
                        ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
                    >
                      {isSelected && <Check size={16} className="text-emerald-600" />}
                      {item}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* ✅ 저장 버튼 */}
        <div className="mt-8 text-center">
          <button
            onClick={handleSave}
            disabled={selected.length === 0 || loading}
            className={`px-6 py-2.5 rounded-md font-semibold text-white transition 
              ${
                selected.length > 0 && !loading
                  ? "bg-emerald-600 hover:bg-emerald-700"
                  : "bg-gray-300 cursor-not-allowed"
              }`}
          >
            {loading ? "Saving..." : "Save and Start →"}
          </button>
        </div>
      </div>
    </div>
  );
}
