import React, { useState, useEffect, useCallback } from 'react';
import ReactWordcloud from 'react-wordcloud';
import { fetchKeywords, KeywordData } from '../api/api';

interface WordCloudProps {
  subreddit: string;
  timeframe: string;
}

interface WordCloudWord {
  text: string;
  value: number;
}

const WordCloud: React.FC<WordCloudProps> = ({ subreddit, timeframe }) => {
  const [words, setWords] = useState<WordCloudWord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [totalPostCount, setTotalPostCount] = useState<number>(0);

  useEffect(() => {
    const fetchKeywordData = async () => {
      if (!subreddit) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const data = await fetchKeywords(subreddit, timeframe);
        
        // Get post count if available
        if (data.length > 0 && data[0].post_count) {
          setTotalPostCount(data[0].post_count);
        }
        
        // Convert to format needed by react-wordcloud
        const wordCloudData = data.map(keyword => ({
          text: keyword.keyword,
          value: keyword.weight
        }));
        
        setWords(wordCloudData);
      } catch (err) {
        setError('Failed to load keyword data');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchKeywordData();
  }, [subreddit, timeframe]);

  // Wordcloud options with theme colors
  const options = {
    colors: [
      'var(--scale-accent)',
      'var(--scale-accent-light)',
      '#4a58e0',
      '#7986cb',
      '#9fa8da',
      '#6200ee',
      '#3700b3',
    ],
    enableTooltip: true,
    deterministic: true,
    fontFamily: 'Inter, system-ui, sans-serif',
    fontSizes: [16, 70],
    fontStyle: 'normal',
    fontWeight: 'bold',
    padding: 3,
    rotations: 2,
    rotationAngles: [0, 0], // Only horizontal text
    scale: 'sqrt',
    spiral: 'archimedean',
    transitionDuration: 1000
  };
  
  // Callbacks for interactions
  const getCallback = useCallback((callback: string) => {
    return function(word: WordCloudWord, event: React.MouseEvent) {
      if (callback === 'onWordClick') {
        console.log(`${word.text}: ${word.value}`);
      }
    };
  }, []);
  
  const callbacks = {
    getWordColor: (word: WordCloudWord) => {
      // More important words get more vibrant colors
      return word.value > 20 ? 'var(--scale-accent)' : '';
    },
    getWordTooltip: (word: WordCloudWord) => `${word.text}: ${Math.round(word.value)} occurrences`,
    onWordClick: getCallback('onWordClick'),
    onWordMouseOver: getCallback('onWordMouseOver'),
    onWordMouseOut: getCallback('onWordMouseOut')
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-16">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-[var(--scale-accent)]"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-red-500 text-center py-8 bg-red-50 rounded-lg p-4">
        <div className="mb-2">⚠️ Error</div>
        <div>{error}</div>
      </div>
    );
  }

  if (words.length === 0) {
    return (
      <div className="text-center py-8">
        <div className="bg-[var(--scale-bg-light)] p-8 rounded-lg">
          <h3 className="text-lg font-medium mb-2">No Keywords Available</h3>
          <p className="text-[var(--scale-text-secondary)]">
            No keyword data is available for r/{subreddit} in the selected timeframe.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ height: 350, width: '100%' }} className="bg-[var(--scale-bg-light)] rounded-lg px-2">
        <ReactWordcloud 
          words={words} 
          options={options} 
          callbacks={callbacks}
          maxWords={100}
        />
      </div>
      <div className="mt-4 text-right text-sm text-[var(--scale-text-light)]">
        <span>Based on {words.length} keywords from {totalPostCount.toLocaleString()} posts</span>
      </div>
    </div>
  );
};

export default WordCloud; 