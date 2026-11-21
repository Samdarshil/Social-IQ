# Judge demo script (about 5 minutes)

Run `make dev-backend` and `make dev-frontend`, open http://localhost:5173. Automated version: `make e2e`.

0. **Brief first (60 s)** – Landing → *Open the clustering analysis*. Walk the page top to bottom: banner (historical, descriptive), category chart, correlation matrix, silhouette curve ("only weakly separated, and we say so"), the three group cards, observations and limitations. Switch country to India to show the honest ordering note.
1. **Landing** – "Your social presence. One intelligent view." Click *Try the demo*. Point out the `DEMO DATA` badge.
2. **Overview** – blended KPIs across four platforms, engagement dip, anomaly strip.
3. **Analytics** – why engagement dropped: rate vs mix effects, significance.
4. **Predictions** – score a post; show interval, SHAP factors, what-if recommendations; open the Model Card and state the honest metrics.
5. **Insights** – cross-platform best platform per category, best publish times, Creator DNA.
6. **Assistant** – ask: "Why did my engagement drop?", "Which platform is performing best?", "What should I post next?", "Show my best-performing content." Show the tool chips and cards, and the mode line.
7. **Privacy Center** – read-only scopes, encryption, export/delete, what the AI receives.
8. **Mobile** – narrow the window.

Fallback talking point: with no `GEMINI_API_KEY` the assistant runs the same tools through a rule-based router and says so.
