// frontend/src/app/play/page.tsx
"use client";

import React, { useState, useEffect, FormEvent } from 'react';
import Link from 'next/link';
import { useSession } from 'next-auth/react';
import Navbar from '@/components/Navbar';
import { useRouter } from 'next/navigation';

interface MCQOptionClient {
  id: string;
  text: string;
}

interface QuestionClient {
  id: string;
  question_text: string;
  options: MCQOptionClient[];
}

interface UserAnswersMap {
  [questionId: string]: string;
}

// Interface for feedback state
interface AnswerFeedback {
  questionId: string;
  selectedOptionId: string;
  isCorrect: boolean;
  correctOptionId: string;
  correctOptionText?: string; // Optional, if backend sends it
}

export default function PlayPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  const [topic, setTopic] = useState<string>("");
  const [numQuestionsInput, setNumQuestionsInput] = useState<string>("5");
  const [questions, setQuestions] = useState<QuestionClient[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(false); // For API calls
  const [error, setError] = useState<string | null>(null);
  const [showTopicInputScreen, setShowTopicInputScreen] = useState<boolean>(true);
  const [selectedAnswers, setSelectedAnswers] = useState<UserAnswersMap>({});
  const [questionGenerationInfo, setQuestionGenerationInfo] = useState<string | null>(null); // Added state for generation info

  // State for immediate feedback
  const [answerFeedback, setAnswerFeedback] = useState<AnswerFeedback | null>(null);
  const [isFeedbackActive, setIsFeedbackActive] = useState<boolean>(false);

  // New state for managing quiz flow
  const [quizStage, setQuizStage] = useState<'topicSelection' | 'playing' | 'completed'>('topicSelection');
  const [sessionPointsEarned, setSessionPointsEarned] = useState<number | null>(null);


  const currentQuestion = questions[currentQuestionIndex];
  const currentQuestionSelectedOptionId = currentQuestion ? selectedAnswers[currentQuestion.id] : undefined;

  const handleGenerateQuestions = async (e: FormEvent) => {
    e.preventDefault();
    // (existing validation logic for topic and numQuestionsInput)
    if (!topic.trim()) { setError("Please enter a topic."); return; }
    const numQ = parseInt(numQuestionsInput, 10);
    if (isNaN(numQ) || numQ <= 0 || numQ > 20) { setError("Please enter a valid number of questions (1-20)."); return; }

    setIsLoading(true);
    setError(null);
    setQuestions([]);
    setSelectedAnswers({});
    setCurrentQuestionIndex(0);
    setAnswerFeedback(null); // Reset feedback
    setIsFeedbackActive(false);
    setQuestionGenerationInfo(null); // Reset generation info
    setSessionPointsEarned(null); // Reset points

    try {
      const response = await fetch('http://localhost:8000/api/mcqs/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          topic_string: topic,
          num_questions: numQ,
        }),
      });
      if (!response.ok) { 
        const errorData = await response.json().catch(() => ({ detail: "Unknown error fetching questions." }));
        throw new Error(errorData.detail || `Error: ${response.status}`);
      }
      const data: { questions: QuestionClient[], topic_id: string | null } = await response.json();
      if (data.questions && data.questions.length > 0) {
        if (data.questions.length < numQ) {
          setQuestionGenerationInfo(`Note: You requested ${numQ} questions, but only ${data.questions.length} were available for the topic "${topic}".`);
        }
        // If data.questions.length >= numQ, questionGenerationInfo remains null from the reset above.
        setQuestions(data.questions);
        setQuizStage('playing'); // Change stage
      } else {
        setError("No questions found for this topic. Please try a different topic.");
        setQuizStage('topicSelection'); // Remain in topic selection
      }
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred while fetching questions.");
      setQuizStage('topicSelection'); // Back to topic selection on error
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectAnswer = (questionId: string, optionId: string) => {
    if (isFeedbackActive) return; // Prevent changing answer while feedback is shown

    setSelectedAnswers(prevAnswers => ({
      ...prevAnswers,
      [questionId]: optionId,
    }));
    if (error === "Please select an answer.") setError(null);
  };

  const proceedToNextStep = () => {
    setIsFeedbackActive(false);
    setAnswerFeedback(null);
    setError(null); // Clear previous errors like "select an answer"

    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(prevIndex => prevIndex + 1);
    } else {
      handleSubmitQuiz(); // This will now change stage to 'completed'
    }
  };

  const handleNextQuestion = async () => {
    if (!currentQuestion) return;
    if (isFeedbackActive) { // If feedback is active, this button means "Continue"
        proceedToNextStep();
        return;
    }

    const selectedOptionId = selectedAnswers[currentQuestion.id];
    
    if (!selectedOptionId) {
      setError("Please select an answer.");
      return; 
    }
    setError(null);

    try {
      setIsLoading(true); 
      const response = await fetch('http://localhost:8000/api/mcqs/answer', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session?.idToken}`, // USE idToken
        },
        body: JSON.stringify({
          question_id: currentQuestion.id,
          selected_answer_id: selectedOptionId,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({detail: "Error saving answer."}));
        throw new Error(errorData.detail || `Failed to save answer: ${response.status}`);
      }

      const result: { // Type matching backend's SubmitAnswerResponse
          is_correct: boolean;
          correct_answer_id: string;
          correct_answer_text?: string;
          current_points?: number; // We might not use current_points here directly
      } = await response.json();
      
      console.log("Answer saved, backend response:", result);
      setAnswerFeedback({
        questionId: currentQuestion.id,
        selectedOptionId: selectedOptionId,
        isCorrect: result.is_correct,
        correctOptionId: result.correct_answer_id,
        correctOptionText: result.correct_answer_text,
      });
      setIsFeedbackActive(true);

    } catch (saveError: any) {
      console.error("Error saving answer:", saveError);
      setError(`Could not save your answer: ${saveError.message}. Please try again.`);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePreviousQuestion = () => {
    if (isFeedbackActive) return; // Don't allow going back while feedback for current Q is shown
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(prevIndex => prevIndex - 1);
      setAnswerFeedback(null); // Clear feedback when moving to a different question
      setIsFeedbackActive(false);
      setError(null);
    }
  };

  const handleSubmitQuiz = async () => {
    // This function is called when the last question's "Next" (which becomes "Submit Quiz") is clicked
    // OR when proceedToNextStep determines it's the end.
    // The actual submission to backend happens here.
    console.log("Final answers for this session:", selectedAnswers);

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:8000/api/mcqs/session/submit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session?.idToken}`, // USE idToken
        },
        body: JSON.stringify({
          answers_map: selectedAnswers,
          topic_id: questions.length > 0 ? `topic_${topic.toLowerCase().replace(/\\s+/g, '_')}` : "unknown_topic"
          // Ensure your backend can derive topic_id or pass it if available/needed
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Failed to submit quiz session." }));
        throw new Error(errorData.detail || `Error: ${response.status}`);
      }

      const result = await response.json(); // Expect { session_points_earned: number, ... }
      console.log("Quiz session submitted, backend response:", result);
      
      setSessionPointsEarned(result.session_points_earned);
      setQuizStage('completed'); // Change stage to show completion screen

    } catch (submitError: any) {
      console.error("Error submitting quiz session:", submitError);
      setError(`Failed to submit quiz: ${submitError.message}`);
      // User remains in 'playing' stage on the last question if submission fails
    } finally {
      setIsLoading(false); 
    }
  };
  
  const resetQuizStateAndNavigateHome = () => {
    setTopic("");
    setNumQuestionsInput("5");
    setQuestions([]);
    setCurrentQuestionIndex(0);
    setSelectedAnswers({});
    setAnswerFeedback(null);
    setIsFeedbackActive(false);
    setError(null);
    setQuestionGenerationInfo(null);
    setSessionPointsEarned(null);
    setQuizStage('topicSelection');
    router.push('/home');
  };

  const handleGoBackToTopicSelection = () => {
    setQuizStage('topicSelection'); 
    setTopic(""); // Optionally reset topic input
    setQuestions([]); // Clear current questions
    setSelectedAnswers({});
    setCurrentQuestionIndex(0);
    setError(null); 
    setAnswerFeedback(null); 
    setIsFeedbackActive(false);
    setQuestionGenerationInfo(null);
    setSessionPointsEarned(null);
  };


  // --- JSX Rendering ---
  if (status === "loading") {
    return (
      <>
        <Navbar />
        <div className="flex justify-center items-center min-h-screen pt-6 md:pt-8">Loading session...</div>
      </>
    );
  }
  // Ensure session is checked after loading status
  if (!session) { // status could be 'unauthenticated' here
    return (
      <>
        <Navbar />
        <div className="flex flex-col items-center justify-center min-h-screen pt-6 md:pt-8">
          <p>You need to be logged in to play MCQs.</p>
          <Link href="/api/auth/signin" className="text-blue-500 hover:underline mt-2">Sign In</Link>
        </div>
      </>
    );
  }

  return (
    <>
      <Navbar />
      <main className="container mx-auto p-4 md:p-6 min-h-screen pt-6">
        {quizStage === 'topicSelection' && (
          // --- Topic Input Screen ---
          <div className="max-w-lg mx-auto bg-white p-6 md:p-8 rounded-xl shadow-xl">
            <h1 className="text-3xl font-bold mb-6 md:mb-8 text-center text-gray-700">Choose Your Topic</h1>
            <form onSubmit={handleGenerateQuestions} className="space-y-6">
              {/* Topic Input */}
              <div>
                <label htmlFor="topic" className="block text-sm font-medium text-gray-700 mb-1">
                  Enter a topic for your MCQs
                </label>
                <input
                  type="text" id="topic" value={topic} onChange={(e) => setTopic(e.target.value)}
                  placeholder="e.g., Past Simple Tense, Business Emails"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  disabled={isLoading}
                />
              </div>
              {/* Num Questions Input */}
              <div>
                <label htmlFor="numQuestions" className="block text-sm font-medium text-gray-700 mb-1">
                  Number of questions (1-20)
                </label>
                <input
                  type="number" id="numQuestions" value={numQuestionsInput} onChange={(e) => setNumQuestionsInput(e.target.value)}
                  min="1" max="20"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  disabled={isLoading}
                />
              </div>
              {error && <p className="text-sm text-red-600 text-center">{error}</p>}
              <button
                type="submit"
                disabled={isLoading || !topic.trim()}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg shadow-md transition duration-150 ease-in-out disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
              >
                {isLoading ? ( 
                  <> 
                    {/* SVG Spinner */} 
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Generating...
                  </> 
                ) : ( "Generate Questions" )}
              </button>
            </form>
          </div>
        )}

        {quizStage === 'playing' && currentQuestion && (
          // --- Question Display Screen ---
          <div className="max-w-2xl mx-auto bg-white p-6 md:p-8 rounded-xl shadow-xl">
            <div className="mb-2 text-sm text-gray-500">Topic: <span className="font-semibold text-gray-700">{topic}</span></div>
            <div className="mb-6 text-right text-gray-600 font-medium">Question {currentQuestionIndex + 1} of {questions.length}</div>
            
            {questionGenerationInfo && (
              <div className="mb-4 p-3 bg-blue-100 border border-blue-300 text-blue-700 rounded-md text-sm">
                {questionGenerationInfo}
              </div>
            )}

            <div className="bg-gray-50 p-6 rounded-lg mb-8 min-h-[100px] flex items-center">
              <p className="text-lg md:text-xl font-semibold text-gray-800 leading-relaxed">
                {currentQuestion.question_text}
              </p>
            </div>

            <div className="space-y-3 md:space-y-4 mb-6">
              {currentQuestion.options.map((option) => {
                let buttonStyle = 'bg-white border-gray-300 hover:bg-blue-50 hover:border-blue-400 text-gray-700'; // Default
                let isDisabled = isFeedbackActive || (isLoading && !!currentQuestionSelectedOptionId); // Disable if feedback active or saving this answer

                if (isFeedbackActive && answerFeedback?.questionId === currentQuestion.id) {
                  if (option.id === answerFeedback.correctOptionId) {
                    buttonStyle = 'bg-green-500 border-green-600 text-white shadow-md ring-2 ring-green-300'; // Correct answer
                  } else if (option.id === answerFeedback.selectedOptionId && !answerFeedback.isCorrect) {
                    buttonStyle = 'bg-red-500 border-red-600 text-white shadow-md ring-2 ring-red-300'; // Incorrectly selected
                  } else {
                    buttonStyle = 'bg-gray-100 border-gray-200 text-gray-500 cursor-not-allowed'; // Other non-selected during feedback
                  }
                } else if (currentQuestionSelectedOptionId === option.id) {
                  buttonStyle = 'bg-blue-500 border-blue-600 text-white ring-2 ring-blue-300 shadow-lg'; // Actively selected by user
                }

                return (
                  <button
                    key={option.id}
                    onClick={() => handleSelectAnswer(currentQuestion.id, option.id)}
                    disabled={isDisabled}
                    className={`w-full text-left p-3 md:p-4 rounded-lg border-2 transition-colors duration-150 ease-in-out
                               font-medium focus:outline-none 
                               ${buttonStyle}
                               ${isDisabled && !(isFeedbackActive && option.id === answerFeedback?.correctOptionId) ? 'opacity-70 cursor-not-allowed' : ''}
                              `}
                  >
                    <span className="font-bold mr-2">{option.id}.</span> {option.text}
                  </button>
                );
              })}
            </div>

            {/* Navigation Buttons */}
            <div className="flex justify-between items-center mt-4">
              <button
                onClick={handlePreviousQuestion}
                disabled={currentQuestionIndex === 0 || isLoading || isFeedbackActive}
                className="px-5 py-2 md:px-6 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold rounded-lg shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <button
                onClick={handleNextQuestion}
                // Disable if:
                // - isLoading (API call in progress for this answer)
                // - Not feedback active AND no answer selected for current question
                disabled={isLoading || (!isFeedbackActive && !currentQuestionSelectedOptionId)}
                className={`px-5 py-2 md:px-6 text-white font-semibold rounded-lg shadow-sm disabled:opacity-50 disabled:cursor-not-allowed
                            ${isFeedbackActive ? 'bg-blue-500 hover:bg-blue-600' : 'bg-green-500 hover:bg-green-600'}`}
              >
                {isLoading && currentQuestionSelectedOptionId && !isFeedbackActive ? ( // Saving state
                  <> 
                    {/* SVG Spinner */} 
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Saving...
                  </>
                ) : isFeedbackActive ? (
                  "Continue"
                ) : currentQuestionIndex === questions.length - 1 ? (
                  "Submit Quiz"
                ) : (
                  "Next"
                )}
              </button>
            </div>

            {/* Feedback message area - MOVED HERE */}
            {isFeedbackActive && answerFeedback?.questionId === currentQuestion.id && (
              <div className={`p-3 mt-4 rounded-md text-sm font-medium text-center
                              ${answerFeedback.isCorrect ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                {answerFeedback.isCorrect ? "Correct!" : `Incorrect. The correct answer was ${answerFeedback.correctOptionId}: ${answerFeedback.correctOptionText || 'N/A'}`}
              </div>
            )}

            {/* General error message - Positioned after feedback message */}
            {error && !isFeedbackActive && <p className="text-sm text-red-600 mt-4 mb-2 text-center">{error}</p>}

            {/* Option to go back */}
            <div className="mt-6 text-center">
              <button
                onClick={handleGoBackToTopicSelection}
                className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
              >
                  Choose a different topic
              </button>
            </div>
          </div>
        )}
        
        {quizStage === 'playing' && !currentQuestion && !isLoading && (
            <div className="text-center text-gray-600 mt-10 max-w-lg mx-auto bg-white p-6 md:p-8 rounded-xl shadow-xl">
                <p className="text-lg">No questions to display.</p>
                <p className="text-sm mb-4">This could be due to an issue fetching questions, or the quiz ended unexpectedly.</p>
                <button 
                    onClick={handleGoBackToTopicSelection}
                    className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                >
                    Try Again with a New Topic
                </button>
            </div>
        )}

        {quizStage === 'completed' && (
          <div className="max-w-lg mx-auto bg-white p-6 md:p-8 rounded-xl shadow-xl text-center">
            <svg className="w-16 h-16 text-green-500 mx-auto mb-4" fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" viewBox="0 0 24 24" stroke="currentColor"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            <h2 className="text-2xl font-semibold text-gray-700 mb-3">Quiz Session Completed!</h2>
            {sessionPointsEarned !== null && (
              <p className="text-gray-600 text-lg mb-6">
                You earned <span className="font-bold text-blue-600">{sessionPointsEarned}</span> points in this session.
              </p>
            )}
            <button
              onClick={resetQuizStateAndNavigateHome}
              className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg shadow-md transition duration-150 ease-in-out"
            >
              Return to Home Page
            </button>
          </div>
        )}
      </main>
    </>
  );
}