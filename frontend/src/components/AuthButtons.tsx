// frontend/src/components/AuthButtons.tsx
"use client";

import { signIn, useSession } from "next-auth/react"; // signOut removed if not used here
import React from "react";

export default function AuthButtons() {
  const { data: session, status } = useSession();

  // If session exists or loading, this component (on the login page) might render nothing
  // or be styled differently. The middleware should redirect away if session exists.
  if (status === "loading") {
    return <p className="text-gray-500">Loading session...</p>;
  }

  // If already signed in (middleware should ideally prevent reaching here on '/' page)
  // This component is mainly for the login page, so this part is defensive.
  if (session) {
    // This part of AuthButtons might no longer be needed if it's only on the login page
    // and the Navbar handles the signed-in state display.
    // However, if you were to use AuthButtons elsewhere for a quick status/logout, keep it.
    // For now, let's assume it is ONLY on the login page:
    return null; // Or a message like "You are already signed in."
                 // But middleware should redirect from '/' if signed in.
  }

  // Only show Sign In if not signed in
  return (
    <>
      {/* <p>Not signed in</p> */} {/* This message might be redundant on a dedicated login page */}
      <button
        onClick={() => signIn("google", { callbackUrl: "/home" })}
        className="w-full px-6 py-3 text-lg font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 transition duration-150 ease-in-out transform hover:scale-105"
      >
        Sign in with Google
      </button>
    </>
  );
}