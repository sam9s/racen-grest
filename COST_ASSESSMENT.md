# GRESTA Chatbot - Scalability & Cost Assessment

**Document Version:** 2.0  
**Date:** December 19, 2025  
**Project:** GRESTA E-commerce Chatbot

---

## Executive Summary

The GRESTA chatbot is **production-ready and scalable**. This document outlines the infrastructure capacity, cost drivers, and recommended pricing tiers.

---

## Current Architecture

| Component | Technology | Scalability |
|-----------|------------|-------------|
| Frontend | Next.js 14 + TypeScript | Fully scalable (Autoscale) |
| Backend | Flask (Python) | Stateless, can run multiple instances |
| Database | PostgreSQL (Replit Managed) | Handles concurrent connections |
| Vector Store | ChromaDB (Local) | Works for current scale |
| LLM | OpenAI gpt-4o-mini | Rate limited by tier |
| Widget | Embeddable JavaScript | CDN-ready |

---

## Cost Drivers

### 1. Replit Hosting

| Type | Specs | Monthly Cost | Best For |
|------|-------|--------------|----------|
| **Autoscale** | Variable | ~$5-30/mo | Variable traffic |
| **Reserved VM** | 1 vCPU / 4GB | ~$12/month | Moderate traffic |
| **Reserved VM** | 2 vCPU / 8GB | ~$25/month | Higher traffic |

### 2. OpenAI API

| Usage Level | Monthly Chats | Est. OpenAI Cost |
|-------------|---------------|------------------|
| **Light** | 500 | $2-5 |
| **Medium** | 2,000 | $10-20 |
| **Heavy** | 10,000 | $50-100 |

---

## Summary

| Question | Answer |
|----------|--------|
| Is the system scalable? | **Yes** |
| Current comfortable capacity | 5-10 concurrent users |
| Main cost driver | OpenAI API usage |
| Ready for production? | **Yes** |

---

*Document prepared for internal planning purposes.*
