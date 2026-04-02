# Sherlock Platform: Modernization & Match Discovery Plan

## 1. Vision
Transform the existing "Manual Calculator" into a "Pro Detective Dashboard". The user should feel like they are inside a Sherlock Holmes investigation room, with glass panels, data flowing, and a clear "Deduction" at the end.

## 2. UI/UX Refinement (Premium Aesthetics)
- **Sidebar Navigation**: Replace top horizontal tabs with a modern sidebar (better for desktop discovery).
- **Glassmorphism 2.0**: Increase blur, add subtle borders, and use linear gradients for a premium feel.
- **Dynamic Icons**: Add visual cues (🔍, 🏟️, 📊, 🕵️‍♂️) for navigation.
- **Consistent Typography**: Use *Inter* for data and *Outfit* for headers.
- **Micro-Animations**: Add hover transitions for all cards and smooth reveals for results.

## 3. Match Discovery (The "WOW" Feature)
- **Upcoming Matches Sidebar**: A panel showing today's fixtures (Football, NBA, Tennis).
- **Auto-Fill Logic**: When a match is clicked, it fetches known stats from the DB and populates the manual form. This bridges the gap between the sync system and the analysis tool.
- **Sync Trigger**: A "Refresh Data" button in the sidebar to call the `/sync` endpoint for the active sport.

## 4. Enhanced AI Deductions
- **Detection Report**: The LLM verdict will be styled as a "Detective's Dossier" (Specialized Card).
- **Sherlock Insights**: Highlighted takeaways (e.g., "🎯 Point of Value", "⚠️ Risk Alert").

## 5. Technical Tasks
### Phase 1: Layout & Navigation
- Update [dashboard.html](file:///C:/Users/cardo/01_Desarrollo/Proyectos_Personales/Sherlock/src/ui/web/templates/dashboard.html) to a Grid layout with Sidebar (`nav`) and Content (`main`).
- Refactor [styles.css](file:///C:/Users/cardo/01_Desarrollo/Proyectos_Personales/Sherlock/src/ui/web/static/css/styles.css) for the new navigation and glassmorphism.

### Phase 2: Match Explorer
- Add a new section in the UI to display the list of upcoming matches.
- Implement the JS logic in [comparator.js](file:///C:/Users/cardo/01_Desarrollo/Proyectos_Personales/Sherlock/src/ui/web/static/js/comparator.js) to fetch from `/api/v1/matches`.
- Add "Auto-fill" handler.

### Phase 3: Visual Polish & Results
- High-fidelity charts (Radar/Bar) with custom colors.
- New "Loading" animation (Sherlock's signature silhouette or magnifying glass).
- Final review of mobile responsiveness.

## 6. Verification
- Test match fetching across all 3 sports.
- Ensure the Manual entry still works perfectly.
- Validate that the AI analysis is still correctly processed.
