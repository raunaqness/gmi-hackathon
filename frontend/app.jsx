const { useState, useRef } = React;

const API_BASE = "http://localhost:8000";

function App() {
  // Cumulative stall profile "DB"
  const [stallName, setStallName] = useState("");
  const [address, setAddress] = useState("");
  const [cuisineType, setCuisineType] = useState("");
  const [stallDesc, setStallDesc] = useState("");
  const [dishes, setDishes] = useState([]);
  const [tags, setTags] = useState([]);
  const [notes, setNotes] = useState("");

  // Upload state
  const [uploadedImages, setUploadedImages] = useState([]); // { preview, type, loading }
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  // Results state (for later)
  const [results, setResults] = useState(null);
  const [activeLang, setActiveLang] = useState("en");
  const [generating, setGenerating] = useState(false);

  const pendingRef = useRef(0);

  function handleImageUpload(e) {
    const files = Array.from(e.target.files);
    if (!files.length) return;
    e.target.value = "";
    setError(null);

    const remaining = 5 - uploadedImages.length;
    const batch = files.slice(0, remaining);
    if (files.length > remaining) {
      setError(`Only ${remaining} more photo(s) allowed (max 5 total). First ${batch.length} selected.`);
    }
    if (batch.length === 0) {
      setError("Maximum 5 photos reached.");
      return;
    }

    setUploading(true);
    const startIdx = uploadedImages.length;
    const placeholders = batch.map((f) => ({ preview: URL.createObjectURL(f), type: "...", loading: true }));
    setUploadedImages((prev) => [...prev, ...placeholders]);
    pendingRef.current += batch.length;

    batch.forEach((file, i) => {
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = reader.result.split(",")[1];
        parseImage(base64, startIdx + i);
      };
      reader.readAsDataURL(file);
    });
  }

  async function parseImage(base64, idx) {
    try {
      const resp = await fetch(`${API_BASE}/api/parse-image`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_base64: base64 }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();

      // Update image type badge
      setUploadedImages((prev) =>
        prev.map((img, i) =>
          i === idx ? { ...img, type: data.image_type || "other", loading: false } : img
        )
      );

      // Merge into stall profile — fill empty fields, don't overwrite existing
      if (data.stall_name && !stallName) setStallName(data.stall_name);
      if (data.address && !address) setAddress(data.address);
      if (data.cuisine_type && !cuisineType) setCuisineType(data.cuisine_type);
      if (data.description && !stallDesc) setStallDesc(data.description);
      if (data.notes && !notes) setNotes(data.notes);

      // Append new dishes
      if (data.dishes && data.dishes.length > 0) {
        setDishes((prev) => [...prev, ...data.dishes]);
      }

      // Merge tags (deduplicate)
      if (data.tags && data.tags.length > 0) {
        setTags((prev) => [...new Set([...prev, ...data.tags])]);
      }
    } catch (err) {
      setError("Couldn't analyze this image. Try another photo.");
      setUploadedImages((prev) =>
        prev.map((img, i) =>
          i === idx ? { ...img, type: "error", loading: false } : img
        )
      );
    } finally {
      pendingRef.current -= 1;
      if (pendingRef.current <= 0) {
        pendingRef.current = 0;
        setUploading(false);
      }
    }
  }

  async function generateCopy() {
    const validDishes = dishes.filter((d) => d.name.trim());
    if (!stallName.trim()) {
      setError("Please add a stall name before generating.");
      return;
    }
    if (validDishes.length === 0) {
      setError("Please add at least one dish before generating.");
      return;
    }
    setGenerating(true);
    setError(null);
    try {
      const resp = await fetch(`${API_BASE}/api/generate-copy`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          stall_name: stallName,
          cuisine_type: cuisineType,
          dishes: validDishes,
          description: [stallDesc, address, notes, tags.length ? "Tags: " + tags.join(", ") : ""].filter(Boolean).join(". "),
        }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();
      setResults(data);
    } catch (err) {
      setError("Failed to generate copy. Please try again.");
    } finally {
      setGenerating(false);
    }
  }

  const hasEnoughInfo = stallName.trim() && dishes.some((d) => d.name.trim());

  const typeBadgeColors = {
    menu: "bg-blue-100 text-blue-700",
    stall: "bg-green-100 text-green-700",
    food: "bg-orange-100 text-orange-700",
    other: "bg-gray-100 text-gray-600",
    error: "bg-red-100 text-red-600",
    "...": "bg-gray-100 text-gray-400",
  };

  return (
    <div className="min-h-screen bg-surface px-4 pt-8 pb-12 max-w-md mx-auto">
      {/* Header */}
      <h1 className="text-3xl font-extrabold text-secondary tracking-tight text-center">MakanMap</h1>
      <p className="text-muted mt-1 text-center text-sm">Upload photos of your stall &mdash; we'll do the rest.</p>

      {error && (
        <div className="mt-4 bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">{error}</div>
      )}

      {/* Upload Area */}
      <div className="mt-6">
        <button
          onClick={() => fileInputRef.current.click()}
          disabled={uploading || uploadedImages.length >= 5}
          className={`w-full font-semibold py-3 rounded-xl text-base shadow-sm transition ${
            uploading || uploadedImages.length >= 5
              ? "bg-gray-300 text-gray-500 cursor-not-allowed"
              : "bg-primary text-white active:scale-95"
          }`}
        >
          {uploading ? "Analyzing photos..." : `Upload Photos (${uploadedImages.length}/5)`}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={handleImageUpload}
        />
        <p className="text-xs text-muted mt-2 text-center">Menu, stall front, food photos &mdash; anything helps!</p>
      </div>

      {/* Uploaded Images Grid */}
      {uploadedImages.length > 0 && (
        <div className="mt-4 flex gap-3 flex-wrap">
          {uploadedImages.map((img, i) => (
            <div key={i} className="relative w-20 h-20 rounded-lg overflow-hidden border border-gray-200 shadow-sm">
              <img src={img.preview} alt="" className="w-full h-full object-cover" />
              {img.loading ? (
                <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
                  <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
                </div>
              ) : (
                <span className={`absolute bottom-0 left-0 right-0 text-center text-[10px] font-semibold py-0.5 ${typeBadgeColors[img.type] || typeBadgeColors.other}`}>
                  {img.type}
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Stall Details Card */}
      <div className="mt-6 bg-white rounded-xl shadow-sm border border-gray-100 p-4">
        <h2 className="text-sm font-semibold text-secondary mb-3">Stall Details</h2>

        <label className="block text-xs font-medium text-muted mb-1">Stall Name</label>
        <input
          value={stallName}
          onChange={(e) => setStallName(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-3 text-sm"
          placeholder="e.g. Ah Kow Char Kway Teow"
        />

        <label className="block text-xs font-medium text-muted mb-1">Address / Location</label>
        <input
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-3 text-sm"
          placeholder="e.g. Tiong Bahru Market, Stall #02-05"
        />

        <div className="flex gap-3 mb-3">
          <div className="flex-1">
            <label className="block text-xs font-medium text-muted mb-1">Cuisine Type</label>
            <select
              value={cuisineType}
              onChange={(e) => setCuisineType(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            >
              <option value="">Select...</option>
              {["Chinese", "Malay", "Indian", "Western", "Japanese", "Korean", "Thai", "Mixed", "Other"].map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </div>
        </div>

        <label className="block text-xs font-medium text-muted mb-1">Description</label>
        <input
          value={stallDesc}
          onChange={(e) => setStallDesc(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          placeholder="e.g. Family recipe, 30 years in Tiong Bahru"
          maxLength={200}
        />

        {tags.length > 0 && (
          <div className="mt-3">
            <label className="block text-xs font-medium text-muted mb-1">Tags</label>
            <div className="flex flex-wrap gap-2">
              {tags.map((tag, i) => {
                const isSpecial = tag.toLowerCase().includes("michelin");
                const isHalal = tag.toLowerCase().includes("halal") || tag.toLowerCase().includes("no pork");
                return (
                  <span
                    key={i}
                    className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ${
                      isSpecial ? "bg-red-100 text-red-700 border border-red-200" :
                      isHalal ? "bg-green-100 text-green-700 border border-green-200" :
                      "bg-purple-100 text-purple-700 border border-purple-200"
                    }`}
                  >
                    {isSpecial ? "\u2b50" : isHalal ? "\u2714" : ""} {tag}
                    <button
                      onClick={() => setTags(tags.filter((_, j) => j !== i))}
                      className="ml-0.5 opacity-50 hover:opacity-100"
                    >&#10005;</button>
                  </span>
                );
              })}
            </div>
          </div>
        )}

        {notes && (
          <div className="mt-3 bg-blue-50 rounded-lg px-3 py-2">
            <p className="text-xs font-medium text-blue-700 mb-1">AI Notes</p>
            <p className="text-xs text-blue-600">{notes}</p>
          </div>
        )}
      </div>

      {/* Menu Items Card */}
      <div className="mt-4 bg-white rounded-xl shadow-sm border border-gray-100 p-4">
        <h2 className="text-sm font-semibold text-secondary mb-3">
          Menu Items {dishes.length > 0 && <span className="text-muted font-normal">({dishes.length})</span>}
        </h2>

        {dishes.length === 0 ? (
          <p className="text-xs text-muted mb-3">No dishes yet. Upload a menu photo or add manually.</p>
        ) : (
          dishes.map((dish, i) => {
            const hasMissingPrice =
              (!dish.sizes || dish.sizes.length === 0) && !dish.price
              || (dish.sizes && dish.sizes.some((s) => !s.price || s.price.trim() === ""));
            return (
            <div key={i} className={`mb-3 ${hasMissingPrice ? "rounded-lg border-l-4 border-amber-400 pl-2" : ""}`}>
              <div className="flex gap-2">
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
                {!dish.sizes?.length && (
                  <input
                    value={dish.price || ""}
                    onChange={(e) => {
                      const next = [...dishes];
                      next[i] = { ...next[i], price: e.target.value };
                      setDishes(next);
                    }}
                    className={`w-24 border rounded-lg px-3 py-2 text-sm ${hasMissingPrice ? "border-amber-400 bg-amber-50" : "border-gray-300"}`}
                    placeholder="$0.00"
                  />
                )}
                <button
                  onClick={() => setDishes(dishes.filter((_, j) => j !== i))}
                  className="text-red-400 text-sm px-2"
                >
                  &#10005;
                </button>
              </div>
              {hasMissingPrice && (
                <p className="text-xs text-amber-600 mt-1 font-medium">Price missing — please add it</p>
              )}
              {dish.sizes?.length > 0 && (
                <div className="ml-2 mt-1 flex flex-wrap gap-2">
                  {dish.sizes.map((s, si) => {
                    const sizeEmpty = !s.price || s.price.trim() === "";
                    return (
                    <span key={si} className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs ${sizeEmpty ? "bg-amber-50 border border-amber-300 text-amber-700" : "bg-orange-50 border border-orange-200 text-orange-700"}`}>
                      <span className="font-medium">{s.label}:</span>
                      <input
                        value={s.price}
                        onChange={(e) => {
                          const next = [...dishes];
                          const newSizes = [...next[i].sizes];
                          newSizes[si] = { ...newSizes[si], price: e.target.value };
                          next[i] = { ...next[i], sizes: newSizes };
                          setDishes(next);
                        }}
                        className={`w-14 bg-transparent text-xs outline-none ${sizeEmpty ? "text-amber-700 placeholder-amber-400" : "text-orange-700"}`}
                        placeholder="$?"
                      />
                    </span>
                    );
                  })}
                </div>
              )}
            </div>
            );
          })
        )}
        <button
          onClick={() => setDishes([...dishes, { name: "", price: "" }])}
          className="text-primary text-sm font-medium mt-1"
        >
          + Add Dish
        </button>
      </div>

      {/* Generate Button */}
      <div className="mt-6">
        <button
          onClick={generateCopy}
          disabled={!hasEnoughInfo || generating}
          className={`w-full font-semibold py-4 rounded-xl text-lg shadow-md transition ${
            hasEnoughInfo && !generating
              ? "bg-secondary text-white active:scale-95"
              : "bg-gray-200 text-gray-400 cursor-not-allowed"
          }`}
        >
          {generating ? "Generating..." : "Generate Marketing Copy"}
        </button>
        {!hasEnoughInfo && (
          <p className="text-xs text-muted mt-2 text-center">Add a stall name and at least one dish to continue.</p>
        )}
      </div>

      {/* Results */}
      {results && <ResultsSection results={results} activeLang={activeLang} setActiveLang={setActiveLang} />}
    </div>
  );
}

function ResultsSection({ results, activeLang, setActiveLang }) {
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
    <div className="mt-8">
      <h2 className="text-lg font-bold text-secondary mb-4">Your Marketing Copy</h2>

      <div className="flex gap-2 mb-4">
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
    </div>
  );
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
