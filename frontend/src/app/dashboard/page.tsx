// frontend/src/app/dashboard/page.tsx
"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useSession } from 'next-auth/react';
import Navbar from '@/components/Navbar';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import ResetDashboardConfirmationModal from '@/components/ResetDashboardConfirmationModal';

// Define types for the data we expect from the backend
interface WrongQuestionInfoClient {
  question_id: string;
  question_text: string;
  timestamp_marked_wrong: string;
}

interface DashboardDataClient {
  user_id: string;
  total_points: number;
  previous_session_points: number;
  points_history: Array<{ timestamp: string; points: number; topic_id?: string }>;
  last_5_wrong_questions: WrongQuestionInfoClient[];
}

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

export default function DashboardPage() {
  const { data: session, status: sessionStatus } = useSession();
  const [dashboardData, setDashboardData] = useState<DashboardDataClient | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isResetModalOpen, setIsResetModalOpen] = useState<boolean>(false);
  const [isResetting, setIsResetting] = useState<boolean>(false);

  const fetchDashboardData = async () => {
    if (sessionStatus === "authenticated" && session?.user?.id) {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch('/api/dashboard', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'X-User-ID': session.user.id,
          },
        });
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ message: "Failed to parse error response from API route." }));
          throw new Error(errorData.detail || `Failed to fetch dashboard data: ${response.status}`);
        }
        const data: DashboardDataClient = await response.json();
        setDashboardData(data);
      } catch (err: any) {
        console.error("Error fetching dashboard data:", err);
        setError(err.message || "Could not load dashboard data.");
      } finally {
        setIsLoading(false);
      }
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [sessionStatus, session]);

  const handleOpenResetModal = () => {
    setIsResetModalOpen(true);
  };

  const handleCloseResetModal = () => {
    setIsResetModalOpen(false);
  };

  const handleConfirmResetDashboard = async () => {
    if (!session?.user?.id) {
      setError("User not authenticated for reset.");
      setIsResetModalOpen(false);
      return;
    }
    setIsResetting(true);
    setError(null);
    try {
      const response = await fetch('/api/dashboard/reset', { // Updated to use the Next.js API route
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': session.user.id, // Pass user ID for backend to identify the user
        },
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: "Failed to parse error response from reset API." }));
        throw new Error(errorData.detail || `Failed to reset dashboard data: ${response.status}`);
      }
      // Reset successful
      setDashboardData(null); // Clear local data or re-fetch
      await fetchDashboardData(); // Re-fetch to get the new empty state
      setIsResetModalOpen(false);
    } catch (err: any) {
      console.error("Error resetting dashboard data:", err);
      setError(err.message || "Could not reset dashboard data.");
    } finally {
      setIsResetting(false);
    }
  };

  // Handle loading session state
  if (sessionStatus === "loading") {
    return (
      <>
        <Navbar />
        <div className="flex justify-center items-center min-h-screen pt-6 md:pt-8">
            <div className="text-xl text-gray-500">Loading session...</div>
        </div>
      </>
    );
  }

  // Handle unauthenticated state (though middleware should ideally redirect)
  if (sessionStatus === "unauthenticated") {
    return (
      <>
        <Navbar />
        <div className="flex flex-col items-center justify-center min-h-screen pt-6 md:pt-8 text-center">
          <p className="text-xl text-gray-700 mb-4">You need to be logged in to view the dashboard.</p>
          <Link href="/" className="px-6 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
            Go to Login
          </Link>
        </div>
      </>
    );
  }

  // Handle data loading state after session is authenticated
  if (isLoading && !dashboardData && !error) {
    return (
      <>
        <Navbar />
        <div className="flex justify-center items-center min-h-screen pt-6 md:pt-8">
            <div className="text-xl text-gray-500">Loading Dashboard Data...</div>
            {/* Optional: Add a spinner here */}
        </div>
      </>
    );
  }

  // Handle error state
  if (error) {
    return (
      <>
        <Navbar />
        <div className="container mx-auto p-4 md:p-6 min-h-screen pt-20 text-center">
          <h1 className="text-2xl font-bold text-red-600 mb-6">Error</h1>
          <p className="text-gray-700">{error}</p>
          <Link href="/home" className="mt-6 inline-block px-6 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
            Return to Main Page
          </Link>
        </div>
      </>
    );
  }
  
  // Handle no data state after loading and no error
  if (!dashboardData) {
    // This case might occur if session is authenticated but data fetch is still pending or failed silently
    // Or if user has no dashboard record and backend doesn't create one by default (though ours now does)
    return (
        <>
            <Navbar />
            <div className="flex flex-col justify-center items-center min-h-screen pt-20 text-center">
                <div className="text-xl text-gray-500 mb-4">No dashboard data available.</div>
                <p className="text-gray-600">Try playing some MCQs to see your progress!</p>
                <Link href="/play" className="mt-6 inline-block px-6 py-2 bg-green-500 text-white rounded hover:bg-green-600">
                    Start Playing
                </Link>
            </div>
        </>
    );
  }

  // Render dashboard with data
  return (
    <>
      <Navbar />
      <main className="container mx-auto p-4 md:p-6 min-h-screen pt-20 pb-10"> {/* Increased pt-20 for Navbar */} 
        <h1 className="text-3xl md:text-4xl font-bold mb-8 text-gray-800 text-center">Your Progress Dashboard</h1>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
          <div className="bg-white p-6 rounded-xl shadow-lg text-center">
            <h2 className="text-lg font-semibold text-gray-500 mb-1">Total Points</h2>
            <p className="text-4xl font-bold text-blue-600">
              {dashboardData.total_points}
            </p>
          </div>
          <div className="bg-white p-6 rounded-xl shadow-lg text-center">
            <h2 className="text-lg font-semibold text-gray-500 mb-1">Previous Session Points</h2>
            <p className="text-4xl font-bold text-green-600">
              {dashboardData.previous_session_points}
            </p>
          </div>
        </div>

        {/* Points Progression Chart */}
        <div className="bg-white p-6 rounded-xl shadow-lg mb-10">
          <h2 className="text-xl font-semibold text-gray-700 mb-4">Points Progression</h2>
          {dashboardData.points_history && dashboardData.points_history.length > 0 ? (
            <div style={{ height: '300px' }}> {/* Ensure container has a defined height */}
              <Line
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: {
                    legend: {
                      position: 'top' as const,
                    },
                    title: {
                      display: true,
                      text: 'Points Earned Over Time',
                    },
                  },
                  scales: {
                    y: {
                      beginAtZero: true,
                      ticks: {
                        stepSize: 10,
                      },
                      title: {
                        display: true,
                        text: 'Points'
                      }
                    },
                    x: {
                      title: {
                        display: true,
                        text: 'Session/Date'
                      }
                    }
                  },
                }}
                data={{
                  labels: dashboardData.points_history.map(item => {
                    const date = new Date(item.timestamp);
                    return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
                  }),
                  datasets: [
                    {
                      label: 'Points Earned',
                      data: dashboardData.points_history.map(item => item.points),
                      borderColor: 'rgb(75, 192, 192)',
                      backgroundColor: 'rgba(75, 192, 192, 0.5)',
                      tension: 0.1,
                    },
                  ],
                }}
              />
            </div>
          ) : (
            <div className="h-64 bg-gray-100 rounded-md flex items-center justify-center">
              <p className="text-gray-500">No points history available to display a chart.</p>
            </div>
          )}
        </div>

        {/* Last 5 Wrongdoing Questions */}
        <div className="bg-white p-6 rounded-xl shadow-lg">
          <h2 className="text-xl font-semibold text-gray-700 mb-4">Review Your Recent Mistakes</h2>
          {dashboardData.last_5_wrong_questions.length > 0 ? (
            <ul className="space-y-3">
              {dashboardData.last_5_wrong_questions.map((q, index) => (
                <li key={q.question_id + '-' + index} className="p-4 bg-red-50 border border-red-200 rounded-lg">
                  <p className="font-medium text-red-700 truncate" title={q.question_text}>
                    {index + 1}. {q.question_text}
                  </p>
                  <p className="text-xs text-red-500 mt-1">
                    Marked wrong on: {new Date(q.timestamp_marked_wrong).toLocaleDateString()}
                  </p>
                  {/* Optionally, add a "Retest this question" button later */}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-500">No recent wrong answers to display. Great job!</p>
          )}
        </div>
        
        {/* Action Buttons */}
        <div className="mt-12 flex flex-col md:flex-row justify-center items-center space-y-4 md:space-y-0 md:space-x-6">
          <button
            onClick={handleOpenResetModal} // Changed from handleResetDashboardData
            className="px-6 py-3 bg-red-500 hover:bg-red-600 text-white font-semibold rounded-lg shadow-md transition duration-150 w-full md:w-auto"
          >
            Reset Dashboard Data
          </button>
          <Link
            href="/home"
            className="block text-center px-6 py-3 bg-blue-500 hover:bg-blue-600 text-white font-semibold rounded-lg shadow-md transition duration-150 w-full md:w-auto"
          >
            Return to Main Page
          </Link>
        </div>
      </main>
      <ResetDashboardConfirmationModal
        isOpen={isResetModalOpen}
        onClose={handleCloseResetModal}
        onConfirm={handleConfirmResetDashboard}
        isLoading={isResetting}
      />
    </>
  );
}