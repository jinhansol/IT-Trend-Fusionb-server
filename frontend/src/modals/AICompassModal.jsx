// src/components/modals/AICompassModal.jsx
import React, { useState, useRef, useEffect } from "react";
import { Send, Rocket, Bot, X, ArrowRight, Eye } from "lucide-react";
import { sendMessage } from "../api/aiAPI";

// ✅ [수정] onPreview prop 추가
export default function AICompassModal({ isOpen, onClose, onPreview }) {
  if (!isOpen) return null;

  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "안녕하세요! AI 커리어 상담가입니다. 🤖\n\nQ1. 무언가를 만들 때 더 희열을 느끼는 순간은 언제인가요?\n\n1️⃣ 내가 짠 코드가 화면에 예쁘게 딱 나타날 때 ✨\n2️⃣ 복잡한 데이터가 착착 정리되어 처리될 때 ⚙️",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    const aiReply = await sendMessage([...messages, userMessage]);
    setMessages((prev) => [...prev, aiReply]);
    setIsLoading(false);
  };

  const renderMessageContent = (content) => {
    let recommendType = null;
    let cleanContent = content;

    if (content.includes("[RECOMMEND: FRONTEND]")) {
        recommendType = "FRONTEND";
        cleanContent = content.replace("[RECOMMEND: FRONTEND]", "");
    } else if (content.includes("[RECOMMEND: BACKEND]")) {
        recommendType = "BACKEND";
        cleanContent = content.replace("[RECOMMEND: BACKEND]", "");
    } else if (content.includes("[RECOMMEND: AI]")) {
        recommendType = "AI";
        cleanContent = content.replace("[RECOMMEND: AI]", "");
    }

    return (
        <div className="flex flex-col gap-3">
            <p className="whitespace-pre-line">{cleanContent}</p>
            {recommendType && (
                <div className="mt-4 p-5 bg-gradient-to-br from-slate-50 to-slate-100 rounded-2xl border border-slate-200 shadow-sm animate-fade-in">
                    <div className="flex items-center gap-2 mb-2">
                        <span className="bg-indigo-100 text-indigo-600 text-xs font-bold px-2 py-1 rounded">AI 분석 완료</span>
                    </div>
                    <h4 className="font-bold text-slate-800 text-lg mb-1">
                        당신은 <span className="text-indigo-600">{recommendType}</span> 개발자 재질!
                    </h4>
                    <p className="text-slate-500 text-xs mb-4">
                        성향에 딱 맞는 커리큘럼을 준비했습니다.<br/>
                        지금 바로 1강을 무료로 체험해보세요.
                    </p>
                    
                    {/* ✅ [수정] 맛보기 버튼 (onPreview 호출) */}
                    <button 
                        onClick={() => onPreview(recommendType)} 
                        className={`w-full py-3.5 rounded-xl font-bold text-white shadow-lg flex items-center justify-center gap-2 transition transform hover:scale-[1.02] active:scale-[0.98]
                            ${recommendType === 'FRONTEND' ? 'bg-gradient-to-r from-pink-500 to-rose-500 hover:from-pink-600' : 
                              recommendType === 'BACKEND' ? 'bg-gradient-to-r from-blue-500 to-indigo-500 hover:from-blue-600' :
                              'bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600'
                            }`}
                    >
                        <Eye size={18} />
                        <span>{recommendType} 로드맵 1강 맛보기</span>
                        <ArrowRight size={16} />
                    </button>
                    <p className="text-[10px] text-center text-slate-400 mt-2">
                        * 이후 단계는 회원가입 후 진행할 수 있습니다.
                    </p>
                </div>
            )}
        </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-white w-full max-w-md h-[600px] rounded-3xl shadow-2xl overflow-hidden flex flex-col relative">
        
        {/* 헤더 */}
        <div className="bg-[#111C44] p-4 flex items-center justify-between text-white shadow-md">
            <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-white/10 rounded-lg flex items-center justify-center">
                    <Rocket size={18} />
                </div>
                <h2 className="font-bold text-lg">AI 커리어 나침반</h2>
            </div>
            <button onClick={onClose} className="p-2 bg-white/10 rounded-full hover:bg-white/20 transition">
                <X size={18} />
            </button>
        </div>

        {/* 채팅 영역 */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#F8FAFC]">
          {messages.map((msg, index) => (
            <div key={index} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              {msg.role === "assistant" && (
                <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center mr-2 shrink-0 mt-1">
                  <Bot size={16} className="text-indigo-600" />
                </div>
              )}
              <div className={`max-w-[85%] p-3.5 rounded-2xl text-sm leading-relaxed shadow-sm ${
                msg.role === "user" 
                  ? "bg-indigo-600 text-white rounded-br-none" 
                  : "bg-white text-slate-800 border border-slate-100 rounded-bl-none"
              }`}>
                {msg.role === "assistant" ? renderMessageContent(msg.content) : msg.content}
              </div>
            </div>
          ))}
          {isLoading && (
             <div className="flex justify-start ml-10">
                <div className="bg-white border border-slate-100 px-4 py-3 rounded-2xl rounded-bl-none shadow-sm flex gap-1 items-center">
                   <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce"></div>
                   <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce delay-100"></div>
                   <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce delay-200"></div>
                </div>
             </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* 입력창 */}
        <div className="p-4 bg-white border-t border-slate-100">
            <form onSubmit={handleSend} className="relative flex items-center">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="답변을 입력하세요..."
                    disabled={isLoading}
                    className="w-full bg-slate-100 border-0 rounded-xl py-3 pl-4 pr-12 focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all text-sm"
                />
                <button
                    type="submit"
                    disabled={!input.trim() || isLoading}
                    className="absolute right-2 top-1/2 -translate-y-1/2 bg-indigo-600 text-white p-1.5 rounded-lg hover:bg-indigo-700 transition disabled:bg-slate-300 disabled:cursor-not-allowed"
                >
                    <Send size={16} />
                </button>
            </form>
        </div>
      </div>
    </div>
  );
}