#!/bin/bash

# Start the Flask webhook server in the background
python webhook_server.py &

# Build and start the Next.js frontend for production
npx next build
npx next start -p 5000 -H 0.0.0.0
