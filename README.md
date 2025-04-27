# Welcome to **SubReddit MeltDown** 🫠

This is for you to understand **Issues → Branches → Pull Requests** workflow.

---

## 1. Getting set up

| Step | Command / URL | Notes |
|------|---------------|-------|
| Clone | `git clone https://github.com/saurabh98s/SubredditMeltdown.git` | Replace URL if you forked. |
| Install GH CLI (nice‑to‑have) | `gh auth login` | Makes PR creation easier. |

---

## 2. Picking something to work on

1. Open the **Issues** tab.
2. Filter by label (e.g. `frontend`, `etl`).
3. **Comment “I’ll take this”** so everyone knows it's in progress.
4. Feel free to ask clarifying questions in the thread.

---

## 3. Create a feature branch

```bash
# Always pull the latest main branch first
git checkout main
git pull origin main
git checkout -b 17-download-reddit-data(this is your branch name)

```

> **Tip:** keep branches small. One Issue = one PR.

---

## 4. Commit early & often

* Use clear commit messages:
  * `feat(api): add /summary endpoint`
  * `fix(etl): skip deleted posts`

```bash
git add .
git commit -m "fix(clean_posts): handle unicode emojis"
git push -u origin 17-download-reddit-data
```

---

## 5. Open a Pull Request (PR)

### Via GitHub UI
1. Visit your branch on GitHub; you’ll see a **Compare & pull request** button.
2. Fill in:
   * **Title:** `feat(clean): drop non‑English rows (#6)`
   * **Description:** What, why, and *how to test*.
   * Link the Issue by typing `Fixes #6`—it auto‑closes when merged.
3. Assign **one reviewer** (ask on Whatsapp if unsure).

### Via GitHub CLI (optional)
```bash
gh pr create --fill --base main --head 17-download-reddit-data
```

---

## 6. Code review etiquette 

* **Be kind & constructive.** Point out what you like as well as improvements.
* Use **suggested‑change** blocks for quick fixes.
* If you're the author, respond to every comment ("Done", "Fixed", or explain why not").
* CI must be green before we press **Merge**.

---

## 7. Merging

| Situation | Button |
|-----------|--------|
| Small PR, review approved, CI green | **Squash & merge** (default) |
| Two parallel features | Ask before merging—avoid large merge conflicts. |

After merging, delete the feature branch in GitHub (click the purple button).

---
