# Contributing to Animated Explainer Studio

Thanks for your interest in contributing! This project turns code and concepts into animated visual explanations. We welcome PRs, bug reports, and feature ideas.

## Getting started

1. Fork the repo and clone your fork
2. Follow the [Quick start](README.md#quick-start-local) guide to get running locally
3. Create a branch for your work: `git checkout -b my-feature`
4. Make your changes, then open a Pull Request against `master`

## What to work on

Check the [open issues](https://github.com/t-mercier/code-visual-explainer/issues) — anything labeled **good first issue** or **help wanted** is a great starting point.

### Known areas that need help

- **Manim animation sync** — voiceover timing doesn't align well with Manim scenes (see issue tracker)
- **Multi-scene Manim rendering** — animations overlap instead of playing sequentially
- **Prompt pipeline quality** — the concept/code explanation path needs better storyboard-to-animation mapping
- **Frontend polish** — UI improvements, mobile responsiveness, dark mode tweaks
- **New concepts** — add pre-made demo videos for more algorithms/data structures
- **Testing** — unit tests for pipeline stages, integration tests for the API

## Guidelines

- Keep PRs focused — one feature or fix per PR
- Add a short description of _what_ and _why_ in your PR
- If you're adding a new pipeline stage or changing the API, update the README
- Run the frontend build (`cd client && npm run build`) before submitting to catch TS errors

## Reporting bugs

Open an issue with:
- What you did (input / steps to reproduce)
- What you expected
- What actually happened
- Logs or screenshots if possible

## Code style

- **Python**: follow existing patterns — type hints, logging, async where appropriate
- **TypeScript/React**: functional components, Tailwind for styling
- No need for strict formatting tools — just be consistent with the surrounding code

## Questions?

Open a discussion or issue — happy to help you get oriented.
