# New AI Models for ListingJet — Plain-English Breakdown

> A non-technical overview of the Qwen 3.6-Plus and Gemma 4 integrations,
> including what changed under the hood and why it matters.

## Meet the Two New Models

### Qwen 3.6-Plus (from Alibaba)
Think of this as a **super-reader with perfect memory**.
- It can read the equivalent of a **700-page book in one sitting** and remember every detail.
- It's great at thinking through complicated, multi-step problems (like breaking down a floor plan photo into a 3D room layout).
- Best for: tasks that need to look at **a lot of information at once** — entire property histories, long market reports, full listing archives.

### Gemma 4 (from Google)
Think of this as a **fast, affordable workhorse**.
- It's **~10x cheaper** than what we currently use for bulk photo analysis.
- It can look at photos, read text, and even understand audio.
- Google lets us **run it on our own computers** for free — meaning no per-use fees once it's set up.
- Best for: high-volume, repetitive tasks like scanning hundreds of listing photos.

---

## What This Means for ListingJet

### Before
Every photo and every piece of listing copy went through the **same expensive AI model**, no matter how simple the job was. It was like paying a surgeon to put on a Band-Aid.

### After
We now match the **right tool to the right job**:

| Task | Before | After | Why |
|---|---|---|---|
| Sorting hundreds of photos | Premium AI ($$$) | Gemma 4 ($) | Simple job, high volume |
| Writing Instagram captions | Premium AI ($$$) | Gemma 4 ($) | Volume-heavy, low stakes |
| Turning floor plan into 3D | Premium AI ($$$) | Qwen 3.6-Plus | Needs to see everything at once |
| Long market analysis reports | Premium AI ($$$) | Qwen 3.6-Plus | Huge amount of context needed |
| Polished MLS listing copy | Premium AI | Premium AI | Quality matters most here |

---

## The Smart Plumbing We Built

### 1. A "Switchboard" for AI Models
Instead of being locked into one AI, **we can now swap models on the fly** — per agent, per customer, or per account tier — just by changing a setting. No code changes needed.

### 2. Automatic Safety Net
If the cheap/fast model fails for any reason, the system **automatically retries with our premium model**. Users never see an error.

### 3. Self-Healing Retries
When the network hiccups or a service is briefly down, the system **waits a moment and tries again** — up to 3 times, with smart spacing. Temporary glitches don't become customer-facing failures.

### 4. Per-Customer Customization
Enterprise customers can say **"I only want premium AI"** while free-tier customers use the cheaper option. It's now just a setting — no developer needed.

### 5. Cost Tracker
Every AI call is now **logged with its cost**. We can see exactly how much each customer, feature, or photo is costing us in real time.

### 6. Admin Dashboard
A new admin screen shows:
- Which AI is being used for which feature right now
- Current pricing for every model
- A cost calculator to forecast "what would 1,000 photos cost?"

### 7. Option to Run Our Own AI
Gemma 4 can be **hosted on our own servers**. Once set up, it has **zero per-use cost** and **keeps sensitive client data in-house** (important for privacy-conscious agents).

---

## Bottom Line for the Business

| Benefit | Impact |
|---|---|
| **Lower costs** | ~70% cheaper on bulk photo/caption jobs |
| **Better quality** | Premium AI still handles the work that matters most |
| **More reliable** | Automatic fallback means fewer failed listings |
| **Flexible pricing tiers** | Enterprise gets premium, free tier gets economy |
| **Privacy option** | Self-hosted path for privacy-sensitive clients |
| **No vendor lock-in** | Easy to swap AI providers as prices/quality change |
