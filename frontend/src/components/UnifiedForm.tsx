import React, { useState, useRef, useEffect } from "react";
import Select from "react-select";

interface UnifiedFormProps {
  mode: "Search" | "AI";
  feedNames: string[];
  feedAuthors: string[];
  providers?: string[];
  models?: string[];
  formState: any;
  onFormChange: (state: any) => void;
  onSubmit: (payload: any) => void;
  hideQueryField?: boolean;
}

const streamingModes = ["Streaming", "Non-Streaming"] as const;

// Color scheme: light grey, dark grey, light blue, mint
const selectStyles = {
  control: (base: any, state: any) => ({
    ...base,
    borderRadius: "0.5rem",
    borderColor: state.isFocused ? "#14b8a6" : "#D1D5DB", // teal when focused, light grey otherwise
    padding: "0.25rem",
    "&:hover": { 
      borderColor: "#14b8a6", // teal on hover
      backgroundColor: "rgba(255, 255, 255, 0.95)", // 95% opacity on hover
      boxShadow: "0 2px 8px rgba(20, 184, 166, 0.2)",
    },
    boxShadow: state.isFocused ? "0 2px 8px rgba(20, 184, 166, 0.2)" : "none",
    minHeight: "2.5rem",
    backgroundColor: "rgba(255, 255, 255, 0.85)", // 85% opacity (15% transparency)
    transition: "all 0.2s ease",
  }),
  menu: (base: any) => ({
    ...base,
    borderRadius: "0.5rem",
    backgroundColor: "white",
    boxShadow: "0 4px 20px rgba(0,0,0,0.15)",
    zIndex: 9999,
  }),
  menuPortal: (base: any) => ({
    ...base,
    zIndex: 9999,
  }),
  option: (base: any, state: any) => ({
    ...base,
    backgroundColor: state.isFocused ? "#81D8D0" : "white", // mint on hover
    color: state.isSelected ? "white" : "#374151", // dark grey
    cursor: "pointer",
    padding: "0.5rem 1rem",
  }),
  placeholder: (base: any) => ({
    ...base,
    color: "#9CA3AF", // light grey
  }),
  singleValue: (base: any) => ({
    ...base,
    color: "#374151", // dark grey
  }),
};

