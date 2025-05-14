// frontend/src/app/api/dashboard/reset/route.ts
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
    const userId = request.headers.get('X-User-ID');

    if (!userId) {
        return NextResponse.json({ detail: 'User ID not provided in X-User-ID header.' }, { status: 400 });
    }

    try {
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';
        const response = await fetch(`${backendUrl}/api/dashboard/reset`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-User-ID': userId, // Forward the user ID to the backend
            },
            // No body is needed for this specific reset endpoint as per backend implementation
        });

        const data = await response.json();

        if (!response.ok) {
            // Forward the error from the backend
            return NextResponse.json({ detail: data.detail || 'Failed to reset dashboard data on the backend.' }, { status: response.status });
        }

        return NextResponse.json(data, { status: response.status });
    } catch (error) {
        console.error('[API /dashboard/reset] Error:', error);
        return NextResponse.json({ detail: 'Internal server error while trying to reset dashboard data.' }, { status: 500 });
    }
}
