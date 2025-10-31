import AppRouter from "./router/AppRouter";
import "./App.css";

function App() {
  // AppRouter 안에 BrowserRouter가 들어 있어서
  // 모든 페이지(Home, Career, Developer 등)에서 useNavigate() 사용 가능
  return <AppRouter />;
}

export default App;
