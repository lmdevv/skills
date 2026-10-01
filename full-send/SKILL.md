---
name: full-send
description: Handle a coding task through verification, PR review, and merge. Use when the user delegates the whole task.
disable-model-invocation: true
user-invocable: true
metadata:
  opencode/autoinvoke: false
---

# Full send

Own the task through merge. Assume the user will never read your output. Invoking this skill authorizes commits, pushes, a pull request, and merge for the requested task. Respect repository rules and stay within scope.

## Finish the work

1. Understand the issue and fix it.
2. Verify the affected behavior using the app, computer use, existing checks, or focused test scripts. For UI changes, exercise the changed flow. Fix failures before proceeding.
3. Commit, push, and open a PR. Describe the fix and verification evidence.
4. Monitor CI and automated reviews. Fix failures and actionable comments, verify, and push again. Wait for checks and reviewers after each push. Explain rejected suggestions in the PR. Continue until CI passes and reviewers finish with no unresolved actionable findings on the latest commit.
5. Review the final diff and verify the behavior once more. Confirm checks and reviews cover the current PR head. If it changes, repeat the affected checks and review.
6. Merge when confidence is high and repository requirements permit it. Use the repository's merge method. Confirm the PR merged.

High confidence needs evidence that the requested behavior works, relevant checks pass, and no material concern remains. Green CI alone is insufficient. Never bypass protections or required approvals to finish.

## When you need the user

Use the question tool whenever you need input. Ordinary output may never reach them. State the blocker and decision needed. Continue independent work while waiting. Silence is not approval.

If verification remains inconclusive, required approval is missing, or an external blocker prevents progress, keep the PR open and use that tool. If unavailable, state the blocker and required input in the final response. Never claim completion while blocked.

After merge, give a short receipt with the PR link and verification results.
