// frontend/src/lib/auth.ts
import NextAuth, { NextAuthOptions } from "next-auth";
import { PrismaAdapter } from "@next-auth/prisma-adapter";
import { PrismaClient } from "@prisma/client";
import GoogleProvider from "next-auth/providers/google"; // Import GoogleProvider

// Instantiate PrismaClient
const prisma = new PrismaClient();

export const authOptions: NextAuthOptions = {
  adapter: PrismaAdapter(prisma),
  providers: [
    // IMPORTANT: Ensure your OAuth provider (e.g., Google, Auth0, etc.)
    // is correctly configured and uncommented here.
    // The provider MUST be configured to return an id_token, and the scope
    // should typically include "openid".
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      authorization: {
        params: {
          scope: "openid email profile", // 'openid' is crucial for id_token
        },
      },
    }),
    // Add your other configured providers here (if any)
  ],
  session: {
    strategy: "jwt",
  },
  callbacks: {
    async jwt({ token, user, account }) {
      console.log("JWT Callback - Account:", JSON.stringify(account, null, 2));
      console.log("JWT Callback - User:", JSON.stringify(user, null, 2));
      console.log("JWT Callback - Initial Token:", JSON.stringify(token, null, 2));

      if (account) {
        token.accessToken = account.access_token;

        if (account.id_token) {
          token.idToken = account.id_token;
          console.log("JWT Callback - Successfully assigned id_token from account:", account.id_token);
        } else {
          console.warn("JWT Callback - WARNING: account.id_token is MISSING. Check provider config & 'openid' scope. Account:", JSON.stringify(account, null, 2));
        }
      }
      // If user object exists (e.g., on sign-in or when adapter populates it), assign its ID to token.userId
      if (user?.id) {
        token.userId = user.id;
        console.log("JWT Callback - Assigned user.id to token.userId:", user.id);
      }

      console.log("JWT Callback - Final Token:", JSON.stringify(token, null, 2));
      return token;
    },
    async session({ session, token }) {
      console.log("Session Callback - Token from JWT:", JSON.stringify(token, null, 2));

      session.accessToken = token.accessToken;
      session.idToken = token.idToken;

      // Ensure session.user exists and assign the id from token.userId (which should be our DB user ID)
      if (session.user) {
        session.user.id = token.userId as string; // Cast as string, ensure userId is always populated in JWT
      } else {
        // Fallback to create user object if it somehow doesn't exist
        session.user = {
          id: token.userId as string,
          name: token.name, // token.name, token.email, token.picture are standard JWT claims
          email: token.email,
          image: token.picture,
        };
      }

      if (!session.idToken) {
        console.warn("Session Callback - WARNING: session.idToken is MISSING. API calls requiring it will fail.");
      }
      if (!session.user?.id) { // Check session.user.id specifically
        console.warn("Session Callback - WARNING: session.user.id is MISSING or undefined.");
      }

      console.log("Session Callback - Final Session:", JSON.stringify(session, null, 2));
      return session;
    },
  },
  // For more detailed NextAuth logs during development
  debug: process.env.NODE_ENV === "development", // Enable debug mode in development
  pages: {
    signIn: '/', // Redirect to home page for sign-in
    error: '/api/auth/error', // Default error page, ensure it handles errors gracefully or customize
  }
};

export default NextAuth(authOptions);