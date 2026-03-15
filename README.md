# Concept → Animation

Turn concepts and code into animated explanations.
Prompt → generate Manim → generated/animation.py → render → media/video.mp4

## Setup

Run:

```bash
chmod +x setup_env.sh
./setup_env.sh
source use-manim-env.sh
```

Activate Environment:

```bash
source manim-env/bin/activate
```

## Test animation

```bash
manim -pql binary_search.py BinarySearchVisualization
```

