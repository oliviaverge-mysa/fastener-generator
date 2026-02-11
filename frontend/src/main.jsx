import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import App from "./app.jsx"; // or App.jsx — match your file name exactly

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
