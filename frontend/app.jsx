const { useState, useRef } = React;

const API_BASE = "http://localhost:8000";

// Screens: "landing", "photo-confirm", "manual-entry", "loading", "results"

function App() {
  const [screen, setScreen] = useState("landing");
  const [stallName, setStallName] = useState("");
  const [cuisineType, setCuisineType] = useState("Chinese");
  const [stallDesc, setStallDesc] = useState("");
  const [dishes, setDishes] = useState([{ name: "", price: "" }]);
  const [imageBase64, setImageBase64] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [results, setResults] = useState(null);
  const [activeLang, setActiveLang] = useState("en");
  const [loadingPhase, setLoadingPhase] = useState("");
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  function reset() {
    setScreen("landing");
    setStallName("");
    setCuisineType("Chinese");
    setStallDesc("");
    setDishes([{ name: "", price: "" }]);
    setImageBase64(null);
    setImagePreview(null);
    setResults(null);
    setActiveLang("en");
    setError(null);
  }

  function handleImageUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    setImagePreview(URL.createObjectURL(file));
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = reader.result.split(",")[1];
      setImageBase64(base64);
      parseMenu(base64);
    };
    reader.readAsDataURL(file);
  }

  async function parseMenu(base64) {
    setScreen("loading");
    setLoadingPhase("Reading your menu...");
    setError(null);
    try {
      const resp = await fetch(`${API_BASE}/api/parse-menu`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_base64: base64 }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();
      if (data.stall_name) setStallName(data.stall_name);
      if (data.cuisine_type) setCuisineType(data.cuisine_type);
      if (data.dishes && data.dishes.length > 0) setDishes(data.dishes);
      setScreen("photo-confirm");
    } catch (err) {
      setError("Couldn't read the menu. Try a clearer photo or enter manually.");
      setScreen("landing");
    }
  }

  async function generateCopy() {
    setScreen("loading");
    setLoadingPhase("Writing your captions in 3 languages...");
    setError(null);
    const validDishes = dishes.filter((d) => d.name.trim());
    if (validDishes.length === 0) {
      setError("Add at least one dish.");
      setScreen("manual-entry");
      return;
    }
    try {
      const resp = await fetch(`${API_BASE}/api/generate-copy`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          stall_name: stallName,
          cuisine_type: cuisineType,
          dishes: validDishes,
          description: stallDesc,
        }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();
      setResults(data);
      setScreen("results");
    } catch (err) {
      setError("Failed to generate copy. Please try again.");
      setScreen("landing");
    }
  }

  // --- LANDING ---
  if (screen === "landing") {
    return (
      <div className="min-h-screen bg-surface flex flex-col items-center px-4 pt-12 pb-8 max-w-md mx-auto">
        <h1 className="text-4xl font-extrabold text-secondary tracking-tight">HawkerBoost</h1>
        <p className="text-muted mt-2 text-center text-sm">AI marketing copy for your hawker stall — in 30 seconds.</p>

        {error && (
          <div className="mt-4 w-full bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">{error}</div>
        )}

        <div className="mt-8 w-full space-y-4">
          <button
            onClick={() => fileInputRef.current.click()}
            className="w-full bg-primary text-white font-semibold py-4 rounded-xl text-lg shadow-md active:scale-95 transition"
          >
            Upload Menu Photo
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={handleImageUpload}
          />
          <button
            onClick={() => setScreen("manual-entry")}
            className="w-full bg-white border-2 border-secondary text-secondary font-semibold py-4 rounded-xl text-lg active:scale-95 transition"
          >
            Enter Manually
          </button>
        </div>

        <div className="mt-10 flex items-center gap-6 text-center text-xs text-muted">
          <div className="flex flex-col items-center gap-1">
            <span className="text-2xl">1.</span>
            <span>Snap</span>
          </div>
          <span className="text-muted text-lg">&#8594;</span>
          <div className="flex flex-col items-center gap-1">
            <span className="text-2xl">2.</span>
            <span>Generate</span>
          </div>
          <span className="text-muted text-lg">&#8594;</span>
          <div className="flex flex-col items-center gap-1">
            <span className="text-2xl">3.</span>
            <span>Copy</span>
          </div>
        </div>

        <p className="mt-6 text-xs text-muted text-center">Output in English, &#20013;&#25991; &amp; Bahasa Melayu</p>
      </div>
    );
  }

  // --- LOADING ---
  if (screen === "loading") {
    return (
      <div className="min-h-screen bg-surface flex flex-col items-center justify-center px-4">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent mb-6"></div>
        <p className="text-lg text-secondary font-medium">{loadingPhase}</p>
      </div>
    );
  }

  // --- PHOTO CONFIRM ---
  if (screen === "photo-confirm") {
    return (
      <div className="min-h-screen bg-surface px-4 pt-6 pb-8 max-w-md mx-auto">
        <h2 className="text-2xl font-bold text-secondary mb-4">Confirm Your Menu</h2>

        {imagePreview && (
          <img src={imagePreview} alt="Menu" className="w-full rounded-lg mb-4 max-h-48 object-cover" />
        )}

        <label className="block text-sm font-medium text-secondary mb-1">Stall Name</label>
        <input
          value={stallName}
          onChange={(e) => setStallName(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-3 text-sm"
          placeholder="e.g. Ah Kow Char Kway Teow"
        />

        <label className="block text-sm font-medium text-secondary mb-1">Cuisine Type</label>
        <select
          value={cuisineType}
          onChange={(e) => setCuisineType(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-4 text-sm"
        >
          {["Chinese", "Malay", "Indian", "Western", "Mixed", "Other"].map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>

        <label className="block text-sm font-medium text-secondary mb-2">Dishes</label>
        {dishes.map((dish, i) => (
          <div key={i} className="flex gap-2 mb-2">
            <input
              value={dish.name}
              onChange={(e) => {
                const next = [...dishes];
                next[i] = { ...next[i], name: e.target.value };
                setDishes(next);
              }}
              className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
              placeholder="Dish name"
            />
            <input
              value={dish.price}
              onChange={(e) => {
                const next = [...dishes];
                next[i] = { ...next[i], price: e.target.value };
                setDishes(next);
              }}
              className="w-24 border border-gray-300 rounded-lg px-3 py-2 text-sm"
              placeholder="$0.00"
            />
            {dishes.length > 1 && (
              <button
                onClick={() => setDishes(dishes.filter((_, j) => j !== i))}
                className="text-red-400 text-sm px-2"
              >
                &#10005;
              </button>
            )}
          </div>
        ))}
        <button
          onClick={() => setDishes([...dishes, { name: "", price: "" }])}
          className="text-primary text-sm font-medium mb-6"
        >
          + Add Dish
        </button>

        <button
          onClick={generateCopy}
          className="w-full bg-primary text-white font-semibold py-4 rounded-xl text-lg shadow-md active:scale-95 transition"
        >
          Looks good — Generate Copy
        </button>
        <button onClick={reset} className="w-full text-muted text-sm mt-3 py-2">Start Over</button>
      </div>
    );
  }

  // --- MANUAL ENTRY ---
  if (screen === "manual-entry") {
    return (
      <div className="min-h-screen bg-surface px-4 pt-6 pb-8 max-w-md mx-auto">
        <h2 className="text-2xl font-bold text-secondary mb-4">Enter Your Menu</h2>

        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">{error}</div>
        )}

        <label className="block text-sm font-medium text-secondary mb-1">Stall Name *</label>
        <input
          value={stallName}
          onChange={(e) => setStallName(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-3 text-sm"
          placeholder="e.g. Ah Kow Char Kway Teow"
        />

        <label className="block text-sm font-medium text-secondary mb-1">Cuisine Type</label>
        <select
          value={cuisineType}
          onChange={(e) => setCuisineType(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-3 text-sm"
        >
          {["Chinese", "Malay", "Indian", "Western", "Mixed", "Other"].map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>

        <label className="block text-sm font-medium text-secondary mb-1">Stall Description (optional)</label>
        <input
          value={stallDesc}
          onChange={(e) => setStallDesc(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-4 text-sm"
          placeholder="e.g. Family recipe, 30 years in Tiong Bahru"
          maxLength={100}
        />

        <label className="block text-sm font-medium text-secondary mb-2">Dishes *</label>
        {dishes.map((dish, i) => (
          <div key={i} className="flex gap-2 mb-2">
            <input
              value={dish.name}
              onChange={(e) => {
                const next = [...dishes];
                next[i] = { ...next[i], name: e.target.value };
                setDishes(next);
              }}
              className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
              placeholder="Dish name"
            />
            <input
              value={dish.price}
              onChange={(e) => {
                const next = [...dishes];
                next[i] = { ...next[i], price: e.target.value };
                setDishes(next);
              }}
              className="w-24 border border-gray-300 rounded-lg px-3 py-2 text-sm"
              placeholder="$0.00"
            />
            {dishes.length > 1 && (
              <button
                onClick={() => setDishes(dishes.filter((_, j) => j !== i))}
                className="text-red-400 text-sm px-2"
              >
                &#10005;
              </button>
            )}
          </div>
        ))}
        {dishes.length < 20 && (
          <button
            onClick={() => setDishes([...dishes, { name: "", price: "" }])}
            className="text-primary text-sm font-medium mb-6"
          >
            + Add Dish
          </button>
        )}

        <button
          onClick={generateCopy}
          className="w-full bg-primary text-white font-semibold py-4 rounded-xl text-lg shadow-md active:scale-95 transition"
        >
          Generate Copy
        </button>
        <button onClick={reset} className="w-full text-muted text-sm mt-3 py-2">Start Over</button>
      </div>
    );
  }

  // --- RESULTS ---
  if (screen === "results") {
    const langs = [
      { key: "en", label: "EN" },
      { key: "zh", label: "\u4e2d\u6587" },
      { key: "bm", label: "BM" },
    ];
    const platforms = [
      { key: "instagram", label: "Instagram Caption", icon: "\ud83d\udcf8" },
      { key: "google_maps", label: "Google Maps Description", icon: "\ud83d\udccd" },
      { key: "whatsapp", label: "WhatsApp Broadcast", icon: "\ud83d\udcac" },
    ];

    return (
      <div className="min-h-screen bg-surface px-4 pt-6 pb-8 max-w-md mx-auto">
        <h2 className="text-2xl font-bold text-secondary mb-4">Your Marketing Copy</h2>

        <div className="flex gap-2 mb-6">
          {langs.map((l) => (
            <button
              key={l.key}
              onClick={() => setActiveLang(l.key)}
              className={`flex-1 py-2 rounded-full text-sm font-semibold transition ${
                activeLang === l.key
                  ? "bg-primary text-white"
                  : "bg-white border border-gray-300 text-secondary"
              }`}
            >
              {l.label}
            </button>
          ))}
        </div>

        {platforms.map((p) => (
          <CopyCard
            key={p.key}
            icon={p.icon}
            label={p.label}
            text={results?.[activeLang]?.[p.key] || ""}
          />
        ))}

        <button onClick={reset} className="w-full text-muted text-sm mt-6 py-2">Start Over</button>
      </div>
    );
  }

  return null;
}

function CopyCard({ icon, label, text }) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 mb-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-secondary">
          {icon} {label}
        </h3>
        <button
          onClick={handleCopy}
          className={`text-xs font-medium px-3 py-1 rounded-full transition ${
            copied ? "bg-green-100 text-green-700" : "bg-gray-100 text-secondary"
          }`}
        >
          {copied ? "Copied \u2713" : "Copy"}
        </button>
      </div>
      <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{text}</p>
      <p className="text-xs text-muted mt-2">{text.length} chars</p>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
