import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "../pages/Home";
import DevDashboard from "../pages/DevDashboard";
import HeaderNav from "../components/common/HeaderNav";
import CareerHomePage from "../pages/career/CareerHomePage";
import TrackPage from "../pages/career/TrackPage";
import UnitPage from "../pages/career/UnitPage";


export default function AppRouter() {
  return (
    <BrowserRouter>
      <HeaderNav />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/dev" element={<DevDashboard />} />
        {/* DevHub 2.0 Career hub. The v1 CareerDashboard (legacy backend) is no longer routed. */}
        <Route path="/career" element={<CareerHomePage />} />
        <Route path="/career/:trackSlug" element={<TrackPage />} />
        <Route path="/career/:trackSlug/:unitSlug" element={<UnitPage />} />

      </Routes>
    </BrowserRouter>
  );
}