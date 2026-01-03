import { NextResponse } from 'next/server';

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Cache-Control': 'public, max-age=60',
};

export async function OPTIONS() {
  return new NextResponse(null, { headers: CORS_HEADERS });
}

export async function GET() {
  try {
    const response = await fetch(`http://localhost:8080/api/widget/config`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });

    if (!response.ok) {
      return NextResponse.json(
        { enabled: true, error: 'Config fetch failed, defaulting to enabled' },
        { headers: CORS_HEADERS }
      );
    }

    const data = await response.json();
    return NextResponse.json(data, { headers: CORS_HEADERS });
  } catch (error) {
    console.error('Widget config error:', error);
    return NextResponse.json(
      { enabled: true, error: 'Config unavailable, defaulting to enabled' },
      { headers: CORS_HEADERS }
    );
  }
}
