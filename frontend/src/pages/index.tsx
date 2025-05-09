import { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import SubredditSelector from '../components/SubredditSelector';
import DateRangeSelector from '../components/DateRangeSelector';
import SentimentTimeseries from '../components/SentimentTimeseries';
import WordCloud from '../components/WordCloud';
import { 
  fetchSubreddits, 
  fetchEvents, 
  fetchGeneratedEvents,
  fetchSentiment, 
  fetchKeywords, 
  SentimentData,
  EventData
} from '../api/api';
import styles from '../styles/Home.module.css';

export default function Home() {
  const [subreddits, setSubreddits] = useState<string[]>([]);
  const [selectedSubreddit, setSelectedSubreddit] = useState<string>('politics');
  const [startDate, setStartDate] = useState<string>('2019-10-01');
  const [endDate, setEndDate] = useState<string>('2019-11-30');
  const [events, setEvents] = useState<EventData[]>([]);
  const [generatedEvents, setGeneratedEvents] = useState<EventData[]>([]);
  const [recentPosts, setRecentPosts] = useState<SentimentData[]>([]);
  const [contentType, setContentType] = useState<string>('submissions');
  const [showGeneratedEvents, setShowGeneratedEvents] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(true);

  // Fetch subreddits
  useEffect(() => {
    const fetchData = async () => {
      try {
        const subredditsData = await fetchSubreddits();
        setSubreddits(subredditsData);
        if (subredditsData.length > 0 && !selectedSubreddit) {
          setSelectedSubreddit(subredditsData[0]);
        }
      } catch (error) {
        console.error('Error fetching subreddits:', error);
      }
    };
    
    fetchData();
  }, []);

  // Fetch data based on selections
  useEffect(() => {
    const fetchData = async () => {
      if (!selectedSubreddit) return;
      
      setLoading(true);
      try {
        // Fetch recent posts data
        const sentimentData = await fetchSentiment(
          selectedSubreddit, 
          startDate, 
          endDate,
          contentType
        );
        setRecentPosts(sentimentData);
        
        // Fetch events
        const eventsData = await fetchEvents(startDate, endDate);
        setEvents(eventsData);
        
        // Fetch generated events
        const generatedEventsData = await fetchGeneratedEvents(
          selectedSubreddit,
          startDate,
          endDate,
          contentType
        );
        setGeneratedEvents(generatedEventsData);
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [selectedSubreddit, startDate, endDate, contentType]);

  const handleSubredditChange = (subreddit: string) => {
    setSelectedSubreddit(subreddit);
  };

  const handleDateRangeChange = (start: string, end: string) => {
    setStartDate(start);
    setEndDate(end);
  };
  
  const handleContentTypeChange = (type: string) => {
    setContentType(type);
  };

  const getAverageSentiment = () => {
    if (recentPosts.length === 0) return 0;
    
    const totalWeightedSentiment = recentPosts.reduce(
      (sum, post) => sum + post.avg_sentiment * post.post_count, 
      0
    );
    const totalPosts = recentPosts.reduce((sum, post) => sum + post.post_count, 0);
    
    return totalPosts ? (totalWeightedSentiment / totalPosts) : 0;
  };

  const getSentimentTrendIcon = () => {
    const avgSentiment = getAverageSentiment();
    
    if (avgSentiment > 0.2) return '📈';
    if (avgSentiment < -0.2) return '📉';
    return '📊';
  };

  const getSentimentDescription = () => {
    const avgSentiment = getAverageSentiment();
    
    if (avgSentiment > 0.5) return 'Very Positive';
    if (avgSentiment > 0.2) return 'Positive';
    if (avgSentiment > -0.2) return 'Neutral';
    if (avgSentiment > -0.5) return 'Negative';
    return 'Very Negative';
  };

  // Combine all events for display
  const allEvents = showGeneratedEvents ? 
    [...events, ...generatedEvents] : 
    events;
    
  // Get total post count
  const totalPostCount = recentPosts.reduce((sum, post) => sum + post.post_count, 0);

  return (
    <div className={styles.container}>
      <Head>
        <title>Reddit Meltdown</title>
        <meta name="description" content="Analyze Reddit sentiment across different events" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <header className={styles.header}>
        <div className={styles.headerContent}>
          <h1 className={styles.title}>Reddit Meltdown</h1>
          <Link href="/dashboard" className={styles.dashboardButton}>
            Advanced Dashboard
          </Link>
        </div>
      </header>

      <main className={styles.mainContent}>
        <div className={styles.selectionPanel}>
          <div className={styles.selectionControls}>
            <div className={styles.controlGroup}>
              <label className={styles.label}>Subreddit</label>
              <SubredditSelector 
                subreddits={subreddits} 
                selectedSubreddit={selectedSubreddit} 
                onSubredditChange={handleSubredditChange} 
              />
            </div>
            
            <div className={styles.controlGroup}>
              <label className={styles.label}>Date Range</label>
              <DateRangeSelector 
                startDate={startDate} 
                endDate={endDate} 
                onDateChange={handleDateRangeChange} 
              />
            </div>
            
            <div className={styles.controlGroup}>
              <label className={styles.label}>Content Type</label>
              <select 
                className={styles.select}
                value={contentType}
                onChange={(e) => handleContentTypeChange(e.target.value)}
              >
                <option value="submissions">Posts</option>
                <option value="comments">Comments</option>
              </select>
            </div>
            
            <div className={styles.controlGroup}>
              <label className={styles.checkboxContainer}>
                <input
                  type="checkbox"
                  checked={showGeneratedEvents}
                  onChange={(e) => setShowGeneratedEvents(e.target.checked)}
                  className={styles.checkbox}
                />
                <span className={styles.checkboxLabel}>Include Dynamic Events</span>
              </label>
              <span className={styles.helpText}>
                Automatically detect significant sentiment shifts
              </span>
            </div>
          </div>
        </div>

        <div className={styles.summary}>
          <div className={styles.summaryContent}>
            <div className={styles.summaryHeader}>
              <h2 className={styles.subtitle}>Sentiment Analysis Dashboard</h2>
              <p>Analyzing Reddit's sentiment evolution across major events</p>
            </div>
            
            <div className={styles.statsGrid}>
              <div className={styles.statsCard}>
                <div className={styles.statsIcon}>{getSentimentTrendIcon()}</div>
                <div className={styles.statsContent}>
                  <h3 className={styles.statsTitle}>Average Sentiment</h3>
                  <p className={styles.statsValue}>{getSentimentDescription()}</p>
                  <p className={styles.statsSubtext}>
                    {getAverageSentiment().toFixed(2)} on scale from -1 to 1
                  </p>
                </div>
              </div>
              
              <div className={styles.statsCard}>
                <div className={styles.statsIcon}>📊</div>
                <div className={styles.statsContent}>
                  <h3 className={styles.statsTitle}>Data Overview</h3>
                  <p className={styles.statsValue}>{totalPostCount.toLocaleString()} {contentType}</p>
                  <p className={styles.statsSubtext}>
                    From {startDate} to {endDate}
                  </p>
                </div>
              </div>
              
              <div className={styles.statsCard}>
                <div className={styles.statsIcon}>🔍</div>
                <div className={styles.statsContent}>
                  <h3 className={styles.statsTitle}>Events Analyzed</h3>
                  <p className={styles.statsValue}>{events.length} official</p>
                  <p className={styles.statsSubtext}>
                    {generatedEvents.length > 0 && showGeneratedEvents ? 
                      `Plus ${generatedEvents.length} dynamically detected` : 
                      'No generated events detected'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Main content grid */}
        <div className={styles.insightsGrid}>
          {/* Left column */}
          <div className={styles.col8}>
            <div className={styles.card}>
              <div className={styles.cardHeader}>
                <h3 className={styles.cardTitle}>Sentiment Timeline with Events</h3>
                <div className={styles.cardActions}>
                  <Link
                    href={{
                      pathname: '/dashboard',
                      query: {
                        subreddit: selectedSubreddit,
                        startDate,
                        endDate,
                        contentType
                      }
                    }}
                    className={styles.cardLink}
                  >
                    Detailed View
                  </Link>
                </div>
              </div>
              <div className={styles.cardBody}>
                <div className={styles.chartContainer}>
                  <SentimentTimeseries
                    subreddit={selectedSubreddit}
                    startDate={startDate}
                    endDate={endDate}
                    contentType={contentType}
                    showVisualization={false}
                  />
                </div>
              </div>
              <div className={styles.cardFooter}>
                <div className={styles.cardFooterText}>
                  Timeline shows sentiment trends overlaid with {allEvents.length} events
                </div>
              </div>
            </div>

            <div className={styles.grid}>
              {/* Keywords Panel - now WordCloud */}
              <div className={styles.col6}>
                <div className={styles.card}>
                  <div className={styles.cardHeader}>
                    <h3 className={styles.cardTitle}>Top Keywords</h3>
                  </div>
                  <div className={styles.cardBody}>
                    <WordCloud
                      subreddit={selectedSubreddit}
                      timeframe="weekly"
                    />
                  </div>
                </div>
              </div>

              <div className={styles.col6}>
                <div className={styles.card}>
                  <div className={styles.cardHeader}>
                    <h3 className={styles.cardTitle}>Recent Events</h3>
                    {generatedEvents.length > 0 && showGeneratedEvents && (
                      <div className={styles.eventCount}>
                        <span className={styles.eventCountBadge}>{generatedEvents.length}</span> 
                        <span>dynamic events found</span>
                      </div>
                    )}
                  </div>
                  <div className={styles.cardBody}>
                    <div className={styles.eventsList}>
                      {loading ? (
                        <div className={styles.loadingIndicator}>
                          <div className={styles.spinner}></div>
                          <span>Loading events...</span>
                        </div>
                      ) : allEvents.length > 0 ? (
                        allEvents
                          .sort((a, b) => b.date.localeCompare(a.date))
                          .slice(0, 5)
                          .map((event, index) => (
                            <div key={index} className={styles.eventItem}>
                              <div className={styles.eventDate}>{event.date}</div>
                              <div className={styles.eventContent}>
                                <p className={styles.eventText}>{event.event}</p>
                                <div className={styles.eventMeta}>
                                  <span className={`${styles.eventCategory} ${styles[`event${event.category.charAt(0).toUpperCase() + event.category.slice(1)}`]}`}>
                                    {event.category}
                                  </span>
                                  {event.impact_score && (
                                    <span className={styles.eventImpact}>
                                      Impact: {event.impact_score.toFixed(2)}
                                    </span>
                                  )}
                                  {/* Show marker for generated events */}
                                  {generatedEvents.some(e => e.date === event.date && e.event === event.event) && (
                                    <span className={styles.eventGenerated} title="Dynamically detected event">🔍</span>
                                  )}
                                </div>
                              </div>
                            </div>
                          ))
                      ) : (
                        <div className={styles.noData}>No events found for the selected time period</div>
                      )}
                    </div>
                    <div className={styles.cardActions} style={{ marginTop: '1rem' }}>
                      <Link
                        href={{
                          pathname: '/dashboard',
                          query: {
                            subreddit: selectedSubreddit,
                            startDate,
                            endDate,
                            contentType,
                            tab: 'correlations'
                          }
                        }}
                        className={styles.cardLink}
                      >
                        View All Events
                      </Link>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right column */}
          <div className={styles.col4}>
            <div className={styles.card}>
              <div className={styles.cardHeader}>
                <h3 className={styles.cardTitle}>About this Project</h3>
              </div>
              <div className={styles.cardBody}>
                <p className={styles.cardText}>
                  Reddit Meltdown analyzes sentiment trends across different subreddits, mapping them against significant events.
                </p>
                <p className={styles.cardText}>
                  The platform combines data from millions of Reddit posts and comments, applying natural language processing to extract sentiment and key topics.
                </p>
                <div className={styles.featureList}>
                  <div className={styles.featureItem}>
                    <div className={styles.featureIcon}>📊</div>
                    <div className={styles.featureText}>
                      <h4>Sentiment Analysis</h4>
                      <p>Track how community sentiment changes over time</p>
                    </div>
                  </div>
                  <div className={styles.featureItem}>
                    <div className={styles.featureIcon}>📅</div>
                    <div className={styles.featureText}>
                      <h4>Event Correlation</h4>
                      <p>See how major events impact Reddit discussions</p>
                    </div>
                  </div>
                  <div className={styles.featureItem}>
                    <div className={styles.featureIcon}>🔍</div>
                    <div className={styles.featureText}>
                      <h4>Dynamic Event Detection</h4>
                      <p>Automatically identify significant sentiment shifts</p>
                    </div>
                  </div>
                  <div className={styles.featureItem}>
                    <div className={styles.featureIcon}>💬</div>
                    <div className={styles.featureText}>
                      <h4>Content Analysis</h4>
                      <p>Compare trends between posts and comments</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className={styles.card}>
              <div className={styles.cardHeader}>
                <h3 className={styles.cardTitle}>Data Sources</h3>
              </div>
              <div className={styles.cardBody}>
                <div className={styles.dataSourceItem}>
                  <h4>Official Events</h4>
                  <p>Curated collection of notable events from 2019-2020 including political, technological, and platform-specific occurrences.</p>
                </div>
                <div className={styles.dataSourceItem}>
                  <h4>Generated Events</h4>
                  <p>Automatically detected significant sentiment shifts in the data, with contextual keywords to explain potential causes.</p>
                </div>
                <div className={styles.dataSourceItem}>
                  <h4>Reddit Content</h4>
                  <p>Historical Reddit submissions and comments processed through sentiment analysis and tokenization.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      <footer className={styles.footer}>
        <div className={styles.footerContent}>
          <p>Reddit Meltdown - Visualizing Reddit Sentiment Analysis</p>
        </div>
      </footer>
    </div>
  );
} 