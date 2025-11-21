// src/pages/DevDashboard.jsx
import React, { useEffect, useState } from "react";
import { fetchPublicDev, fetchPersonalDev } from "../api/devAPI";

export default function DevDashboard() {
  const [mode, setMode] = useState("public");
  const [loading, setLoading] = useState(true);

  const [publicData, setPublicData] = useState({
    github_trending: [],
    velog_trending: [],
    velog_tags: [],
  });

  const [personalData, setPersonalData] = useState({
    tech_stack: [],
    github_updates: [],
    velog_recommended: [],
  });

  const token = localStorage.getItem("token");
  const isLoggedIn = !!token;

  // ================================
  // PUBLIC DATA
  // ================================
  const loadPublic = async () => {
    try {
      const res = await fetchPublicDev();
      setPublicData(res || {});
    } catch (e) {
      console.error("❌ Public Load Error:", e);
    }
  };

  // ================================
  // PERSONAL DATA
  // ================================
  const loadPersonal = async () => {
    try {
      const res = await fetchPersonalDev();
      if (res?.mode === "personal") {
        setMode("personal");
        setPersonalData(res);
      } else {
        setMode("public");
      }
    } catch (e) {
      console.error("❌ Personal Load Error:", e);
      setMode("public");
    }
  };

  // ================================
  // INIT
  // ================================
  useEffect(() => {
    setLoading(true);

    const loadAll = async () => {
      await loadPublic();
      if (isLoggedIn) await loadPersonal();
      setLoading(false);
    };

    loadAll();
  }, []);

  if (loading)
    return (
      <div className="flex justify-center items-center h-screen text-gray-500">
        Loading Dev Dashboard...
      </div>
    );

  const isPublic = mode === "public";

  // ================================
  // REUSABLE CARD
  // ================================
  const Card = ({ title, children }) => (
    <div className="bg-white p-6 rounded-2xl shadow">
      <h2 className="text-lg font-semibold mb-4 text-gray-800">{title}</h2>
      {children}
    </div>
  );

  // ================================
  // RIGHT SIDEBAR
  // ================================
  const RightSidebar = () => {
    if (isPublic) {
      return (
        <Card title="🔥 Popular Velog Tags">
          <ul className="space-y-2">
            {(publicData.velog_tags || []).map((tag, i) => (
              <li
                key={i}
                className="flex justify-between border-b pb-2 last:border-0 text-sm"
              >
                <span>#{tag.tag}</span>
                <span className="text-gray-400">{tag.count}</span>
              </li>
            ))}
          </ul>
        </Card>
      );
    }

    return (
      <Card title="📌 Tech Stack Summary">
        {(personalData.tech_stack || []).length === 0 ? (
          <p className="text-gray-500 text-sm">관심 기술을 설정해주세요.</p>
        ) : (
          <ul className="space-y-3">
            {personalData.tech_stack.map((tech, i) => (
              <li
                key={i}
                className="border-b pb-3 last:border-0 text-sm text-gray-700"
              >
                <strong className="text-emerald-600">{tech}</strong> 기반으로
                최신 업데이트를 모아 제공하고 있어요.
              </li>
            ))}
          </ul>
        )}
      </Card>
    );
  };

  // ================================
  // PUBLIC VIEW
  // ================================
  const PublicView = () => (
    <>
      {/* GitHub Trending */}
      <Card title="🔥 GitHub Trending">
        <ul className="space-y-4">
          {(publicData.github_trending || []).map((repo, i) => (
            <li key={i} className="border-b pb-4 last:border-none">
              <div className="flex justify-between items-center">
                <span className="font-medium text-gray-900">
                  {repo.full_name}
                </span>
                <span className="text-yellow-500 font-medium">
                  ⭐ {repo.stars}
                </span>
              </div>

              {/* 기본 1줄 요약 */}
              {repo.summary_kor && (
                <p className="text-gray-800 text-sm bg-gray-100 p-2 rounded mt-2 leading-snug">
                  🇰🇷 {repo.summary_kor}
                </p>
              )}

              {/* README 기반 핵심 요약 */}
              {repo.summary_detail && repo.summary_detail.trim() !== "" && (
                <p className="text-gray-700 text-xs bg-gray-50 border-l-4 border-emerald-500 p-3 rounded mt-2 leading-relaxed whitespace-pre-line">
                  📘 {repo.summary_detail}
                </p>
              )}
            </li>
          ))}
        </ul>
      </Card>

      {/* Velog Trending */}
      <Card title="📝 Velog Trending Posts">
        <ul className="space-y-3">
          {(publicData.velog_trending || []).map((post, i) => (
            <li key={i} className="border-b pb-3 last:border-none">
              <a
                href={post.url}
                target="_blank"
                rel="noreferrer"
                className="text-emerald-600 font-semibold"
              >
                {post.title}
              </a>
              <p className="text-gray-500 text-sm">{post.summary}</p>
            </li>
          ))}
        </ul>
      </Card>
    </>
  );

  // ================================
  // PERSONAL VIEW
  // ================================
  const PersonalView = () => (
    <>
      {/* GitHub Updates */}
      <Card title="🔧 GitHub Updates (Your Tech Stack)">
        <ul className="space-y-3">
          {(personalData.github_updates || []).map((repo, i) => (
            <li key={i} className="border-b pb-3 last:border-none">
              <div className="flex justify-between">
                <span className="font-medium">{repo.full_name}</span>
                <span className="text-yellow-500">⭐ {repo.stars}</span>
              </div>
              <p className="text-gray-500 text-sm">{repo.description}</p>
            </li>
          ))}
        </ul>
      </Card>

      {/* Velog Recommended */}
      <Card title="📝 Recommended Velog Articles">
        <ul className="space-y-3">
          {(personalData.velog_recommended || []).map((post, i) => (
            <li key={i} className="border-b pb-3 last:border-none">
              <a
                href={post.url}
                target="_blank"
                rel="noreferrer"
                className="text-emerald-600 font-semibold"
              >
                {post.title}
              </a>
              <p className="text-gray-500 text-sm">{post.summary}</p>
            </li>
          ))}
        </ul>
      </Card>
    </>
  );

  // ================================
  // FINAL RENDER
  // ================================
  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-800">Dev Dashboard</h1>
        <p className="text-sm text-gray-600">
          Mode:{" "}
          <span className="font-semibold text-emerald-600">
            {isPublic ? "Public" : "Personalized"}
          </span>
        </p>
      </div>

      {/* GRID */}
      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-6">
          {isPublic ? <PublicView /> : <PersonalView />}
        </div>

        <div className="space-y-6">
          <RightSidebar />
        </div>
      </div>
    </div>
  );
}
