#!/usr/bin/env bash
source manim-env/bin/activate

export HOMEBREW_PREFIX="$(brew --prefix)"
export PATH="$HOMEBREW_PREFIX/bin:$HOMEBREW_PREFIX/sbin:$PATH"
export PKG_CONFIG="$HOMEBREW_PREFIX/bin/pkg-config"
export PKG_CONFIG_PATH="$HOMEBREW_PREFIX/lib/pkgconfig:$(brew --prefix cairo)/lib/pkgconfig:$(brew --prefix pango)/lib/pkgconfig"