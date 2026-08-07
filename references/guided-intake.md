# Guided intake

Use this on the first invocation when the user has not supplied every launch choice. Prefill any values already present and omit questions that are fully resolved.

Ask in one message:

> This setup has two phases:
>
> 1. **Build and seed:** I’ll collect the essentials, create a unique campaign folder under `Desktop/Codex/SSP Projects`, and validate it.
> 2. **Open and run:** I’ll then show you the exact generated folder to add as a local Codex project. You’ll start a new task inside it and type `run`.
>
> You do not need to create an empty campaign project first. When Phase 1 finishes, select the exact generated campaign folder—not the shared `SSP Projects` parent.
>
> For Phase 1, please attach the publisher CSV if it is not already attached, then reply with:
>
> 1. **Ad manager / SSP:**  
> 2. **Minimum monthly visitors:** `50k` by default  
> 3. **Target site types:** `travel and travel adjacent` by default  
> 4. **Geography:** `any` by default  
> 5. **Optional note or project name:** leave blank if unnecessary  
>
> You can simply provide the ad manager and say **use defaults** for items 2–4.

Behavior:

- If the CSV is attached, state its filename and do not request a path.
- If the provider is already supplied, prefill it.
- If optional criteria are already supplied, prefill them rather than asking again.
- Do not run the builder while the required CSV or provider is missing.
- Treat `use defaults` as:
  - minimum monthly traffic `50000`;
  - target verticals `travel,travel_adjacent`;
  - no geography restriction.
