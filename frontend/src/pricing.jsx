import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import "./pricing.css";
import PricingPage from "./pages/PricingPage.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <PricingPage />
  </StrictMode>,
);
