import { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import SubredditSelector from '../components/SubredditSelector';
import DateRangeSelector from '../components/DateRangeSelector';
import SentimentTimeseries from '../components/SentimentTimeseries';
import EventCorrelation from '../components/EventCorrelation';
import ConversationSamples from '../components/ConversationSamples';
import KeywordPanel from '../components/KeywordPanel';
import { fetchSubreddits, fetchEvents, fetchGeneratedEvents } from '../api/api';
import styles from '../styles/Dashboard.module.css';
import Button from '../components/Button';

interface EventData {
  date: string;
  event: string;
  category: string;
  impact_score?: number;
}

export default function Dashboard() {
  const router = useRouter();
  const [subreddits, setSubreddits] = useState<string[]>([]);
  const [selectedSubreddit, setSelectedSubreddit] = useState<string>('');
  const [startDate, setStartDate] = useState<string>('2019-10-01');
  const [endDate, setEndDate] = useState<string>('2019-11-30');
  const [selectedEventDate, setSelectedEventDate] = useState<string | null>(null);
  const [contentType, setContentType] = useState<string>('submissions');
  const [activeTab, setActiveTab] = useState<string>('timeseries');
  const [recentEvents, setRecentEvents] = useState<EventData[]>([]);
  const [generatedEvents, setGeneratedEvents] = useState<EventData[]>([]);
  const [showGeneratedEvents, setShowGeneratedEvents] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    // Fetch available subreddits on component mount
    const getSubreddits = async () => {
      try {
        const data = await fetchSubreddits();
        setSubreddits(data);
        if (data.length > 0 && !selectedSubreddit) {
          setSelectedSubreddit(data[0]);
        }
      } catch (error) {
        console.error('Error fetching subreddits:', error);
      }
    };

    getSubreddits();
  }, [selectedSubreddit]);

  // Handle query parameters from the home page
  useEffect(() => {
    if (router.isReady) {
      const { subreddit, startDate: queryStartDate, endDate: queryEndDate, contentType: queryContentType } = router.query;
      
      if (subreddit && typeof subreddit === 'string') {
        setSelectedSubreddit(subreddit);
      }
      
      if (queryStartDate && typeof queryStartDate === 'string') {
        setStartDate(queryStartDate);
      }
      
      if (queryEndDate && typeof queryEndDate === 'string') {
        setEndDate(queryEndDate);
      }
      
      if (queryContentType && typeof queryContentType === 'string') {
        setContentType(queryContentType);
      }
    }
  }, [router.isReady, router.query]);

  // Fetch events
  useEffect(() => {
    const getEvents = async () => {
      if (!startDate || !endDate) return;
      
      setLoading(true);
      try {
        // Fetch predefined events
        const events = await fetchEvents(startDate, endDate);
        setRecentEvents(events);
        
        // Fetch dynamically generated events if we have a selected subreddit
        if (selectedSubreddit) {
          const generated = await fetchGeneratedEvents(
            selectedSubreddit,
            startDate,
            endDate,
            contentType,
            0.1 // min sentiment change
          );
          setGeneratedEvents(generated);
        }
      } catch (error) {
        console.error('Error fetching events:', error);
      } finally {
        setLoading(false);
      }
    };

    getEvents();
  }, [startDate, endDate, selectedSubreddit, contentType]);

  const handleSubredditChange = (subreddit: string) => {
    setSelectedSubreddit(subreddit);
    // Reset selected event when subreddit changes
    setSelectedEventDate(null);
  };

  const handleDateChange = (start: string, end: string) => {
    setStartDate(start);
    setEndDate(end);
    // Reset selected event when date range changes
    setSelectedEventDate(null);
  };

  const handleEventSelect = (date: string) => {
    setSelectedEventDate(date);
    // Switch to conversations tab when an event is selected
    setActiveTab('conversations');
  };

  const handleContentTypeChange = (type: string) => {
    setContentType(type);
  };

  const getEventCategoryClass = (category: string) => {
    switch (category?.toLowerCase()) {
      case 'politics':
        return styles.eventPolitics;
      case 'economic':
        return styles.eventEconomic;
      case 'pandemic':
        return styles.eventPandemic;
      case 'technology':
        return styles.eventTechnology;
      case 'platform':
        return styles.eventPlatform;
      case 'gaming':
        return styles.eventGaming;
      case 'entertainment':
        return styles.eventEntertainment;
      case 'sports':
        return styles.eventSports;
      case 'news':
        return styles.eventNews;
      case 'community':
        return styles.eventCommunity;
      default:
        return '';
    }
  };

  // Combine predefined and generated events
  const allEvents = showGeneratedEvents ? 
    [...recentEvents, ...generatedEvents] : 
    recentEvents;

  // Sort by date
  allEvents.sort((a, b) => a.date.localeCompare(b.date));

  return (
    <div className={styles.container}>
      <Head>
        <title>Reddit Meltdown Dashboard</title>
        <meta name="description" content="In-depth analysis of sentiment trends and events on Reddit" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <header className={styles.header}>
        <div className={styles.headerContent}>
          <h1 className={styles.title}>Reddit Meltdown Dashboard</h1>
          <Link href="/" className={styles.button}>
            Back to Home
          </Link>
        </div>
      </header>

      <main className={styles.mainContent}>
        <div className={styles.grid}>
          <div className={styles.col3}>
            <div className={styles.card}>
              <div className={styles.cardBody}>
                <label className={styles.label}>Select Subreddit</label>
                <SubredditSelector 
                  subreddits={subreddits}
                  selectedSubreddit={selectedSubreddit}
                  onSubredditChange={handleSubredditChange}
                />
              </div>
            </div>
          </div>
          <div className={styles.col3}>
            <div className={styles.card}>
              <div className={styles.cardBody}>
                <label className={styles.label}>Date Range</label>
                <DateRangeSelector
                  startDate={startDate}
                  endDate={endDate}
                  onDateChange={handleDateChange}
                />
              </div>
            </div>
          </div>
          <div className={styles.col3}>
            <div className={styles.card}>
              <div className={styles.cardBody}>
                <label className={styles.label}>Content Type</label>
                <select
                  className={styles.select}
                  value={contentType}
                  onChange={(e) => handleContentTypeChange(e.target.value)}
                >
                  <option value="submissions">Submissions</option>
                  <option value="comments">Comments</option>
                </select>
              </div>
            </div>
          </div>
          <div className={styles.col3}>
            <div className={styles.card}>
              <div className={styles.cardBody}>
                <label className={styles.label}>Event Sources</label>
                <div className={styles.checkboxGroup}>
                  <label className={styles.checkboxLabel}>
                    <input 
                      type="checkbox" 
                      checked={showGeneratedEvents}
                      onChange={(e) => setShowGeneratedEvents(e.target.checked)}
                      className={styles.checkbox}
                    />
                    <span>Include Dynamic Events</span>
                  </label>
                  <div className={styles.helpText}>
                    Dynamic events are generated based on sentiment changes in the selected subreddit
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className={styles.grid}>
          <div className={styles.col8}>
            {/* Tab Navigation */}
            <div className="flex flex-wrap gap-2 mb-4 border-b border-gray-200 pb-2">
              <Button
                onClick={() => setActiveTab('timeseries')}
                variant={activeTab === 'timeseries' ? 'primary' : 'outline'}
                size="sm" 
              >
                Sentiment Timeseries
              </Button>
              <Button
                onClick={() => setActiveTab('correlations')}
                variant={activeTab === 'correlations' ? 'primary' : 'outline'}
                size="sm"
              >
                Event Correlations
              </Button>
              <Button
                onClick={() => setActiveTab('conversations')}
                variant={activeTab === 'conversations' ? 'primary' : 'outline'}
                size="sm"
                disabled={!selectedEventDate}
              >
                Conversations
              </Button>
              <Button
                onClick={() => setActiveTab('keywords')}
                variant={activeTab === 'keywords' ? 'primary' : 'outline'}
                size="sm"
              >
                Keywords
              </Button>
            </div>

            {/* Tab Content */}
            <div className={styles.card}>
              <div className={styles.cardBody}>
                {activeTab === 'timeseries' && (
                  <SentimentTimeseries
                    subreddit={selectedSubreddit}
                    startDate={startDate}
                    endDate={endDate}
                    contentType={contentType}
                    onEventSelect={handleEventSelect}
                    initialViewMode="chart"
                  />
                )}

                {activeTab === 'correlations' && (
                  <EventCorrelation
                    subreddit={selectedSubreddit}
                    startDate={startDate}
                    endDate={endDate}
                    contentType={contentType}
                    onEventSelect={handleEventSelect}
                  />
                )}

                {activeTab === 'conversations' && selectedEventDate && (
                  <ConversationSamples
                    subreddit={selectedSubreddit}
                    eventDate={selectedEventDate}
                  />
                )}

                {activeTab === 'keywords' && (
                  <KeywordPanel
                    subreddit={selectedSubreddit}
                    timeframe="weekly"
                  />
                )}
              </div>
            </div>
          </div>

          <div className={styles.col4}>
            <div className={styles.card}>
              <div className={styles.cardHeader}>
                <div className={styles.cardHeaderTitle}>
                  <h2 className={styles.sectionTitle}>Recent Events</h2>
                  {generatedEvents.length > 0 && showGeneratedEvents && (
                    <div className={styles.eventCount}>
                      <span className={styles.eventCountBadge}>{generatedEvents.length}</span> dynamic events found
                    </div>
                  )}
                </div>
              </div>
              <div className={`${styles.cardBody} ${styles.eventsList}`}>
                {loading ? (
                  <div className={styles.loading}>Loading events...</div>
                ) : allEvents.length > 0 ? (
                  allEvents.map((event, index) => (
                    <div 
                      key={`${event.date}-${index}`} 
                      className={`${styles.eventItem} ${selectedEventDate === event.date ? styles.eventItemSelected : ''}`}
                      onClick={() => handleEventSelect(event.date)}
                    >
                      <div className={styles.eventDate}>{event.date}</div>
                      <div className={styles.eventContent}>
                        <div className={styles.eventText}>{event.event}</div>
                        <div className={styles.eventMeta}>
                          <span className={`${styles.eventCategory} ${getEventCategoryClass(event.category)}`}>
                            {event.category}
                          </span>
                          {event.impact_score && (
                            <span className={styles.eventImpact}>
                              Impact: {event.impact_score.toFixed(2)}
                            </span>
                          )}
                          {/* Show icon for generated events */}
                          {generatedEvents.some(e => e.date === event.date && e.event === event.event) && (
                            <span className={styles.eventGenerated} title="Dynamically detected event">
                              🔍
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className={styles.noEvents}>No events found in this date range</div>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>

      <footer className={styles.footer}>
        <div className={styles.footerContent}>
          <p>Reddit Meltdown Analysis - Data 228 Project</p>
        </div>
      </footer>
    </div>
  );
} 