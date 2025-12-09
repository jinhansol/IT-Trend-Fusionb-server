import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "../pages/Home";
import CareerDashboard from "../pages/CareerDashboard";
import DevDashboard from "../pages/DevDashboard";
import HeaderNav from "../components/common/HeaderNav";


export default function AppRouter() {
  return (
    <BrowserRouter>
      <HeaderNav />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/career" element={<CareerDashboard />} />
        <Route path="/dev" element={<DevDashboard />} />

      </Routes>
    </BrowserRouter>
  );
}