import { Link } from "react-router-dom";

const NOT_FOUND_CODES = new Set(["TRACK_NOT_FOUND", "UNIT_NOT_FOUND"]);

/** Loading / not-found / error placeholder for learning pages. */
export default function LoadState({ state, notFoundText = "찾을 수 없는 학습 콘텐츠입니다." }) {
  if (state.status === "loading") {
    return <p className="text-center text-slate-400 py-20">불러오는 중...</p>;
  }
  const notFound = NOT_FOUND_CODES.has(state.error?.code);
  return (
    <div className="text-center py-20 space-y-4">
      <p className="text-slate-600">
        {notFound ? notFoundText : "학습 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요."}
      </p>
      <Link to="/career" className="text-indigo-600 font-semibold underline">
        Career로 돌아가기
      </Link>
    </div>
  );
}
