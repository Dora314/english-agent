// frontend/src/app/page.tsx
import AuthButtons from "@/components/AuthButtons";

export default async function HomePage() {
  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-8">
      <div className="p-8 bg-white rounded-lg shadow-xl text-center">
        <h1 className="text-3xl font-bold mb-6 text-gray-800">
          Welcome to the English MCQ Platform
        </h1>
        <div className="space-y-4">
          <AuthButtons /> {/* This will show "Sign in with Google" */}
        </div>
      </div>
    </main>
  );
}