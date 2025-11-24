import React, { useEffect, useState } from "react";
import { fetchDevPublic, fetchDevPersonal } from "../api/devAPI";

import DevSidebar from "../components/DevSidebar";

// Section Components
import OkkySection from "../components/OkkySection";
import DevtoSection from "../components/DevtoSection";

export default function DevDashboard() {
  const [feed, setFeed] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState("all");

  const token = localStorage.getItem("token")?.trim();

  useEffect(() => {
    setLoading(true);

    const fetchFeed = async () => {
      try {
        const validToken =
          token && token !== "null" && token !== "undefined";

        if (validToken) {
          try {
            const personal = await fetchDevPersonal();
            setFeed(personal);
          } catch (err) {
            if (err.response?.status === 401) {
              const pub = await fetchDevPublic();
              setFeed(pub);
            } else {
              throw err;
            }
          }
        } else {
          const pub = await fetchDevPublic();
          setFeed(pub);
        }
      } catch (err) {
        console.error("❌ Dev Feed Error:", err);
        setFeed(null);
      } finally {
        setLoading(false);
      }
    };

    fetchFeed();
  }, [token]);

  if (loading) return <p className="p-10 text-gray-500">Loading Dev Dashboard...</p>;
  if (!feed) return <p className="p-10 text-red-500">Failed to load data.</p>;

  return (
    <div className="max-w-7xl mx-auto px-6 py-10 flex gap-8">

      {/* Sidebar */}
      <DevSidebar selected={selected} onSelect={setSelected} />

      {/* Content */}
      <div className="flex-1 space-y-10">

        {/* OKKY SECTION */}
        <section>
          <h2 className="text-xl font-semibold mb-4">OKKY Trending</h2>
          <OkkySection data={feed.okky} filter={selected} />
        </section>

        {/* DEVTO SECTION */}
        <section>
          <h2 className="text-xl font-semibold mb-4">Dev.to Articles</h2>
          <DevtoSection data={feed.devto} filter={selected} />
        </section>

      </div>
    </div>
  );
}
