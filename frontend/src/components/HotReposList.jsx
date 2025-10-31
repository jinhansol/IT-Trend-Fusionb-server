// src/components/HotReposList.jsx
import { FaStar } from "react-icons/fa";
import { AiOutlineArrowUp } from "react-icons/ai";

export default function HotReposList({ repos }) {
  return (
    <div className="bg-white p-5 rounded-2xl shadow-sm">
      <div className="flex justify-between items-center mb-3">
        <h2 className="text-lg font-semibold">Hot Open Source Projects</h2>
        <button className="text-blue-600 text-sm font-medium">View All</button>
      </div>

      {repos && repos.length > 0 ? (
        <div className="space-y-4">
          {repos.map((repo) => (
            <div
              key={repo.name}
              className="flex justify-between items-start border-b border-gray-100 pb-3"
            >
              <div>
                <p className="font-semibold text-gray-800">
                  #{repo.rank}{" "}
                  <a
                    href={repo.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-blue-600 transition"
                  >
                    {repo.name}
                  </a>
                </p>
                <p className="text-gray-600 text-sm mt-1">
                  {repo.description || "설명이 없습니다."}
                </p>
              </div>
              <div className="text-right">
                <p className="font-semibold text-yellow-500 flex items-center justify-end">
                  <FaStar className="mr-1" /> {repo.stars}
                </p>
                <p className="text-green-500 text-xs flex items-center justify-end">
                  <AiOutlineArrowUp className="mr-1" /> {repo.growth}
                </p>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-gray-500 text-sm text-center py-4">
          데이터를 불러올 수 없습니다.
        </p>
      )}
    </div>
  );
}
