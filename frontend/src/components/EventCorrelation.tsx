import React, { useState, useEffect } from 'react';
import { fetchEventCorrelation } from '../api/api';

interface EventCorrelationProps {
  subreddit: string;
  startDate: string;
  endDate: string;
  contentType?: string;
  onEventSelect?: (eventDate: string) => void;
}

const EventCorrelation: React.FC<EventCorrelationProps> = ({ 
  subreddit, 
  startDate, 
  endDate, 
  contentType = 'submissions',
  onEventSelect
}) => {
  const [correlations, setCorrelations] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const getEventCorrelation = async () => {
      if (!subreddit) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const data = await fetchEventCorrelation(subreddit, startDate, endDate, contentType);
        setCorrelations(data);
      } catch (err) {
        console.error('Error fetching event correlation:', err);
        setError('Failed to load event correlation data');
      } finally {
        setLoading(false);
      }
    };

    getEventCorrelation();
  }, [subreddit, startDate, endDate, contentType]);

  const handleEventClick = (eventDate: string) => {
    if (onEventSelect) {
      onEventSelect(eventDate);
    }
  };

  if (loading) {
    return <div className="flex justify-center py-8"><div className="scale-spinner"></div></div>;
  }

  if (error) {
    return <div className="text-red-500 text-center py-8">{error}</div>;
  }

  if (correlations.length === 0) {
    return (
      <div className="text-center py-8">
        <div className="bg-[var(--scale-bg-light)] p-8 rounded-lg">
          <h3 className="scale-heading-3 mb-2">No Event Correlations Available</h3>
          <p className="scale-text">
            No correlation data is available for this period and subreddit combination.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="scale-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Event</th>
              <th>Category</th>
              <th>Impact</th>
              <th>Keywords</th>
            </tr>
          </thead>
          <tbody>
            {correlations.map((item, index) => (
              <tr key={index} onClick={() => handleEventClick(item.event.date)} style={{ cursor: 'pointer' }}>
                <td className="whitespace-nowrap">{item.event.date}</td>
                <td className="font-medium text-[var(--scale-text-primary)]">{item.event.event}</td>
                <td>
                  <span className={`scale-badge ${getCategoryBadgeClass(item.event.category)}`}>
                    {item.event.category}
                  </span>
                </td>
                <td>
                  <div className="flex items-center">
                    <span className={`${getSentimentColor(item.sentiment_change)}`}>
                      {(item.sentiment_change > 0 ? '+' : '') + item.sentiment_change.toFixed(2)}
                    </span>
                    <SentimentArrow value={item.sentiment_change} />
                  </div>
                </td>
                <td>
                  <div className="flex flex-wrap gap-1">
                    {item.related_keywords.map((keyword: string, i: number) => (
                      <span key={i} className="scale-badge scale-badge-blue">{keyword}</span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      <div className="mt-6 p-4 bg-[var(--scale-bg-light)] rounded-lg">
        <h3 className="font-semibold text-[var(--scale-text-primary)] text-lg mb-2">About Event Impact Analysis</h3>
        <p className="scale-text">
          This analysis shows how key events correlate with changes in sentiment across the selected subreddit. 
          A positive impact score indicates a positive shift in sentiment following the event, while a negative score 
          indicates a decrease in sentiment. The keywords represent terms frequently associated with discussions about these events.
        </p>
        <p className="scale-text mt-2">
          <strong>Content type:</strong> {contentType === 'submissions' ? 'Posts' : 'Comments'}
        </p>
      </div>
    </div>
  );
};

// Helper components
const SentimentArrow: React.FC<{ value: number }> = ({ value }) => {
  if (Math.abs(value) < 0.05) return null;
  
  return value > 0 
    ? <svg className="h-5 w-5 ml-1 text-green-500" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z" clipRule="evenodd"></path></svg>
    : <svg className="h-5 w-5 ml-1 text-red-500" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 12.586V5a1 1 0 012 0v7.586l2.293-2.293a1 1 0 011.414 0z" clipRule="evenodd"></path></svg>;
};

// Helper functions
const getCategoryBadgeClass = (category: string): string => {
  const categories: { [key: string]: string } = {
    'politics': 'scale-badge-blue',
    'platform': 'scale-badge-purple',
    'technology': 'scale-badge-green',
    'gaming': 'scale-badge-red',
    'economic': 'scale-badge-yellow'
  };
  
  return categories[category] || 'scale-badge-blue';
};

const getSentimentColor = (value: number): string => {
  if (value > 0.1) return 'text-green-600 font-semibold';
  if (value < -0.1) return 'text-red-600 font-semibold';
  return 'text-gray-600';
};

export default EventCorrelation; 