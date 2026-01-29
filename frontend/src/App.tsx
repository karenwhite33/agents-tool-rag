import React, { useState } from "react";
import ResultDisplay from "./components/ResultDisplay";
import UnifiedForm from "./components/UnifiedForm";
import { fetchArticles, aiStream, aiNonStream } from "./api/backend";
import { providers, getModelsForProvider } from "./data/modelRegistry";
import { feeds } from "./data/feedsAndProviders";

const App: React.FC = () => {
  const [mode, setMode] = useState<"Search" | "AI">("Search");
  const [formState, setFormState] = useState<any>({
    query_text: "",
    provider: providers[0],
    model: "",
    streamingMode: "Streaming",
  });
  const [formError, setFormError] = useState("");
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [articles, setArticles] = useState<any[]>([]);
  const [aiResponse, setAIResponse] = useState("");
  const [modelInfo, setModelInfo] = useState("");
  const [aiErrorMsg, setAIErrorMsg] = useState("");
  const [loading, setLoading] = useState(false);

  const handleFormChange = (newState: any) => {
    setFormState(newState);
    setFormError("");
  };

  const handleSubmit = async (payload: any) => {
    if (!payload.query_text.trim()) {
      setFormError("Please enter a query.");
      return;
    }

    setHasSubmitted(true);
    setLoading(true);
    setFormError("");
    setArticles([]);
    setAIResponse("");
    setModelInfo("");
    setAIErrorMsg("");

    try {
      if (mode === "Search") {
        const results = await fetchArticles(payload);
        setArticles(results);
      } else {
        if (payload.streamingMode === "Streaming") {
          let hasContent = false;
          let hasError = false;
          await aiStream(
            payload,
            (text: string, errorMsg?: string) => {
              setAIResponse(text);
              if (errorMsg) {
                setAIErrorMsg(errorMsg);
                hasError = true;
                // Immediately clear loading when error occurs
                setLoading(false);
              } else if (!hasContent && text.trim().length >= 10) {
                // Only hide loading when we have actual text content (at least 10 chars to avoid flicker)
                hasContent = true;
                setLoading(false);
              }
            },
            (info: string) => setModelInfo(`Model used based on latency: ${info}`)
          );
          // If streaming completed but we never got content or error, hide loading anyway
          if (!hasContent && !hasError) {
            setLoading(false);
          }
        } else {
          const { answer, modelUsed } = await aiNonStream(payload);
          setAIResponse(answer);
          setModelInfo(`Model used based on latency: ${modelUsed || "unknown"}`);
        }
      }
    } catch (err) {
      // Extract user-friendly error message if available
      const errorMessage = err instanceof Error ? err.message : "Something went wrong. Please try again.";
      // For AI mode, set aiErrorMsg; for Search mode, set formError
      if (mode === "AI") {
        setAIErrorMsg(errorMessage);
      } else {
        setFormError(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  const feedNames = feeds.map((f) => f.name);
  const feedAuthors = feeds.map((f) => f.author);

  return (
    <div className="flex h-screen bg-gray-100 overflow-hidden">
      {/* LEFT SIDEBAR WITH FUNCTIONALITY MENU */}
      <div className="w-96 bg-gradient-to-b from-blue-300 to-teal-300 flex flex-col rounded-bl-3xl shadow-lg relative z-50 overflow-y-auto">
        {/* Logo/Star Icon at Top */}
        <div className="p-6 border-b border-blue-400/30">
          <div className="flex items-center gap-3">
            <svg className="w-8 h-8 text-blue-500" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" />
            </svg>
            <h2 className="text-gray-700 font-semibold text-lg">AI Agent Tools</h2>
          </div>
        </div>

        {/* Mode Selection */}
        <div className="p-4 border-b border-blue-400/30">
          <div className="flex gap-2">
            {["Search", "AI"].map((m) => (
              <button
                key={m}
                onClick={() => setMode(m as "Search" | "AI")}
                className={`flex-1 px-4 py-2 rounded-lg font-semibold transition-all text-sm ${
                  mode === m
                    ? "bg-white text-teal-600 shadow-md"
                    : "bg-blue-200/50 text-gray-600 hover:bg-blue-200/70"
                }`}
              >
                {m === "Search" ? "Search" : "AI"}
              </button>
            ))}
          </div>
        </div>

        {/* Form with All Options */}
        <div className="flex-1 p-4">
          {formError && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
              {formError}
            </div>
          )}
          
          <UnifiedForm
            mode={mode}
            formState={formState}
            onFormChange={handleFormChange}
            onSubmit={handleSubmit}
            hideQueryField={false}
            providers={mode === "AI" ? providers : undefined}
            models={mode === "AI" ? getModelsForProvider(formState.provider) : []}
            feedNames={feedNames}
            feedAuthors={feedAuthors}
          />
        </div>

      </div>

      {/* MAIN CONTENT AREA - RESULTS ONLY */}
      <div className="flex-1 flex flex-col bg-white overflow-hidden">
        {/* Top Right Help Link */}
        <div className="absolute top-4 right-4 z-10">
          <a href="#" className="text-gray-500 hover:text-gray-700 flex items-center gap-1 text-sm">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Help
          </a>
        </div>

        {/* Main Content - Results Only */}
        <main className="flex-1 overflow-y-auto px-8 py-12">
          {/* Welcome Message */}
          <div className="mb-6">
            <p className="text-blue-400 text-lg mb-2">Welcome to the AI Agents Tools RSS Feed</p>
            <h1 className="text-blue-400 text-4xl font-bold mb-3">What would like to know?</h1>
            <p className="text-gray-500 text-base">
              Learn anything from AI Agents!
            </p>
          </div>

          {/* Three Horizontal Cards */}
          <div className="flex gap-6 mb-12">
            {[
              { heading: "What is Agentic AI?" },
              { heading: "What is Langraph for?" },
              { heading: "Eval loops" },
            ].map((card, index) => (
              <div
                key={index}
                className="flex-1 bg-white rounded-xl p-6 shadow-md border border-gray-200 hover:shadow-lg transition-shadow"
              >
                <div className="flex items-center justify-between">
                  <h3 className="text-gray-700 font-bold text-lg">{card.heading}</h3>
                  <svg className="w-5 h-5 text-teal-400" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" />
                  </svg>
                </div>
              </div>
            ))}
          </div>

          {/* Results Display Area */}
          {hasSubmitted && (
            <div>
              <ResultDisplay
                articles={mode === "Search" ? articles : undefined}
                aiResponse={mode === "AI" ? aiResponse : undefined}
                modelInfo={mode === "AI" ? modelInfo : undefined}
                aiErrorMsg={mode === "AI" ? aiErrorMsg : undefined}
                loading={loading}
              />
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

export default App;
