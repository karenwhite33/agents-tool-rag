const VITE_BACKEND_URL = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_BACKEND_URL;

export interface SearchPayload {
  query_text: string;
  feed_name?: string;
  feed_author?: string;
  title_keywords?: string;
  category?: string;
  language?: string;
  source_type?: string;
  min_stars?: number;
  limit: number;
}

export interface AIRequestPayload extends SearchPayload {
  provider: string;
  model?: string;
}

// ------------------------
// Helper: clean payload
// ------------------------
const cleanPayload = (payload: AIRequestPayload) => {
  const adjusted: any = { ...payload, provider: payload.provider.toLowerCase() };
  if (!adjusted.model || adjusted.model === "Automatic Model Selection (Model Routing)") {
    delete adjusted.model;
  }
  return adjusted;
};

// ------------------------
// Fetch articles
// ------------------------
export const fetchArticles = async (payload: SearchPayload) => {
  const url = `${VITE_BACKEND_URL}/search/unique-titles`;

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        "X-API-Key": import.meta.env.VITE_API_KEY || ""
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      // Do not expose backend error text to user (visible in F12 / UI)
      throw new Error("Search failed. Please try again.");
    }

    const text = await res.text();

    try {
      const data = JSON.parse(text);
      return data.results || [];
    } catch {
      return text;
    }
  } catch (err) {
    // Re-throw with generic message only (no backend details)
    throw err instanceof Error ? err : new Error("Search failed. Please try again.");
  }
};

// ------------------------
// AI Streaming
// ------------------------
export const aiStream = async (
  payload: AIRequestPayload,
  onUpdate: (text: string, errorMsg?: string) => void,
  onModelInfo?: (info: string) => void
) => {
  const adjustedPayload = cleanPayload(payload);

  try {
    const res = await fetch(`${VITE_BACKEND_URL}/search/ask/stream`, {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        "X-API-Key": import.meta.env.VITE_API_KEY || ""
      },
      body: JSON.stringify(adjustedPayload),
    });

    if (!res.ok) {
      // Try to extract error message from response
      let errorMsg = "Your query contains invalid characters or patterns. Please rephrase your question.";
      try {
        const errorText = await res.text();
        try {
          const errorData = JSON.parse(errorText);
          if (errorData.detail && typeof errorData.detail === "object" && errorData.detail.message) {
            errorMsg = errorData.detail.message;
          } else if (typeof errorData.detail === "string") {
            errorMsg = errorData.detail;
          }
        } catch {
          // If JSON parsing fails, check if it's a plain text error
          if (errorText && errorText.trim().length > 0) {
            errorMsg = errorText.substring(0, 200); // Limit length
          }
        }
      } catch {
        // If reading response fails, use default message
      }
      onUpdate("", errorMsg);
      return;
    }

    if (!res.body) {
      onUpdate("", "error");
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let done = false;
    let accumulated = "";
    let errorOrTruncateMsg = "";

    while (!done) {
      const { value, done: doneReading } = await reader.read();
      done = doneReading;
      if (value) {
        const chunk = decoder.decode(value, { stream: true });

        // Handle special messages
        if (chunk.startsWith("__model_used__:")) {
          onModelInfo?.(chunk.replace("__model_used__:", "").trim());
        } else if (chunk.startsWith("__error__")) {
          // Extract error message after "__error__" prefix
          const errorMsg = chunk.replace("__error__", "").trim();
          errorOrTruncateMsg = errorMsg || "An error occurred. Please try again.";
        } else if (chunk.startsWith("__truncated__")) {
          errorOrTruncateMsg = "truncated";
        } else {
          accumulated += chunk; // normal AI text
        }

        onUpdate(accumulated, errorOrTruncateMsg);
      }
    }
  } catch (err) {
    // Error handled silently - no sensitive info exposed
    onUpdate("", "error");
  }
};

// ------------------------
// AI Non-Streaming
// ------------------------
export const aiNonStream = async (payload: AIRequestPayload) => {
  const adjustedPayload = cleanPayload(payload);

  try {
    const res = await fetch(`${VITE_BACKEND_URL}/search/ask`, {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        "X-API-Key": import.meta.env.VITE_API_KEY || ""
      },
      body: JSON.stringify(adjustedPayload),
    });

    if (!res.ok) {
      // Try to extract error message from JSON response
      let errorMsg = "Your query contains invalid characters or patterns. Please rephrase your question.";
      try {
        const errorText = await res.text();
        try {
          const errorData = JSON.parse(errorText);
          if (errorData.detail && typeof errorData.detail === "object" && errorData.detail.message) {
            errorMsg = errorData.detail.message;
          } else if (typeof errorData.detail === "string") {
            errorMsg = errorData.detail;
          }
        } catch {
          // If JSON parsing fails, check if it's a plain text error
          if (errorText && errorText.trim().length > 0) {
            errorMsg = errorText.substring(0, 200); // Limit length
          }
        }
      } catch {
        // If reading response fails, use default message
      }
      throw new Error(errorMsg);
    }

    const data = await res.json();

    return {
      answer: data.answer || "",
      modelUsed: data.model || "",
    };
  } catch (err) {
    // Error handled silently - no sensitive info exposed
    throw new Error("Failed to get response from server");
  }
};
