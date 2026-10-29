import { BrowserRouter, Routes, Route } from "react-router-dom";
import HomePage from "../pages/home/HomePage";
import DevPage from "../pages/dev/DevPage";
import HeaderNav from "../components/common/HeaderNav";
import CareerHomePage from "../pages/career/CareerHomePage";
import TrackPage from "../pages/career/TrackPage";
import UnitPage from "../pages/career/UnitPage";
import SettingsPage from "../pages/settings/SettingsPage";


export default function AppRouter() {
  return (
    <BrowserRouter>
      <HeaderNav />
      <Routes>
        {/* DevHub 2.0 Home and Dev. The v1 Home/DevDashboard (legacy backend) are no longer routed. */}
        <Route path="/" element={<HomePage />} />
        <Route path="/dev" element={<DevPage />} />
        {/* DevHub 2.0 Career hub. The v1 CareerDashboard (legacy backend) is no longer routed. */}
        <Route path="/career" element={<CareerHomePage />} />
        <Route path="/career/:trackSlug" element={<TrackPage />} />
        <Route path="/career/:trackSlug/:unitSlug" element={<UnitPage />} />
        <Route path="/settings" element={<SettingsPage />} />

      </Routes>
    </BrowserRouter>
  );
}