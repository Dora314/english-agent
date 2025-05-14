'use client';

import { useState, useEffect, FormEvent } from 'react'; // Added FormEvent
import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import Navbar from '@/components/Navbar'; // Added Navbar import
import Link from 'next/link'; // Added Link for sign-in prompt

interface MCQOption {
  id: string;
  text: string;
}

interface QuestionForRetest {
  id: string;
  question_text: string;
  options: MCQOption[];
}

interface AnswerFeedbackBackend { // Renamed to avoid conflict if we add a local feedback state
  is_correct: boolean;
  correct_answer_id?: string;
  correct_answer_text?: string;
}

const RetestPage = () => {
  const router = useRouter();
  const { data: session, status } = useSession();

  const [numQuestionsInput, setNumQuestionsInput] = useState<string>("5"); // Changed to string for consistency with play page input
  const [questions, setQuestions] = useState<QuestionForRetest[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState<number>(0);
  const [selectedAnswers, setSelectedAnswers] = useState<Record<string, string>>({});
  const [feedbackMap, setFeedbackMap] = useState<Record<string, AnswerFeedbackBackend>>({}); // Renamed from feedback
  
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [stage, setStage] = useState<'input' | 'retesting' | 'completed'>('input');

  // New state for immediate feedback UI, similar to play/page.tsx
  const [currentAnswerFeedback, setCurrentAnswerFeedback] = useState<AnswerFeedbackBackend & { questionId: string; selectedOptionId: string } | null>(null);
  const [isFeedbackActive, setIsFeedbackActive] = useState<boolean>(false);


  useEffect(() => {
    // No automatic redirect, show message and link instead
    // if (status === 'unauthenticated') {
    //   router.push('/api/auth/signin');
    // }
  }, [status, router]);

  const handleStartRetest = async (e: FormEvent) => { // Added FormEvent and e.preventDefault()
    e.preventDefault();
    const numQ = parseInt(numQuestionsInput, 10);
    if (isNaN(numQ) || numQ <= 0 || numQ > 50) { // Max 50 for retest, can be adjusted
      setError("Please enter a valid number of questions (1-50).");
      return;
    }
    setIsLoading(true);
    setError(null);
    setQuestions([]);
    setSelectedAnswers({});
    setCurrentQuestionIndex(0);
    setFeedbackMap({});
    setCurrentAnswerFeedback(null);
    setIsFeedbackActive(false);

    try {
      const response = await fetch('http://localhost:8000/api/retest/generate', { 
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session?.idToken}`,
        },
        body: JSON.stringify({ num_questions: numQ }),
      });
      if (!response.ok) {
        const errData = await response.json().catch(() => ({ detail: "Unknown error fetching retest questions." }));
        throw new Error(errData.detail || `Error: ${response.status}`);
      }
      const data = await response.json();
      if (data.questions && data.questions.length > 0) {
        setQuestions(data.questions);
        setStage('retesting');
      } else {
        setError('No wrong questions found to retest, or none available for the number requested.');
        setStage('input'); 
      }
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred while fetching questions.');
      setStage('input');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnswerSelect = (questionId: string, optionId: string) => {
    if (isFeedbackActive) return; 

    setSelectedAnswers(prev => ({ ...prev, [questionId]: optionId }));
    if (error === "Please select an answer.") setError(null);
  };

  const proceedToNextStep = () => {
    setIsFeedbackActive(false);
    setCurrentAnswerFeedback(null);
    setError(null);

    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(prevIndex => prevIndex + 1);
    } else {
      setStage('completed'); // All questions answered and feedback shown
    }
  };
  
  const handleSubmitAnswerAndShowFeedback = async () => {
    const currentQuestion = questions[currentQuestionIndex];
    if (!currentQuestion) return;

    const selectedOptionId = selectedAnswers[currentQuestion.id];
    if (!selectedOptionId) {
      setError("Please select an answer.");
      return;
    }
    setError(null);
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/mcqs/answer', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session?.idToken}`, // Ensure idToken is available
        },
        body: JSON.stringify({
          question_id: currentQuestion.id,
          selected_answer_id: selectedOptionId,
          is_retest: true, // Indicate this is a retest answer
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Error submitting answer." }));
        throw new Error(errorData.detail || `Failed to submit answer: ${response.status}`);
      }
      const backendFeedback: AnswerFeedbackBackend = await response.json();
      
      setFeedbackMap(prev => ({ ...prev, [currentQuestion.id]: backendFeedback }));
      setCurrentAnswerFeedback({
        ...backendFeedback,
        questionId: currentQuestion.id,
        selectedOptionId: selectedOptionId,
      });
      setIsFeedbackActive(true);

    } catch (submitError: any) {
      setError(`Could not submit your answer: ${submitError.message}. Please try again.`);
    } finally {
      setIsLoading(false);
    }
  };


  const handleNextOrSubmitButton = () => {
    if (isFeedbackActive) {
      proceedToNextStep();
    } else {
      handleSubmitAnswerAndShowFeedback();
    }
  };

  const handlePreviousQuestion = () => {
    if (isFeedbackActive) return; 
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(prevIndex => prevIndex - 1);
      setCurrentAnswerFeedback(null); 
      setIsFeedbackActive(false);
      setError(null);
    }
  };

  const handleFinishRetestAndNavigateHome = () => {
    router.push('/home'); 
  };


  if (status === 'loading') {
    return (
      <>
        <Navbar />
        <div className="flex justify-center items-center min-h-screen pt-6 md:pt-8">Loading session...</div>
      </>
    );
  }
  if (status === 'unauthenticated' || !session) { // Added !session check
    return (
      <>
        <Navbar />
        <div className="flex flex-col items-center justify-center min-h-screen pt-6 md:pt-8">
          <p>You need to be logged in to access the retest feature.</p>
          <Link href="/api/auth/signin" className="text-blue-500 hover:underline mt-2">Sign In</Link>
        </div>
      </>
    );
  }

  const currentQuestion = questions.length > 0 ? questions[currentQuestionIndex] : null;
  // const currentFeedbackForDisplay = currentQuestion ? feedbackMap[currentQuestion.id] : null; // For styling options after feedback
  const currentQuestionSelectedOptionId = currentQuestion ? selectedAnswers[currentQuestion.id] : undefined;


  return (
    <>
      <Navbar />
      <main className="container mx-auto p-4 md:p-6 min-h-screen pt-6">
        {stage === 'input' && (
          <div className="max-w-lg mx-auto bg-white p-6 md:p-8 rounded-xl shadow-xl">
            <h1 className="text-3xl font-bold mb-6 md:mb-8 text-center text-gray-700">Retest Wrong Questions</h1>
            <form onSubmit={handleStartRetest} className="space-y-6">
              <div>
                <label htmlFor="numQuestions" className="block text-sm font-medium text-gray-700 mb-1">
                  Number of questions to retest (1-50)
                </label>
                <input
                  type="number"
                  id="numQuestions"
                  value={numQuestionsInput}
                  onChange={(e) => setNumQuestionsInput(e.target.value)}
                  min="1"
                  max="50" // Consistent with validation
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  disabled={isLoading}
                />
              </div>
              {error && <p className="text-sm text-red-600 text-center">{error}</p>}
              <button
                type="submit"
                disabled={isLoading || !numQuestionsInput.trim()}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg shadow-md transition duration-150 ease-in-out disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
              >
                {isLoading ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Loading Questions...
                  </>
                ) : 'Start Retest'}
              </button>
            </form>
          </div>
        )}

        {stage === 'retesting' && currentQuestion && (
          <div className="max-w-2xl mx-auto bg-white p-6 md:p-8 rounded-xl shadow-xl">
            <div className="mb-6 text-right text-gray-600 font-medium">Question {currentQuestionIndex + 1} of {questions.length}</div>
            
            <div className="bg-gray-50 p-6 rounded-lg mb-8 min-h-[100px] flex items-center">
              <p className="text-lg md:text-xl font-semibold text-gray-800 leading-relaxed">
                {currentQuestion.question_text}
              </p>
            </div>

            <div className="space-y-3 md:space-y-4 mb-6">
              {currentQuestion.options.map((option) => {
                let buttonStyle = 'bg-white border-gray-300 hover:bg-blue-50 hover:border-blue-400 text-gray-700';
                let isDisabled = isFeedbackActive || (isLoading && !!currentQuestionSelectedOptionId);

                if (isFeedbackActive && currentAnswerFeedback?.questionId === currentQuestion.id) {
                  if (option.id === currentAnswerFeedback.correct_answer_id) {
                    buttonStyle = 'bg-green-500 border-green-600 text-white shadow-md ring-2 ring-green-300';
                  } else if (option.id === currentAnswerFeedback.selectedOptionId && !currentAnswerFeedback.is_correct) {
                    buttonStyle = 'bg-red-500 border-red-600 text-white shadow-md ring-2 ring-red-300';
                  } else {
                    buttonStyle = 'bg-gray-100 border-gray-200 text-gray-500 cursor-not-allowed';
                  }
                } else if (currentQuestionSelectedOptionId === option.id) {
                  buttonStyle = 'bg-blue-500 border-blue-600 text-white ring-2 ring-blue-300 shadow-lg';
                }

                return (
                  <button
                    key={option.id}
                    onClick={() => handleAnswerSelect(currentQuestion.id, option.id)}
                    disabled={isDisabled}
                    className={`w-full text-left p-3 md:p-4 rounded-lg border-2 transition-colors duration-150 ease-in-out
                               font-medium focus:outline-none 
                               ${buttonStyle}
                               ${isDisabled && !(isFeedbackActive && option.id === currentAnswerFeedback?.correct_answer_id) ? 'opacity-70 cursor-not-allowed' : ''}
                              `}
                  >
                    <span className="font-bold mr-2">{option.id}.</span> {option.text}
                  </button>
                );
              })}
            </div>

            <div className="flex justify-between items-center mt-4">
              <button
                onClick={handlePreviousQuestion}
                disabled={currentQuestionIndex === 0 || isLoading || isFeedbackActive}
                className="px-5 py-2 md:px-6 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold rounded-lg shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <button
                onClick={handleNextOrSubmitButton}
                disabled={isLoading || (!isFeedbackActive && !currentQuestionSelectedOptionId)}
                className={`px-5 py-2 md:px-6 text-white font-semibold rounded-lg shadow-sm disabled:opacity-50 disabled:cursor-not-allowed
                            ${isFeedbackActive ? 'bg-blue-500 hover:bg-blue-600' : 'bg-green-500 hover:bg-green-600'}`}
              >
                {isLoading && currentQuestionSelectedOptionId && !isFeedbackActive ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Submitting...
                  </>
                ) : isFeedbackActive ? (
                  "Continue"
                ) : currentQuestionIndex === questions.length - 1 ? (
                  "Submit & Finish" // Or "Show Result & Finish"
                ) : (
                  "Submit Answer" // Or "Show Result"
                )}
              </button>
            </div>

            {/* Feedback message area - MOVED HERE */}
            {isFeedbackActive && currentAnswerFeedback?.questionId === currentQuestion.id && (
              <div className={`p-3 mt-4 rounded-md text-sm font-medium text-center
                              ${currentAnswerFeedback.is_correct ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                {currentAnswerFeedback.is_correct ? "Correct!" : `Incorrect. The correct answer was ${currentAnswerFeedback.correct_answer_id}: ${currentAnswerFeedback.correct_answer_text || 'N/A'}`}
              </div>
            )}
            
            {/* General error message - Positioned after feedback message */}
            {error && !isFeedbackActive && <p className="text-sm text-red-600 mt-4 mb-2 text-center">{error}</p>}

          </div>
        )}

        {stage === 'retesting' && questions.length === 0 && !isLoading && (
           <div className="max-w-lg mx-auto bg-white p-6 md:p-8 rounded-xl shadow-xl text-center">
              <p className="text-gray-700 text-lg mb-4">No questions were found for your retest session.</p>
              <p className="text-gray-600 text-sm mb-6">This might be because you have no incorrectly answered questions pending, or there were fewer than you requested.</p>
              <button
                onClick={() => { setStage('input'); setError(null); setNumQuestionsInput("5"); }}
                className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline transition-colors"
              >
                Try Again
              </button>
          </div>
        )}

        {stage === 'completed' && (
          <div className="max-w-lg mx-auto bg-white p-6 md:p-8 rounded-xl shadow-xl text-center">
            <svg className="w-16 h-16 text-green-500 mx-auto mb-4" fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" viewBox="0 0 24 24" stroke="currentColor"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            <h2 className="text-2xl font-semibold text-gray-700 mb-4">Retest Session Completed!</h2>
            <p className="text-gray-600 mb-6">You have reviewed the selected questions.</p>
            <button
              onClick={handleFinishRetestAndNavigateHome}
              className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg shadow-md transition duration-150 ease-in-out"
            >
              Return to Home Page
            </button>
          </div>
        )}
      </main>
    </>
  );
};

export default RetestPage;
