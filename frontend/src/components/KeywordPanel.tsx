import { useState, useEffect } from 'react';
import { fetchKeywords, fetchSentimentKeywords, KeywordData } from '../api/api';
import WordCloud from './WordCloud';

interface KeywordPanelProps {
  subreddit: string;
  timeframe: string;
}

const KeywordPanel: React.FC<KeywordPanelProps> = ({ subreddit, timeframe }) => {
  const [keywords, setKeywords] = useState<KeywordData[]>([]);
  const [sentimentKeywords, setSentimentKeywords] = useState<{
    positive: KeywordData[];
    negative: KeywordData[];
  }>({ positive: [], negative: [] });
  const [activeTab, setActiveTab] = useState<'all' | 'positive' | 'negative'>('all');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchKeywordData = async () => {
      if (!subreddit) return;
      
      setLoading(true);
      setError(null);
      
      try {
        // Fetch regular keywords
        const data = await fetchKeywords(subreddit, timeframe);
        setKeywords(data);
        
        // Fetch sentiment-based keywords
        const sentimentData = await fetchSentimentKeywords(subreddit, timeframe);
        setSentimentKeywords(sentimentData);
      } catch (err) {
        setError('Failed to load keyword data');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchKeywordData();
  }, [subreddit, timeframe]);

  if (loading) {
    return <div className="py-8 text-center">Loading keyword data...</div>;
  }

  if (error) {
    return <div className="py-8 text-red-500">{error}</div>;
  }

  if (keywords.length === 0 && sentimentKeywords.positive.length === 0 && sentimentKeywords.negative.length === 0) {
    return (
      <div className="py-8 text-center">
        No keyword data available for r/{subreddit} in the selected timeframe.
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4 text-sm bg-gray-100 rounded-lg p-2 flex justify-center">
        <div className="inline-flex rounded-lg shadow-sm" role="group">
          <button
            type="button"
            className={`px-4 py-2 text-sm font-medium rounded-l-lg ${
              activeTab === 'all'
                ? 'bg-indigo-600 text-white'
                : 'bg-white hover:bg-gray-100 text-gray-800'
            }`}
            onClick={() => setActiveTab('all')}
          >
            All Keywords
          </button>
          <button
            type="button"
            className={`px-4 py-2 text-sm font-medium ${
              activeTab === 'positive'
                ? 'bg-green-600 text-white'
                : 'bg-white hover:bg-gray-100 text-gray-800'
            }`}
            onClick={() => setActiveTab('positive')}
          >
            Positive
          </button>
          <button
            type="button"
            className={`px-4 py-2 text-sm font-medium rounded-r-lg ${
              activeTab === 'negative'
                ? 'bg-red-600 text-white'
                : 'bg-white hover:bg-gray-100 text-gray-800'
            }`}
            onClick={() => setActiveTab('negative')}
          >
            Negative
          </button>
        </div>
      </div>

      {activeTab === 'all' && (
        <div className="mb-8">
          <h3 className="text-lg font-medium mb-4">Top Keywords for r/{subreddit}</h3>
          <div className="bg-white rounded-lg shadow overflow-hidden p-4">
            <WordCloud 
              subreddit={subreddit} 
              timeframe={timeframe}
              height={350}
              width={700}
            />
          </div>
        </div>
      )}

      {activeTab === 'positive' && (
        <div>
          <h3 className="text-lg font-medium mb-4 text-green-700">Positive Sentiment Keywords</h3>
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-green-500">
            {sentimentKeywords.positive.length > 0 ? (
              <WordCloud 
                subreddit={subreddit} 
                timeframe={timeframe}
                initialActiveTab="positive"
                height={400}
              />
            ) : (
              <p className="text-center py-8 text-gray-500">No positive keywords available</p>
            )}
          </div>
        </div>
      )}

      {activeTab === 'negative' && (
        <div>
          <h3 className="text-lg font-medium mb-4 text-red-700">Negative Sentiment Keywords</h3>
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-red-500">
            {sentimentKeywords.negative.length > 0 ? (
              <WordCloud 
                subreddit={subreddit} 
                timeframe={timeframe}
                initialActiveTab="negative"
                height={400}
              />
            ) : (
              <p className="text-center py-8 text-gray-500">No negative keywords available</p>
            )}
          </div>
        </div>
      )}
      
      <div className="mt-6 p-4 bg-gray-100 rounded-lg">
        <h3 className="font-semibold text-gray-800 text-lg mb-2">Keyword Analysis</h3>
        <p className="text-gray-600 text-sm">
          {activeTab === 'positive' && 
            "These are the most frequently used words in positive comments and submissions."}
          {activeTab === 'negative' && 
            "These are the most frequently used words in negative comments and submissions."}
          {activeTab === 'all' && 
            "These are the most frequently used words across all submissions and comments. Words are sized based on frequency."}
        </p>
        <p className="text-gray-600 text-sm mt-2">
          When analyzing sentiment, these keywords can help identify the topics that drive positive and negative discussions.
        </p>
      </div>
    </div>
  );
};

export default KeywordPanel; 