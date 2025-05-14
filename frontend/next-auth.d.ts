// frontend/next-auth.d.ts
import NextAuth, { DefaultSession, DefaultUser } from "next-auth";
import { JWT, DefaultJWT } from "next-auth/jwt";

declare module "next-auth" {
  /**
   * Returned by `useSession`, `getSession` and received as a prop on the `SessionProvider` React Context
   */
  interface Session {
    user: {
      /** The user's postal address. */
      id: string; // Ensure id is always a string
    } & DefaultSession["user"]; // Keep the default properties
    idToken?: string; // Add idToken to the session
    accessToken?: string; // Add accessToken to the Session interface
    error?: string; // Optional: for conveying auth errors to the client
  }

  /**
   * The shape of the user object returned in the OAuth providers' `profile` callback,
   * or the second parameter of the `session` callback, when using a database.
   */
  interface User extends DefaultUser {
    // Add any other properties you expect on the User object from your database
    // For example, if your Prisma User model has `role`:
    // role?: string;
    id: string; // Ensure id is always a string
  }
}

declare module "next-auth/jwt" {
  /** Returned by the `jwt` callback and `getToken`, when using JWT sessions */
  interface JWT extends DefaultJWT {
    /** OpenID ID Token */
    // Add any custom properties you're adding to the JWT token
    // For example, the user's ID is often stored in `sub` (subject) by default.
    // If you add it explicitly:
    // id?: string;
    // Or, if you add it to the token in the jwt callback:
    // userId?: string;
    idToken?: string;     // Add idToken to the JWT interface
    accessToken?: string; // Add accessToken to the JWT interface
    userId?: string;      // This will hold the user's ID from your database
    // Optional: add iat, exp, jti if needed
  }
}