# ⚡ Smart EV Charging Optimization

A **time-aware EV charging scheduler** that minimizes electricity costs while ensuring your vehicle reaches the target battery level before the planned departure time. This project demonstrates **energy optimization skills**, interactive UI, and backend scheduling logic, with a foundation for future **Energy AI / ML enhancements**.

---

## 🚀 Project Overview

The goal of this project is to provide a **smart, interactive system** for planning electric vehicle (EV) charging based on:

- Current battery level
- Target battery level
- Charger power
- Departure time
- Electricity tariffs (peak/off-peak hours)

The system calculates an optimized charging schedule to **minimize cost** while guaranteeing the EV is ready on time. It also provides **visual feedback** via a real-time SOC chart and countdown.

> ⚠️ Current version uses **rule-based optimization**. Future enhancements can include ML/AI-based price prediction and reinforcement learning charging strategies.

---

## 📸 Features

- **Interactive UI** using React + Tailwind CSS  
- **Time-aware optimization** based on departure time and electricity tariffs  
- **Real-time countdown** until charging starts  
- **Dynamic SOC timeline chart** using Recharts  
- **Switchable cost-optimization mode** (cheapMode toggle)  
- **Responsive design** for desktop and mobile

---

## 🛠 Tech Stack

| Layer        | Technologies |
| ------------ | ------------ |
| Frontend     | Next.js, React, TypeScript, Tailwind CSS, Framer Motion |
| Charts & UI  | Recharts, Radix UI components |
| Backend API  | FastAPI (planned / placeholder) |
| State        | React useState / useMemo / useEffect |
| Deployment   | Vercel (Next.js hosting) |

---

## ⚡ How It Works

1. User inputs:
   - Current battery (%)
   - Charger power (kW)
   - Target SOC (%)
   - Departure time
   - Cost optimization toggle
2. The system calculates:
   - Optimal start and end charging times
   - Charging hours needed
   - Cost now vs optimized cost
3. Visual feedback:
   - SOC timeline chart with start/end reference lines
   - Real-time countdown until charging starts
   - Alerts if the target SOC cannot be reached before departure

---

## 🎯 Next Steps / Future Enhancements

- Backend API using FastAPI for optimization requests
- Persist charging results in a database
- AI-powered electricity price prediction (LightGBM / Random Forest)
- Reinforcement learning for smart charging policies
- Historical data dashboard
- Push notifications when charging completes

> Once fully implemented with ML/AI, this project becomes a strong **Energy AI / MLOps portfolio piece**.

---

## 📦 Getting Started

Clone the repo:

```bash
git clone https://github.com/YOUR_USERNAME/smart-ev-charging.git
cd smart-ev-charging

```
Install dependencies:
```bash
npm install
# or
yarn
# or
pnpm install
```

Run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
```

Open http://localhost:3000 in your browser.
---


## 📊 Project Structure
📊 Project Structure
```bash
.
├── app/                 # Next.js pages & components
├── components/ui/       # Reusable UI components (Slider, Switch, ChartTooltip, etc.)
├── public/              # Static assets
├── styles/              # Tailwind CSS configuration
├── backend/             # Placeholder for FastAPI optimization endpoints
└── README.md
```
## 🧠 Learnings & Skills

- Energy domain understanding: time-based EV charging, peak/off-peak electricity costs  
- Rule-based optimization logic for scheduling  
- Time handling: cross-day, timestamps, Date → number conversions for charts  
- Interactive charts with Recharts and React hooks  
- Frontend-backend integration with fetch API  
- Preparing a project foundation for future AI/ML integration


## 🔗 Deployment

You can deploy the Next.js app on **Vercel**:

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=YOUR_REPO_URL)



## 👤 Author

Ricky Chang  

- [Portfolio](https://rickychang.vercel.app)  
- [GitHub](https://github.com/GiaSoon2000)  
- [LinkedIn](https://linkedin.com/in/ricky-chang-80728628b/)
