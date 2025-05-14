// frontend/src/app/home/page.tsx
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import Link from "next/link";
// Remove AuthButtons import if Sign Out is handled by Navbar
// import AuthButtons from "@/components/AuthButtons";
import Navbar from "@/components/Navbar"; // Import Navbar

export default async function UserHomePage() {
  const session = await getServerSession(authOptions);

  if (!session) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen p-8 text-center">
        <p className="text-xl text-red-600 mb-4">Access Denied</p>
        <p className="mb-6">You need to be signed in to view this page.</p>
        <Link
          href="/"
          className="px-6 py-2 font-semibold text-white bg-blue-500 rounded hover:bg-blue-600"
        >
          Go to Login Page
        </Link>
      </div>
    );
  }

  return (
    <>
      {" "}
      {/* Use a fragment to wrap Navbar and main content */}
      <Navbar />
      <main className="flex flex-col items-center justify-start min-h-screen p-8 pt-24 bg-gray-50">
        {" "}
        {/* Added pt-24 for Navbar height */}
        <div className="w-full max-w-2xl p-8 bg-white rounded-lg shadow-xl text-center">
          <h1 className="text-3xl font-bold mb-3 text-gray-800">
            Welcome to Your Dashboard!
          </h1>
          <p className="mb-2 text-lg text-gray-600">
            Hello, {session.user?.name || session.user?.email}!
          </p>
          <p className="mb-8 text-sm text-gray-500">
            Your User ID: {session.user?.id}
          </p>

          <div className="space-y-4">
            <Link
              href="/play"
              className="block w-full px-6 py-4 text-lg font-medium text-white bg-green-500 rounded-lg shadow hover:bg-green-600 transition duration-150 ease-in-out transform hover:scale-105"
            >
              Play MCQs
            </Link>
            <Link
              href="/dashboard"
              className="block w-full px-6 py-4 text-lg font-medium text-white bg-indigo-500 rounded-lg shadow hover:bg-indigo-600 transition duration-150 ease-in-out transform hover:scale-105"
            >
              View Progress Dashboard
            </Link>
            <Link
              href="/retest"
              className="block w-full px-6 py-4 text-lg font-medium text-gray-800 bg-yellow-400 rounded-lg shadow hover:bg-yellow-500 transition duration-150 ease-in-out transform hover:scale-105"
            >
              Retest Wrong Questions
            </Link>
          </div>
          {/* Remove AuthButtons if Sign Out is handled by Navbar
          <div className="mt-10">
            <AuthButtons />
          </div>
          */}
        </div>
      </main>
    </>
  );
}
