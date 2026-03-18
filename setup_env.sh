#!/usr/bin/env bash

set -e

echo "🚀 Setting up Concept → Animation environment"

# Check Homebrew
if ! command -v brew &> /dev/null
then
    echo "❌ Homebrew not found. Please install it first:"
    echo "https://brew.sh"
    exit
fi

echo "📦 Installing system dependencies..."
brew install cairo pango pkg-config

echo "🐍 Creating Python virtual environment..."

python3 -m venv manim-env

source manim-env/bin/activate

echo "⬆️ Updating pip..."
pip install --upgrade pip setuptools wheel

echo "📚 Installing Python dependencies..."
pip install -r requirements.txt

echo "🛠 Creating environment activation script..."

cat << 'EOF' > use-manim-env.sh
#!/usr/bin/env bash

echo "Activating Manim environment..."

source manim-env/bin/activate

export HOMEBREW_PREFIX="$(brew --prefix)"
export PATH="$HOMEBREW_PREFIX/bin:$HOMEBREW_PREFIX/sbin:$PATH"
export PKG_CONFIG="$HOMEBREW_PREFIX/bin/pkg-config"
export PKG_CONFIG_PATH="$HOMEBREW_PREFIX/lib/pkgconfig:$(brew --prefix cairo)/lib/pkgconfig:$(brew --prefix pango)/lib/pkgconfig"

echo "Environment ready."
echo "Test with:"
echo "manim -pql concepts/binary_search.py BinarySearchVisualization"
EOF

chmod +x use-manim-env.sh

echo "✅ Installation complete"

echo ""
echo "Next steps:"
echo ""
echo "1️⃣ Activate environment:"
echo "source use-manim-env.sh"
echo ""
echo "2️⃣ Test animation:"
echo "manim -pql concepts/binary_search.py BinarySearchVisualization"