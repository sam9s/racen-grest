import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8080';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    console.log(`[Chat API] Attempting to reach backend at: ${BACKEND_URL}/api/chat`);
    
    const response = await fetch(`${BACKEND_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      console.error(`[Chat API] Backend returned status ${response.status}`);
      const errorText = await response.text();
      console.error(`[Chat API] Backend error: ${errorText}`);
      return NextResponse.json(
        { error: 'Backend error', response: 'I apologize, but I encountered an issue. Please try again.', debug: `Backend status: ${response.status}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error(`[Chat API] Error proxying chat request: ${errorMessage}`);
    console.error(`[Chat API] Full error:`, error);
    return NextResponse.json(
      { error: 'Failed to process request', response: 'I apologize, but I encountered an issue. Please try again.', debug: errorMessage },
      { status: 500 }
    );
  }
}
