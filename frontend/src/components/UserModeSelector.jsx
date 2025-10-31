import { useNavigate } from "react-router-dom";

export default function UserModeSelector() {
  const navigate = useNavigate();
  return (
    <div className="mt-16 flex flex-col md:flex-row justify-center gap-6 text-center">
      <button
        onClick={() => navigate("/career")}
        className="bg-blue-100 text-blue-700 px-6 py-3 rounded-xl hover:bg-blue-200 transition"
      >
        💼 취준생용 보기
      </button>
      <button
        onClick={() => navigate("/developer")}
        className="bg-indigo-100 text-indigo-700 px-6 py-3 rounded-xl hover:bg-indigo-200 transition"
      >
        💻 개발자용 보기
      </button>
    </div>
  );
}
