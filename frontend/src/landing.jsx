import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import "./landing.css";
import LandingPage from "./pages/LandingPage.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <LandingPage />
  </StrictMode>,
);
