import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "../pages/Home";
import CareerDashboard from "../pages/CareerDashboard";
import DevDashboard from "../pages/DevDashboard";
import HeaderNav from "../components/HeaderNav"; // ✅ 변경된 부분

export default function AppRouter() {
  return (
    <BrowserRouter>
      {/* ✅ 모든 페이지 공통 헤더 */}
      <HeaderNav />

      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/career" element={<CareerDashboard />} />
        <Route path="/dev" element={<DevDashboard />} />
        <Route path="/insight" element={<DevDashboard />} /> {/* ✅ 경로명 일관화 */} 
      </Routes>
    </BrowserRouter>
  );
}
