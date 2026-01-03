# GRESTA Widget Embed Guide

## Quick Start

Add this single line of code to your website, just before the closing `</body>` tag:

```html
<script src="https://gresta.sam9scloud.in/widget.js"></script>
```

That's it! The GRESTA chatbot widget will appear in the bottom-right corner of your website.

---

## Features

| Feature | Description |
|---------|-------------|
| **Dark Mode** | Sleek dark theme matching GREST branding |
| **Emerald Green Accent** | Uses GREST brand color (#10b981) |
| **New Chat Button** | "+" button in header to start fresh conversation |
| **Resize Handle** | Top-left corner allows resizing the chat window |
| **Session Persistence** | Conversations are saved locally and restored |
| **Streaming Responses** | Real-time character-by-character response display |
| **Mobile Responsive** | Adapts to mobile screens automatically |
| **Toggle Control** | Enable/disable widget remotely without code changes |

---

## Toggle Control (Enable/Disable Widget)

You can control whether the widget appears on your website remotely.

**Note:** Toggle control requires the admin token for security.

### Check Current Status (Public)
```bash
curl https://gresta.sam9scloud.in/api/widget/config
```

### Disable Widget (Requires Auth)
```bash
curl -X POST https://gresta.sam9scloud.in/api/widget/config \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: YOUR_ADMIN_TOKEN" \
  -d '{"enabled": false}'
```

### Enable Widget (Requires Auth)
```bash
curl -X POST https://gresta.sam9scloud.in/api/widget/config \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: YOUR_ADMIN_TOKEN" \
  -d '{"enabled": true}'
```

When disabled, the widget will not render on any page that has the embed code.

**Security:** The toggle endpoint requires the `X-Admin-Token` header to prevent unauthorized changes.

---

## Advanced Configuration

### Custom API Endpoint

If you need to point to a different API:

```html
<script>
  window.GRESTA_BASE_URL = 'https://your-custom-domain.com';
</script>
<script src="https://gresta.sam9scloud.in/widget.js"></script>
```

### Programmatic Control

The widget exposes a global API:

```javascript
// Start a new chat (clears history)
window.GRESTAWidget.startNewChat();

// Toggle chat window open/closed
window.GRESTAWidget.toggle();

// Re-initialize widget
window.GRESTAWidget.init();
```

---

## Troubleshooting

### Widget not appearing?
1. Check browser console for errors
2. Verify the script URL is correct
3. Check if widget is enabled: `curl https://gresta.sam9scloud.in/api/widget/config`

### CORS errors?
The widget handles CORS automatically. If you see CORS errors, contact support.

### Widget appears but doesn't respond?
1. Check if the API server is running
2. Verify your domain is in the allowed origins list

---

## Contact

For issues or feature requests, contact the GREST team.
