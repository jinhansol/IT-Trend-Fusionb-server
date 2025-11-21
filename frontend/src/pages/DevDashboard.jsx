// src/pages/DevDashboard.jsx
import React, { useEffect, useState } from "react";
import { fetchDevFeed } from "../api/devAPI";

/* 재사용 Card */
const Card = ({ title, children }) => (
  <div className="bg-white p-6 rounded-2xl shadow w-full">
    <h2 className="text-lg font-semibold mb-4 text-gray-800">{title}</h2>
    {children}
  </div>
);

/* Velog Item */
const VelogItem = ({ post }) => (
  <li className="border-b pb-3 last:border-none">
    <a
      href={post.url}
      target="_blank"
      rel="noreferrer"
      className="text-emerald-600 font-semibold"
    >
      {post.title}
    </a>
    <p className="text-gray-500 text-sm mt-1">{post.summary}</p>
  </li>
);

/* GitHub Repo Item */
const RepoItem = ({ repo }) => (
  <li className="border-b pb-4 last:border-none">
    <div className="flex justify-between items-center">
      <a
        href={repo.url}
        target="_blank"
        rel="noreferrer"
        className="font-semibold text-blue-600 hover:underline"
      >
        {repo.full_name}
      </a>
      <span className="text-yellow-500 font-medium">⭐ {repo.stars}</span>
    </div>

    {repo.description && (
      <p className="text-gray-700 text-sm mt-2 leading-snug">{repo.description}</p>
    )}
  </li>
);

export default function DevDashboard() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState({
    mode: "public",
    velog_trending: [],
    velog_tags: [],
    github_trending: [],
    velog_recommended: [],
    velog_interest_match: [],
    github_recommended: [],
  });

  useEffect(() => {
    async function loadFeed() {
      setLoading(true);
      const feed = await fetchDevFeed();
      setData(feed);
      setLoading(false);
    }
    loadFeed();
  }, []);

  if (loading)
    return (
      <div className="flex justify-center items-center h-screen text-gray-500">
        Loading Dev Dashboard...
      </div>
    );

  const isPublic = data.mode === "public";

  return (
    <div className="p-8 bg-gray-50 min-h-screen">

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800">Dev Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">
          Mode:{" "}
          <span className="font-semibold text-emerald-600">
            {data.mode}
          </span>
        </p>
      </div>

      {/* Grid Layout */}
      <div className="grid grid-cols-3 gap-6">

        {/* Left Panel */}
        <div className="col-span-2 space-y-6">
          {isPublic ? (
            <>
              <Card title="🔥 Velog Trending">
                <ul className="space-y-3">
                  {data.velog_trending.map((post, i) => (
                    <VelogItem key={i} post={post} />
                  ))}
                </ul>
              </Card>

              <Card title="⭐ GitHub Trending">
                <ul className="space-y-4">
                  {data.github_trending.map((repo, i) => (
                    <RepoItem key={i} repo={repo} />
                  ))}
                </ul>
              </Card>
            </>
          ) : (
            <>
              <Card title="📝 관심사 기반 추천 글">
                <ul className="space-y-3">
                  {data.velog_interest_match.map((post, i) => (
                    <VelogItem key={i} post={post} />
                  ))}
                </ul>
              </Card>

              <Card title="✨ 개인 RSS 기반 추천 글">
                <ul className="space-y-3">
                  {data.velog_recommended.map((post, i) => (
                    <VelogItem key={i} post={post} />
                  ))}
                </ul>
              </Card>

              <Card title="🔧 GitHub 추천 프로젝트">
                <ul className="space-y-4">
                  {data.github_recommended.map((repo, i) => (
                    <RepoItem key={i} repo={repo} />
                  ))}
                </ul>
              </Card>

              <Card title="🔥 GitHub Trending (참고용)">
                <ul className="space-y-4">
                  {data.github_trending.map((repo, i) => (
                    <RepoItem key={i} repo={repo} />
                  ))}
                </ul>
              </Card>
            </>
          )}
        </div>

        {/* Right Sidebar */}
        <div className="space-y-6">
          {isPublic ? (
            <Card title="🏷 인기 태그">
              <ul className="space-y-2">
                {data.velog_tags.map((tag, i) => (
                  <li
                    key={i}
                    className="flex justify-between border-b pb-2 last:border-none"
                  >
                    <span>#{tag.tag}</span>
                    <span className="text-gray-400">{tag.count}</span>
                  </li>
                ))}
              </ul>
            </Card>
          ) : (
            <Card title="🔍 개인화 안내">
              <p className="text-gray-600 text-sm">
                회원님의 관심 키워드를 기반으로  
                Velog & GitHub 최신 콘텐츠를 추천해드리고 있어요.
              </p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
