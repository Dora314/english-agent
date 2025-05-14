// frontend/src/app/providers.tsx
"use client"; // This component must be a Client Component

import { SessionProvider } from "next-auth/react";
import React from "react";

interface Props {
  children: React.ReactNode;
}

export default function NextAuthProviders({ children }: Props) {
  return <SessionProvider>{children}</SessionProvider>;
}