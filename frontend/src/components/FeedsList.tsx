// src/components/FeedsList.tsx
import React from "react";
import { feeds } from "../data/feedsAndProviders";

const FeedsList: React.FC = () => {
  return (
    <div className="absolute top-24 left-4 bg-white dark:bg-gray-800 rounded-lg shadow-md p-3 max-w-xs text-sm text-gray-700 dark:text-gray-300">
      <h3 className="font-semibold mb-2 text-orange-600 dark:text-orange-400">
        Available Feeds
      </h3>
      <ul className="space-y-1">
        {feeds.map((feed, idx) => (
          <li key={idx} className="flex flex-col">
            <span className="font-medium">{feed.name}</span>
            <span className="text-gray-500 dark:text-gray-400 text-xs">{feed.author}</span>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default FeedsList;
