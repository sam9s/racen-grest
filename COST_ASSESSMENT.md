# JoveHeal Chatbot - Scalability & Cost Assessment

**Document Version:** 1.0  
**Date:** December 10, 2025  
**Project:** Jovee (RACEN) Wellness Chatbot

---

## Executive Summary

The JoveHeal chatbot is **production-ready and scalable**. This document outlines the infrastructure capacity, cost drivers, and recommended pricing tiers for your client.

---

## Current Architecture

| Component | Technology | Scalability |
|-----------|------------|-------------|
| Frontend | Next.js 14 + TypeScript | Fully scalable (Autoscale) |
| Backend | Flask (Python) | Stateless, can run multiple instances |
| Database | PostgreSQL (Replit Managed) | Handles concurrent connections |
| Vector Store | ChromaDB (Local) | Works for current scale, may need migration at very high volume |
| LLM | OpenAI gpt-4o-mini | Rate limited by tier |
| Widget | Embeddable JavaScript | CDN-ready, no scaling concerns |

---

## Current Capacity Limits

### Concurrent Users (Simultaneous Active Chats)

| Scenario | Concurrent Users | Experience |
|----------|------------------|------------|
| Comfortable | 5-10 | Smooth, fast responses |
| Moderate Load | 10-15 | Slight delays (2-5 seconds) |
| High Load | 15-25 | Noticeable delays, possible queuing |
| Overload | 25+ | Timeouts, errors, degraded experience |

### Bottleneck Priority

1. **OpenAI API Rate Limits** - Hard ceiling based on account tier
2. **Flask Backend** - Single process handles requests sequentially
3. **Replit Container Resources** - CPU/RAM constraints
4. **ChromaDB** - Local disk-based vector search

---

## Cost Drivers

### 1. Replit Hosting

#### Compute Units (Autoscale Deployments)

| Resource | Compute Units |
|----------|---------------|
| 1 CPU Second | 18 units |
| 1 RAM Second | 2 units |

#### Deployment Options

| Type | Specs | Monthly Cost | Best For |
|------|-------|--------------|----------|
| **Autoscale** | Variable (scales to zero) | Pay-per-use (~$5-30/mo typical) | Variable traffic, cost optimization |
| **Reserved VM (Shared)** | 0.5 vCPU / 2GB RAM | ~$7/month | Always-on, light traffic |
| **Reserved VM (Dedicated)** | 1 vCPU / 4GB RAM | ~$12/month | Moderate traffic |
| **Reserved VM (Dedicated)** | 2 vCPU / 8GB RAM | ~$25/month | Higher traffic, faster responses |
| **Reserved VM (Dedicated)** | 4 vCPU / 16GB RAM | ~$50/month | Heavy traffic, enterprise use |

#### Included Credits

| Subscription | Monthly Credits |
|--------------|-----------------|
| Core | $25/month |
| Teams | $40/user/month |

**Note:** Core subscription likely covers UAT and light-to-moderate production use.

---

### 2. OpenAI API (Primary Variable Cost)

#### Pricing (gpt-4o-mini)

| Token Type | Cost per 1K Tokens |
|------------|-------------------|
| Input | $0.15 |
| Output | $0.60 |

#### Estimated Monthly Costs by Usage

| Usage Level | Monthly Chats | Messages/Chat | Est. OpenAI Cost |
|-------------|---------------|---------------|------------------|
| **Light** | 500 | 4 | $2-5 |
| **Medium** | 2,000 | 4 | $10-20 |
| **Heavy** | 10,000 | 4 | $50-100 |
| **Very Heavy** | 50,000 | 4 | $250-500 |
| **Enterprise** | 100,000+ | 4 | $500+ |

*Assumptions: Average 4 messages per conversation, ~200 input tokens + 150 output tokens per message*

---

### 3. OpenAI Rate Limits (Capacity Ceiling)

| Account Tier | Requests Per Minute (RPM) | Tokens Per Minute (TPM) | Practical Concurrent Users |
|--------------|---------------------------|-------------------------|---------------------------|
| **Free/Tier 1** | 60 | 60,000 | 10-15 |
| **Tier 2** | 500 | 200,000 | 50-100 |
| **Tier 3** | 5,000 | 400,000 | 200-500 |
| **Tier 4** | 10,000 | 2,000,000 | 500-1,000 |
| **Tier 5** | 30,000 | 30,000,000 | 1,000+ |

**How to upgrade:** OpenAI automatically upgrades tiers based on usage and payment history. You can also request increases via their dashboard.

