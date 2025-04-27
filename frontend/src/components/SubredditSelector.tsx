import React from 'react';

interface SubredditSelectorProps {
  subreddits: string[];
  selectedSubreddit: string;
  onSubredditChange: (subreddit: string) => void;
}

const SubredditSelector: React.FC<SubredditSelectorProps> = ({
  subreddits,
  selectedSubreddit,
  onSubredditChange,
}) => {
  return (
    <div className="bg-white p-4 shadow rounded-lg">
      <label htmlFor="subreddit-select" className="block text-sm font-medium text-gray-700 mb-2">
        Select Subreddit
      </label>
      <select
        id="subreddit-select"
        className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
        value={selectedSubreddit}
        onChange={(e) => onSubredditChange(e.target.value)}
      >
        {subreddits.length === 0 ? (
          <option value="">Loading subreddits...</option>
        ) : (
          subreddits.map((subreddit) => (
            <option key={subreddit} value={subreddit}>
              r/{subreddit}
            </option>
          ))
        )}
      </select>
    </div>
  );
};

export default SubredditSelector; 