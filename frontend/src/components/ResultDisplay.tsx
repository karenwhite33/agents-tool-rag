import React, { useEffect, useState } from "react";
import ArticleCard from "./ArticleCard";
import { marked } from "marked";
import hljs from "highlight.js";
import DOMPurify from "dompurify";
import "highlight.js/styles/github-dark.css";

interface ResultDisplayProps {
  articles?: any[];
  aiResponse?: string;
  modelInfo?: string;
  aiErrorMsg?: string;
  loading?: boolean;
}

const ResultDisplay: React.FC<ResultDisplayProps> = ({
  articles,
  aiResponse,
  modelInfo,
  aiErrorMsg,
  loading = false,
}) => {
  const [showSpinner, setShowSpinner] = useState(loading);

  useEffect(() => {
    if (loading) {
      setShowSpinner(true);
    } else {
      // Check for articles (Search mode), AI response content (Ask AI mode), or error messages
      const hasArticles = articles && articles.length > 0;
      const hasAiContent = aiResponse && aiResponse.trim().length >= 10;
      const hasError = aiErrorMsg && aiErrorMsg.trim().length > 0;
      const hasContent = hasArticles || hasAiContent || hasError;
      
      if (hasContent) {
        // Small delay to ensure smooth transition
        const timeout = setTimeout(() => setShowSpinner(false), 200);
        return () => clearTimeout(timeout);
      }
      // If loading is false but no content yet, keep spinner visible
      // (This handles the case where loading was set to false too early)
    }
  }, [loading, aiResponse, articles, aiErrorMsg]);

  // Highlight code blocks
  useEffect(() => {
    document.querySelectorAll("pre code").forEach((block) => {
      hljs.highlightElement(block as HTMLElement);
    });
  }, [aiResponse]);

  if (showSpinner) {
    return (
      <div className="flex flex-col items-center justify-center p-12 min-h-[200px] bg-gray-50 rounded-xl border border-gray-200 animate-fade-in">
        <div className="w-14 h-14 rounded-full border-4 border-transparent bg-conic-gradient animate-spin mb-4 relative">
          <div className="absolute inset-1.5 rounded-full bg-white shadow-sm" />
        </div>
        <p className="text-gray-600 font-medium text-lg">
          Generating response...
        </p>
      </div>
    );
  }

  if (articles && articles.length > 0) {
    return (
      <div className="grid grid-cols-1 gap-5">
        {articles.map((item, idx) => (
          <ArticleCard
            key={idx}
            title={item.title}
            feed_name={item.feed_name}
            feed_author={item.feed_author}
            source_name={item.source_name}
            source_author={item.source_author}
            article_authors={item.article_author}
            authors={item.authors}
            url={item.url}
            category={item.category}
            language={item.language}
            stars={item.stars}
            source_type={item.source_type}
            features={item.features}
          />
        ))}
      </div>
    );
  }

  // Show error message even if there's no response
  if (aiErrorMsg) {
    return (
      <div className="px-4 py-4 md:px-8 md:py-6 space-y-6">
        <div className="max-w-md mx-auto p-6 rounded-xl bg-red-50 border border-red-200 shadow-lg flex flex-col items-center justify-center gap-2">
          <span className="text-2xl mb-2">⚠️</span>
          <span className="font-semibold text-gray-800 text-center text-lg">
            {aiErrorMsg}
          </span>
        </div>
      </div>
    );
  }

  if (aiResponse) {
    // Sanitize HTML to prevent XSS attacks (use sync parse so type is string)
    const htmlStr = marked.parse(aiResponse, { async: false });
    const sanitizedHtml = DOMPurify.sanitize(htmlStr, {
      ALLOWED_TAGS: [
        'p', 'br', 'strong', 'em', 'u', 's', 'code', 'pre',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'blockquote',
        'a', 'img',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'hr', 'div', 'span'
      ],
      ALLOWED_ATTR: ['href', 'title', 'target', 'rel', 'src', 'alt', 'class', 'id'],
      ALLOW_DATA_ATTR: false
    });

    return (
      <div className="px-4 py-4 md:px-8 md:py-6 space-y-6">
        {/* Card wrapper for the AI response */}
        <div className="bg-white p-6 rounded-xl shadow-md border border-gray-200 overflow-x-auto">
          <div className="markdown-content max-w-full overflow-x-auto prose prose-indigo break-words">
            <div dangerouslySetInnerHTML={{ __html: sanitizedHtml }} />
          </div>
        </div>

        {modelInfo && (
          <div className="max-w-lg mx-auto mt-6 p-6 rounded-xl bg-teal-50 border border-teal-200 shadow-lg flex flex-col items-center justify-center gap-2">
            <span className="text-xl">🤖</span>
            <span className="font-semibold text-gray-700 w-full text-center">
              Model used based on latency
            </span>
            <span className="font-bold font-semibold text-teal-600 w-full text-center">
              {modelInfo.replace(/^Model used based on latency:\s*/, "")}
            </span>
          </div>
        )}
      </div>
    );
  }


  return null;
};

export default ResultDisplay;