---

## Recommended Client Pricing Tiers

### Option A: Usage-Based Pricing

| Tier | Monthly Chats | Suggested Price | Your Est. Cost | Margin |
|------|---------------|-----------------|----------------|--------|
| **Starter** | Up to 1,000 | $50-75/mo | ~$15-25 | 60-70% |
| **Growth** | Up to 5,000 | $150-200/mo | ~$50-75 | 60-65% |
| **Scale** | Up to 20,000 | $400-500/mo | ~$150-200 | 55-60% |
| **Enterprise** | Unlimited | Custom | Variable | Negotiated |

### Option B: Flat Rate with Overages

| Tier | Included Chats | Monthly Fee | Overage Rate |
|------|----------------|-------------|--------------|
| **Basic** | 1,000 | $75/mo | $0.05/chat |
| **Professional** | 5,000 | $200/mo | $0.04/chat |
| **Business** | 20,000 | $500/mo | $0.03/chat |

### Option C: Value-Based Pricing

| Package | Features | Monthly Fee |
|---------|----------|-------------|
| **Essential** | Widget only, up to 2K chats | $99/mo |
| **Professional** | Widget + WhatsApp, up to 5K chats | $249/mo |
| **Enterprise** | All channels + priority support | $499+/mo |

---

## Cost Scenarios

### Scenario 1: Soft Launch (Month 1-3)

- **Expected traffic:** 200-500 chats/month
- **Replit hosting:** Covered by Core credits ($0)
- **OpenAI API:** ~$2-5/month
- **Total cost:** ~$5/month
- **Recommended charge:** $50-75/month (setup + maintenance included)

### Scenario 2: Growing Business (Month 4-6)

- **Expected traffic:** 1,000-3,000 chats/month
- **Replit hosting:** ~$10-15/month
- **OpenAI API:** ~$15-40/month
- **Total cost:** ~$25-55/month
- **Recommended charge:** $150-200/month

### Scenario 3: Active Marketing Campaign

- **Expected traffic:** 10,000+ chats/month
- **Replit hosting:** ~$25-50/month (Reserved VM recommended)
- **OpenAI API:** ~$100-200/month
- **OpenAI tier upgrade:** May be needed (free)
- **Total cost:** ~$125-250/month
- **Recommended charge:** $400-500/month

---

## Scaling Checklist

When traffic increases, follow this checklist:

### Immediate (No Cost)

- [ ] Monitor Replit dashboard for resource usage
- [ ] Check OpenAI usage dashboard for rate limit proximity
- [ ] Review error logs for timeout/failure patterns

### If Hitting Limits

- [ ] Upgrade to Reserved VM deployment (predictable resources)
- [ ] Request OpenAI tier upgrade (free, based on history)
- [ ] Enable Replit Autoscale with higher max instances

### Future Optimizations (If Needed)

- [ ] Implement response caching for common questions
- [ ] Migrate ChromaDB to cloud-hosted vector database
- [ ] Add request queuing for traffic spikes
- [ ] Consider dedicated OpenAI enterprise agreement

---

## Monitoring Recommendations

### Key Metrics to Track

1. **Chat volume** - Daily/weekly/monthly conversations
2. **Response times** - Average time to first token
3. **Error rates** - Timeouts, API failures
4. **OpenAI usage** - Tokens consumed, rate limit hits
5. **User satisfaction** - Thumbs up/down ratio

### Alerting Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Response time | > 5 seconds | > 15 seconds |
| Error rate | > 2% | > 5% |
| OpenAI RPM usage | > 70% of limit | > 90% of limit |
| Daily chats | > 80% of tier | > 100% of tier |

---

## Summary

| Question | Answer |
|----------|--------|
| Is the system scalable? | **Yes** |
| Current comfortable capacity | 5-10 concurrent users |
| Maximum with current setup | ~15-25 concurrent users |
| Main cost driver | OpenAI API usage |
| Can we increase capacity? | Yes (upgrade OpenAI tier, Reserved VM) |
| Is UAT safe? | **Absolutely** |
| Ready for production? | **Yes** |

---

## Appendix: Quick Reference URLs

| Resource | URL |
|----------|-----|
| Replit Pricing | https://replit.com/pricing |
| OpenAI Pricing | https://openai.com/pricing |
| OpenAI Rate Limits | https://platform.openai.com/account/limits |
| Replit Usage Dashboard | Available in your Replit account |

---

*Document prepared for internal planning purposes. Adjust pricing based on your business model and client relationship.*
