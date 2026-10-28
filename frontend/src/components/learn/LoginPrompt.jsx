// Asks anonymous visitors to log in where personal progress would appear.
import { useState } from "react";
import LoginPopup from "../../modals/LoginPopup";
import SignupPopup from "../../modals/SignupPopup";

export default function LoginPrompt({ message }) {
  const [popup, setPopup] = useState(null); // "login" | "signup" | null

  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center">
      <p className="text-slate-600 mb-4">{message}</p>
      <div className="flex justify-center gap-3 text-sm font-semibold">
        <button className="px-4 py-2 rounded-lg border border-slate-300 bg-white" onClick={() => setPopup("login")}>
          로그인
        </button>
        <button className="px-4 py-2 rounded-lg bg-emerald-500 text-white" onClick={() => setPopup("signup")}>
          회원가입
        </button>
      </div>

      {popup === "login" && <LoginPopup onClose={() => setPopup(null)} onSwitch={() => setPopup("signup")} />}
      {popup === "signup" && <SignupPopup onClose={() => setPopup(null)} onSwitch={() => setPopup("login")} />}
    </div>
  );
}
