import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";  // shared authOptions
import { NextResponse } from 'next/server';

export async function GET(request: Request) {
    const session = await getServerSession(authOptions);

    if (!session || !session.user || !session.user.id) {
        return NextResponse.json({ message: "Not authenticated" }, { status: 401 });
    }

    const userId = session.user.id;

    try {
        // Fetch data from your FastAPI backend
        const backendResponse = await fetch(`${process.env.BACKEND_API_URL}/api/dashboard`, { // Make sure BACKEND_API_URL is in .env
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-User-ID': userId, // Send user ID to backend
            },
        });

        if (!backendResponse.ok) {
            const errorData = await backendResponse.json().catch(() => ({ detail: "Backend error" }));
            console.error("Backend API error for /dashboard:", errorData);
            return NextResponse.json({ message: errorData.detail || "Failed to fetch dashboard data from backend" }, { status: backendResponse.status });
        }

        const data = await backendResponse.json();
        return NextResponse.json(data);

    } catch (error) {
        console.error("Error in /dashboard Next.js route:", error);
        return NextResponse.json({ message: "Internal server error" }, { status: 500 });
    }
}
