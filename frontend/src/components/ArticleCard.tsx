import React from "react";

interface ArticleCardProps {
  title: string;
  feed_name?: string;
  feed_author?: string;
  source_name?: string;
  source_author?: string;
  article_authors?: string[];
  authors?: string[];
  url?: string;
  category?: string;
  language?: string;
  stars?: number;
  source_type?: string;
  features?: string[];
}

const ArticleCard: React.FC<ArticleCardProps> = ({
  title,
  feed_name,
  feed_author,
  source_name,
  source_author,
  article_authors,
  authors,
  url,
  category,
  language,
  stars,
  source_type,
  features,
}) => {
  const displaySourceName = source_name || feed_name;
  const displaySourceAuthor = source_author || feed_author;
  const displayAuthors = authors || article_authors;

  return (
    <div className="bg-white rounded-xl shadow-md p-6 transition-transform hover:scale-[1.02] hover:shadow-lg border border-gray-200 w-full">
      
      <h2 className="text-xl md:text-2xl font-semibold mb-3 text-gray-900 truncate">
        {title}
      </h2>

      <div className="flex flex-wrap gap-2 mb-2">
        {displaySourceName && (
          <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-semibold">
            {displaySourceName}
          </span>
        )}
        {displaySourceAuthor && (
          <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs font-semibold">
            {displaySourceAuthor}
          </span>
        )}
        {category && (
          <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded-full text-xs font-semibold">
            {category}
          </span>
        )}
        {language && (
          <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded-full text-xs font-semibold">
            {language}
          </span>
        )}
        {stars !== undefined && stars !== null && (
          <span className="px-2 py-1 bg-orange-100 text-orange-800 rounded-full text-xs font-semibold">
            ⭐ {stars.toLocaleString()}
          </span>
        )}
        {source_type && (
          <span className="px-2 py-1 bg-indigo-100 text-indigo-800 rounded-full text-xs font-semibold">
            {source_type.replace("_", " ")}
          </span>
        )}
      </div>

      {displayAuthors && displayAuthors.length > 0 && (
        <p className="text-gray-600 text-sm mb-2">
          <span className="font-semibold">Authors:</span> {displayAuthors.join(", ")}
        </p>
      )}

      {features && features.length > 0 && (
        <p className="text-gray-600 text-sm mb-2">
          <span className="font-semibold">Features:</span> {features.slice(0, 5).join(", ")}
          {features.length > 5 && "..."}
        </p>
      )}

      {url && (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block mt-2 text-blue-600 font-medium hover:underline"
        >
          {source_type === "github_repo" ? "View Repository" : "Read Full Article"}
        </a>
      )}
    </div>
  );
};

export default ArticleCard;
