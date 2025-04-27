import { useState, useEffect } from 'react';
import Head from 'next/head';
import SentimentChart from '../components/SentimentChart';
import SubredditSelector from '../components/SubredditSelector';
import DateRangeSelector from '../components/DateRangeSelector';
import EventOverlay from '../components/EventOverlay';
import KeywordPanel from '../components/KeywordPanel';
import { fetchSubreddits } from '../api/api';

export default function Home() {
  const [subreddits, setSubreddits] = useState<string[]>([]);
  const [selectedSubreddit, setSelectedSubreddit] = useState<string>('');
  const [startDate, setStartDate] = useState<string>('2020-01-01');
  const [endDate, setEndDate] = useState<string>('2022-12-31');
  const [showEvents, setShowEvents] = useState<boolean>(true);
  const [selectedEventCategories, setSelectedEventCategories] = useState<string[]>([
    'politics', 'pandemic', 'economic', 'technology'
  ]);
  const [timeframe, setTimeframe] = useState<string>('monthly');

  useEffect(() => {
    // Fetch available subreddits on component mount
    const getSubreddits = async () => {
      try {
        const data = await fetchSubreddits();
        setSubreddits(data);
        if (data.length > 0) {
          setSelectedSubreddit(data[0]);
        }
      } catch (error) {
        console.error('Error fetching subreddits:', error);
      }
    };

    getSubreddits();
  }, []);

  const handleSubredditChange = (subreddit: string) => {
    setSelectedSubreddit(subreddit);
  };

  const handleDateChange = (start: string, end: string) => {
    setStartDate(start);
    setEndDate(end);
  };

  const handleEventToggle = () => {
    setShowEvents(!showEvents);
  };

  const handleEventCategoryChange = (categories: string[]) => {
    setSelectedEventCategories(categories);
  };

  const handleTimeframeChange = (newTimeframe: string) => {
    setTimeframe(newTimeframe);
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <Head>
        <title>Reddit Meltdown Analysis</title>
        <meta name="description" content="Analyzing sentiment trends across Reddit subreddits" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <header className="bg-indigo-600 shadow-lg">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-white">Reddit Meltdown Analysis</h1>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="flex flex-col md:flex-row gap-4 mb-6">
            <div className="flex-1">
              <SubredditSelector 
                subreddits={subreddits}
                selectedSubreddit={selectedSubreddit}
                onSubredditChange={handleSubredditChange}
              />
            </div>
            <div className="flex-1">
              <DateRangeSelector
                startDate={startDate}
                endDate={endDate}
                onDateChange={handleDateChange}
              />
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-medium text-gray-900">Sentiment Over Time</h2>
                <div className="flex items-center">
                  <div className="mr-4">
                    <label className="inline-flex items-center">
                      <input
                        type="checkbox"
                        className="form-checkbox h-5 w-5 text-indigo-600"
                        checked={showEvents}
                        onChange={handleEventToggle}
                      />
                      <span className="ml-2 text-gray-700">Show Events</span>
                    </label>
                  </div>
                </div>
              </div>
              
              <SentimentChart
                subreddit={selectedSubreddit}
                startDate={startDate}
                endDate={endDate}
              />
              
              {showEvents && (
                <EventOverlay
                  startDate={startDate}
                  endDate={endDate}
                  selectedCategories={selectedEventCategories}
                  onCategoryChange={handleEventCategoryChange}
                />
              )}
            </div>
          </div>

          <div className="mt-6">
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <h2 className="text-lg font-medium text-gray-900 mb-4">Top Keywords</h2>
                <div className="flex mb-4">
                  <select
                    className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
                    value={timeframe}
                    onChange={(e) => handleTimeframeChange(e.target.value)}
                  >
                    <option value="monthly">Monthly</option>
                    <option value="quarterly">Quarterly</option>
                    <option value="yearly">Yearly</option>
                    <option value="all">All Time</option>
                  </select>
                </div>
                
                <KeywordPanel
                  subreddit={selectedSubreddit}
                  timeframe={timeframe}
                />
              </div>
            </div>
          </div>
        </div>
      </main>

      <footer className="bg-white">
        <div className="max-w-7xl mx-auto py-6 px-4 overflow-hidden sm:px-6 lg:px-8">
          <p className="text-center text-base text-gray-500">
            Reddit Meltdown Analysis - Data 228 Project
          </p>
        </div>
      </footer>
    </div>
  );
} 