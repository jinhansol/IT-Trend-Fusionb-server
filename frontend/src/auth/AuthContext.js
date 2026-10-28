import { createContext } from "react";

// { status: "loading" | "anonymous" | "authenticated", user, login, register, logout, reloadUser }
export const AuthContext = createContext(null);
