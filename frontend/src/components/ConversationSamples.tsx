import React, { useState, useEffect } from 'react';
import { fetchConversations } from '../api/api';

interface ConversationSamplesProps {
  subreddit: string;
  eventDate: string | null;
}

const ConversationSamples: React.FC<ConversationSamplesProps> = ({ subreddit, eventDate }) => {
  const [conversations, setConversations] = useState<any[]>([]);
  const [eventInfo, setEventInfo] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [contentFilter, setContentFilter] = useState<string>("all");

  useEffect(() => {
    const getConversations = async () => {
      if (!subreddit || !eventDate) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const data = await fetchConversations(subreddit, eventDate);
        setConversations(data.conversations || []);
        setEventInfo(data.event || null);
      } catch (err) {
        console.error('Error fetching conversations:', err);
        setError('Failed to load conversation data');
      } finally {
        setLoading(false);
      }
    };

    getConversations();
  }, [subreddit, eventDate]);

  const filteredConversations = conversations.filter(item => {
    if (contentFilter === "all") return true;
    return item.type === contentFilter;
  });

  if (!eventDate) {
    return (
      <div className="text-center py-8">
        <div className="bg-[var(--scale-bg-light)] p-8 rounded-lg">
          <h3 className="scale-heading-3 mb-2">No Event Selected</h3>
          <p className="scale-text">
            Select an event from the Sentiment Timeseries tab to view related conversations
          </p>
        </div>
      </div>
    );
  }

  if (loading) {
    return <div className="flex justify-center py-8"><div className="scale-spinner"></div></div>;
  }

  if (error) {
    return <div className="text-red-500 text-center py-8">{error}</div>;
  }

  if (conversations.length === 0) {
    return (
      <div className="text-center py-8">
        <div className="bg-[var(--scale-bg-light)] p-8 rounded-lg">
          <h3 className="scale-heading-3 mb-2">No conversations found</h3>
          <p className="scale-text">
            No conversations were found for this event. Try selecting a different event.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {eventInfo && (
        <div className="mb-6 bg-[var(--scale-bg-light)] p-5 rounded-lg">
          <h3 className="scale-heading-3 mb-1">{eventInfo.name}</h3>
          <div className="flex items-center gap-2">
            <span className="scale-badge scale-badge-blue">{eventInfo.date}</span>
            <span className="scale-badge scale-badge-purple">{eventInfo.category}</span>
          </div>
        </div>
      )}

      {/* Content type filter */}
      <div className="flex items-center gap-2 mb-4">
        <span className="text-sm font-medium text-[var(--scale-text-secondary)]">Filter by:</span>
        <div className="flex rounded-md overflow-hidden border border-[var(--scale-border)]">
          <button 
            className={`px-4 py-2 text-sm font-medium ${contentFilter === 'all' 
              ? 'bg-[var(--scale-accent)] text-white' 
              : 'bg-white text-[var(--scale-text-primary)]'}`}
            onClick={() => setContentFilter('all')}
          >
            All
          </button>
          <button 
            className={`px-4 py-2 text-sm font-medium ${contentFilter === 'submission' 
              ? 'bg-[var(--scale-accent)] text-white' 
              : 'bg-white text-[var(--scale-text-primary)]'}`}
            onClick={() => setContentFilter('submission')}
          >
            Posts
          </button>
          <button 
            className={`px-4 py-2 text-sm font-medium ${contentFilter === 'comment' 
              ? 'bg-[var(--scale-accent)] text-white' 
              : 'bg-white text-[var(--scale-text-primary)]'}`}
            onClick={() => setContentFilter('comment')}
          >
            Comments
          </button>
        </div>
      </div>

      {filteredConversations.length === 0 ? (
        <div className="text-center py-8">
          <div className="bg-[var(--scale-bg-light)] p-8 rounded-lg">
            <h3 className="scale-heading-3 mb-2">No conversations found</h3>
            <p className="scale-text">
              No conversations of this type were found. Try selecting a different filter.
            </p>
          </div>
        </div>
      ) : (
        filteredConversations.map((item, index) => (
          <div key={index} className="scale-card hover:shadow-lg transform transition-all duration-200">
            <div className="scale-card-body">
              {item.title && (
                <h4 className="font-semibold text-[var(--scale-text-primary)] text-lg mb-2">{item.title}</h4>
              )}
              <p className="scale-text whitespace-pre-line mb-3">{item.content}</p>
              <div className="flex justify-between items-center text-xs text-[var(--scale-text-light)]">
                <span className="flex items-center gap-2">
                  <span className="inline-flex items-center px-2 py-1 rounded-full bg-[var(--scale-bg-light)] font-medium">
                    u/{item.author}
                  </span>
                  {item.score !== undefined && (
                    <span className="inline-flex items-center px-2 py-1 rounded-full bg-[var(--scale-bg-light)]">
                      {item.score} points
                    </span>
                  )}
                  <span className={`inline-flex items-center px-2 py-1 rounded-full ${
                    item.type === 'submission' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'
                  }`}>
                    {item.type === 'submission' ? 'Post' : 'Comment'}
                  </span>
                </span>
                <span className="flex items-center gap-2">
                  <span>{item.date}</span>
                  {item.days_from_event !== undefined && (
                    <span className={`inline-flex items-center px-2 py-1 rounded-full ${item.days_from_event === 0 
                      ? 'bg-yellow-100 text-yellow-800 font-bold' 
                      : 'bg-[var(--scale-bg-light)]'}`}>
                      {item.days_from_event === 0 
                        ? 'day of event' 
                        : item.days_from_event > 0 
                          ? `+${item.days_from_event} days` 
                          : `${item.days_from_event} days`}
                    </span>
                  )}
                </span>
              </div>
              
              {item.sentiment !== undefined && (
                <div className="mt-3">
                  <span className={`text-xs px-3 py-1 rounded-full ${
                    item.sentiment > 0.2 ? 'scale-badge-green' :
                    item.sentiment < -0.2 ? 'scale-badge-red' :
                    'scale-badge-blue'
                  }`}>
                    Sentiment: {item.sentiment.toFixed(2)}
                  </span>
                </div>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
};

export default ConversationSamples; 