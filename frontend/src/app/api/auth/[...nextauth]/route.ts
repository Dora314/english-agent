// frontend/src/app/api/auth/[...nextauth]/route.ts
import NextAuth from "next-auth";
import { authOptions } from "@/lib/auth"; // Import the shared authOptions from lib/auth.ts

// Initialize NextAuth with the shared options
const handler = NextAuth(authOptions);

// Export the handler for both GET and POST requests, as required by NextAuth.js
export { handler as GET, handler as POST };