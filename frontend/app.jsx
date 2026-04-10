const { useState } = React;

const API_BASE = "http://localhost:8000";

function App() {
  return (
    <div className="min-h-screen bg-surface flex items-center justify-center">
      <h1 className="text-3xl font-bold text-secondary">HawkerBoost</h1>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