const UnifiedForm: React.FC<UnifiedFormProps> = ({
  mode,
  feedNames,
  feedAuthors,
  providers = [],
  models = [],
  formState,
  onFormChange,
  onSubmit,
  hideQueryField,
}) => {
  const _hideQueryField = hideQueryField ?? false;
  const queryText = formState.query_text || "";
  const feedName =
    formState.feed_nameObj ||
    (formState.feed_name ? { value: formState.feed_name, label: formState.feed_name } : null);
  const feedAuthor =
    formState.feed_authorObj ||
    (formState.feed_author ? { value: formState.feed_author, label: formState.feed_author } : null);
  const titleKeywords = formState.title_keywords || "";
  const category = formState.category || "";
  const language = formState.language || "";
  const sourceType = formState.source_type || "";
  const minStars = formState.min_stars ?? 0;
  const limit = formState.limit ?? 5;
  const provider = formState.provider || (providers[0] ?? "");
  const model = formState.model || "";
  const streamingMode = formState.streamingMode || "Streaming";

  const [showTooltip, setShowTooltip] = useState(false);
  const tooltipRef = useRef<HTMLDivElement>(null);

  const handleChange = (field: string, value: any) => {
    onFormChange({ ...formState, [field]: value });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const payload: any = {
      query_text: queryText,
      feed_name: feedName?.value ?? "",
      feed_nameObj: feedName,
      feed_author: feedAuthor?.value ?? "",
      feed_authorObj: feedAuthor,
      title_keywords: titleKeywords,
      limit,
    };
    if (category) payload.category = category;
    if (language) payload.language = language;
    if (sourceType) payload.source_type = sourceType;
    if (minStars > 0) payload.min_stars = minStars;
    if (mode === "AI") {
      payload.provider = provider;
      payload.model = model;
      payload.streamingMode = streamingMode;
    }
    onSubmit(payload);
  };

  // Hide tooltip when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (tooltipRef.current && !tooltipRef.current.contains(event.target as Node)) {
        setShowTooltip(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="flex flex-col gap-4">
        {!_hideQueryField && (
          <textarea
            className="w-full p-4 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-400 focus:border-teal-400 resize-none text-gray-700 placeholder-gray-400 hover:border-teal-400 hover:shadow-md transition-all duration-200 cursor-pointer"
            style={{ backgroundColor: "rgba(255, 255, 255, 0.85)" }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.95)"}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.85)"}
            placeholder="Ask what ever you want...."
            value={queryText}
            onChange={(e) => handleChange("query_text", e.target.value)}
            rows={6}
          />
        )}

        {/* Author Select */}
        <div className="hover:scale-[1.02] transition-transform duration-200 relative z-10">
          <Select
            options={feedAuthors.map((fa) => ({ value: fa, label: fa }))}
            value={feedAuthor}
            onChange={(option: any) => handleChange("feed_authorObj", option)}
            isClearable
            placeholder="Select Author (optional)"
            styles={selectStyles}
            menuPortalTarget={document.body}
            menuPosition="fixed"
          />
        </div>

        {/* Feed / Source Select */}
        <div className="hover:scale-[1.02] transition-transform duration-200 relative z-10">
          <Select
            options={feedNames.map((fn) => ({ value: fn, label: fn }))}
            value={feedName}
            onChange={(option: any) => handleChange("feed_nameObj", option)}
            isClearable
            placeholder="Select feed (optional)"
            styles={selectStyles}
            menuPortalTarget={document.body}
            menuPosition="fixed"
          />
        </div>

        {/* Tool Filters */}
        <div className="hover:scale-[1.02] transition-transform duration-200 relative z-10">
          <Select
            options={[
              { value: "", label: "All Categories" },
              { value: "Framework", label: "Framework" },
              { value: "Library", label: "Library" },
              { value: "Platform", label: "Platform" },
              { value: "Tool", label: "Tool" },
            ]}
            value={category ? { value: category, label: category } : null}
            onChange={(option: any) => handleChange("category", option?.value || "")}
            isClearable
            placeholder="Category (optional)"
            styles={selectStyles}
            menuPortalTarget={document.body}
            menuPosition="fixed"
          />
        </div>

        <div className="hover:scale-[1.02] transition-transform duration-200 relative z-10">
          <Select
            options={[
              { value: "", label: "All Languages" },
              { value: "Python", label: "Python" },
              { value: "JavaScript", label: "JavaScript" },
              { value: "TypeScript", label: "TypeScript" },
              { value: "Go", label: "Go" },
              { value: "Rust", label: "Rust" },
              { value: "Java", label: "Java" },
            ]}
            value={language ? { value: language, label: language } : null}
            onChange={(option: any) => handleChange("language", option?.value || "")}
            isClearable
            placeholder="Language (optional)"
            styles={selectStyles}
            menuPortalTarget={document.body}
            menuPosition="fixed"
          />
        </div>

        <div className="hover:scale-[1.02] transition-transform duration-200 relative z-10">
          <Select
            options={[
              { value: "", label: "All Sources" },
              { value: "github_repo", label: "GitHub Repository" },
              { value: "rss_article", label: "RSS Article" },
              { value: "documentation", label: "Documentation" },
            ]}
            value={sourceType ? (() => {
              const sourceTypeOptions = [
                { value: "", label: "All Sources" },
                { value: "github_repo", label: "GitHub Repository" },
                { value: "rss_article", label: "RSS Article" },
                { value: "documentation", label: "Documentation" },
              ];
              const found = sourceTypeOptions.find(opt => opt.value === sourceType);
              return found || null;
            })() : null}
            onChange={(option: any) => handleChange("source_type", option?.value || "")}
            isClearable
            placeholder="Source Type (optional)"
            styles={selectStyles}
            menuPortalTarget={document.body}
            menuPosition="fixed"
          />
        </div>

        <div className="hover:bg-white/20 p-3 rounded-lg transition-all duration-200 cursor-pointer">
          <label className="block text-sm font-semibold mb-2 text-gray-800">Min GitHub Stars: {minStars}</label>
          <input
            type="range"
            min={0}
            max={50000}
            step={100}
            value={minStars}
            onChange={(e) => handleChange("min_stars", Number(e.target.value))}
            className="w-full h-2 bg-gray-300 rounded-lg appearance-none cursor-pointer accent-teal-500 hover:accent-teal-600 transition-all duration-200"
            style={{
              background: `linear-gradient(to right, #14b8a6 0%, #14b8a6 ${(minStars / 50000) * 100}%, #d1d5db ${(minStars / 50000) * 100}%, #d1d5db 100%)`
            }}
          />
        </div>

        {mode === "Search" && (
          <>
            <div className="relative w-full" ref={tooltipRef}>
              <input
                type="text"
                className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-400 focus:border-teal-400 text-gray-700 placeholder-gray-500 hover:border-teal-400 hover:shadow-md transition-all duration-200 cursor-pointer"
              style={{ backgroundColor: "rgba(255, 255, 255, 0.85)" }}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.95)"}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.85)"}
                placeholder="Title Keywords (optional)"
                value={titleKeywords}
                onChange={(e) => handleChange("title_keywords", e.target.value)}
              />

              {/* Question mark icon */}
              <span
                className="absolute top-1/2 right-3 -translate-y-1/2 text-gray-400 cursor-pointer"
                onClick={() => setShowTooltip(!showTooltip)}
              >
                ?
              </span>

              {/* Tooltip */}
              {showTooltip && (
                <div className="absolute right-6 top-1/2 -translate-y-1/2 bg-gray-600 text-white text-xs rounded-lg py-2 px-3 w-max whitespace-nowrap z-50 shadow-lg">
                  Keywords present in the title
                </div>
              )}
            </div>

            {/* Number of results */}
            <div className="hover:bg-white/20 p-3 rounded-lg transition-all duration-200 cursor-pointer">
              <label className="block text-sm font-semibold mb-2 text-gray-800">Number of results: {limit}</label>
              <input
                type="range"
                min={1}
                max={20}
                value={limit}
                onChange={(e) => handleChange("limit", Number(e.target.value))}
                className="w-full h-2 bg-gray-300 rounded-lg appearance-none cursor-pointer accent-teal-500 hover:accent-teal-600 transition-all duration-200"
                style={{
                  background: `linear-gradient(to right, #14b8a6 0%, #14b8a6 ${((limit - 1) / 19) * 100}%, #d1d5db ${((limit - 1) / 19) * 100}%, #d1d5db 100%)`
                }}
              />
            </div>
          </>
        )}

        {/* AI mode options */}
        {mode === "AI" && (
          <div className="flex flex-col gap-4">
            <div>
              <label className="block text-sm font-semibold mb-2 text-gray-800">
                LLM Provider
              </label>
              <select
                value={provider}
                onChange={(e) => handleChange("provider", e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-400 focus:border-teal-400 text-gray-600 hover:border-teal-400 hover:shadow-md transition-all duration-200 cursor-pointer"
                style={{ backgroundColor: "rgba(255, 255, 255, 0.85)" }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.95)"}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.85)"}
              >
                {providers.map((p, idx) => (
                  <option key={idx} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-semibold mb-2 text-gray-800">
                Model
              </label>
              <select
                value={model}
                onChange={(e) => handleChange("model", e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-400 focus:border-teal-400 text-gray-600 hover:border-teal-400 hover:shadow-md transition-all duration-200 cursor-pointer"
                style={{ backgroundColor: "rgba(255, 255, 255, 0.85)" }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.95)"}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.85)"}
              >
                {models.map((m, idx) => (
                  <option key={idx} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>

            <div 
              className="flex gap-4 items-center text-sm p-3 rounded-lg hover:shadow-md transition-all duration-200 cursor-pointer"
              style={{ backgroundColor: "rgba(255, 255, 255, 0.85)" }}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.95)"}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.85)"}
            >
              <span className="font-medium text-gray-600">Answer:</span>
              {streamingModes.map((sm) => (
                <label key={sm} className="flex items-center gap-2 text-gray-600 cursor-pointer hover:text-teal-600 transition-colors">
                  <input
                    type="radio"
                    name="streamingMode"
                    value={sm}
                    checked={streamingMode === sm}
                    onChange={() => handleChange("streamingMode", sm)}
                    className="accent-teal-400 hover:accent-teal-600 cursor-pointer transition-all"
                  />
                  {sm}
                </label>
              ))}
            </div>
          </div>
        )}

        <div className="flex justify-end mt-4 pt-4 border-t border-gray-200">
          <button
            type="submit"
            className="bg-green-500 hover:bg-green-600 text-white rounded-lg px-6 py-3 shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2 font-semibold"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
            Search
          </button>
        </div>
      </div>
    </form>
  );
};

export default UnifiedForm;
